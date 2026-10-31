import json
import re
from functools import lru_cache

import pytest

from parse_ank import OUT_DIR, RAW_DIR, chunks, code_lines, parse, pick_wordings, split_number

EXPECTED = {
    "2026-01-12": {"articles": 787, "superscript": 94, "repealed": 17, "chunks": 3005, "words": 127725},
    "2026-11-01": {"articles": 791, "superscript": 98, "repealed": 20, "chunks": 3014, "words": 127875},
}

ARTICLE_HEADING = r"\d+\s+straipsnis\."
WORDING_HEADING = r"\d+\s+straipsnio redakcija nuo "
CHAPTER_HEADING = r"[IVXLC]+\s+(DALIS|SKYRIUS)$"
ACT_NUMBER = r"Nr\.\s"
TAR_NOTE = r"TAR pastaba"
AMENDMENT_NOTE = r"(Straipsnio|Papildyta|Pakeistas|Punkto|Priedo)\b.*:$"
NOT_LAW_PARTS = [ARTICLE_HEADING, WORDING_HEADING, CHAPTER_HEADING, ACT_NUMBER, TAR_NOTE, AMENDMENT_NOTE]
NOT_LAW = re.compile("^(" + "|".join(NOT_LAW_PARTS) + ")")


@lru_cache(maxsize=None)
def parsed(version):
    meta_path = RAW_DIR / f"ank_{version}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    text_path = RAW_DIR / f"ank_{version}.txt"
    articles, problems = parse(text_path.read_text(encoding="utf-8"))
    articles = pick_wordings(articles, meta["valid_from"])
    rows = list(chunks(articles, meta))
    return articles, problems, rows


def test_split_number():
    assert split_number("343", 342) == (343, None)
    assert split_number("3421", 342) == (342, "1")
    assert split_number("34210", 342) == (342, "10")
    assert split_number("211", 21) == (21, "1")
    assert split_number("211", 210) == (211, None)
    assert split_number("500", 342) is None


@pytest.mark.parametrize("version", EXPECTED)
def test_counts(version):
    articles, problems, rows = parsed(version)
    expected = EXPECTED[version]
    assert problems == []
    assert len(articles) == expected["articles"]

    superscript = 0
    for a in articles:
        if a.sup:
            superscript += 1
    assert superscript == expected["superscript"]

    repealed = 0
    for a in articles:
        if a.title.startswith("Neteko galios"):
            repealed += 1
    assert repealed == expected["repealed"]

    assert len(rows) == expected["chunks"]
    ids = {r["id"] for r in rows}
    assert len(ids) == len(rows)
    row_articles = {r["article"] for r in rows}
    article_keys = {a.key for a in articles}
    assert row_articles == article_keys


@pytest.mark.parametrize("version", EXPECTED)
def test_processed_files_match_a_fresh_parse(version):
    _, _, rows = parsed(version)
    path = OUT_DIR / f"ank_{version}.jsonl"
    stored = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stored.append(json.loads(line))
    assert stored == rows


@pytest.mark.parametrize("version", EXPECTED)
def test_known_parts(version):
    _, _, rows = parsed(version)
    by_id = {r["id"]: r for r in rows}
    assert by_id["488(1)"]["header"] == "ANK 488 str. 1 d. Viešosios rimties trikdymas"
    assert by_id["342-1(1)"]["label"] == "342¹(1)"
    assert by_id["247(6-1)"]["label"] == "247(6¹)"
    assert "aerodromo triukšmo apsauginių zonų" in by_id["53(1)"]["text"]
    assert by_id["82"]["repealed"]


@pytest.mark.parametrize("version", EXPECTED)
def test_notes_stay_out_of_the_text(version):
    _, _, rows = parsed(version)
    for r in rows:
        assert "TAR pastaba" not in r["text"]
        assert "paskelbta TAR" not in r["text"]

    found_note = False
    for r in rows:
        for note in r["notes"]:
            if "TAR pastaba" in note:
                found_note = True
                break
        if found_note:
            break
    assert found_note


def test_dated_wordings():
    articles, _, _ = parsed("2026-11-01")
    kept = {a.key: a for a in articles}
    assert kept["53"].valid_from == "2025-01-01"
    assert kept["53"].valid_to is None
    assert kept["256"].valid_from == "2025-01-01"


@pytest.mark.parametrize("version", EXPECTED)
def test_every_word_of_the_law_is_in_exactly_one_chunk(version):
    meta = json.loads((RAW_DIR / f"ank_{version}.json").read_text(encoding="utf-8"))
    text = (RAW_DIR / f"ank_{version}.txt").read_text(encoding="utf-8")
    everything, _ = parse(text)
    kept = pick_wordings(list(everything), meta["valid_from"])
    rows = list(chunks(kept, meta))

    dropped = []
    for a in everything:
        is_kept = False
        for k in kept:
            if a is k:
                is_kept = True
                break
        if not is_kept:
            dropped.append(a)

    dropped_words = 0
    for a in dropped:
        for p in a.parts:
            for line in p.lines:
                dropped_words += len(line.split())

    stream = []
    for r in rows:
        title_only = r["part"] is None and r["text"] == r["title"]
        if title_only:
            continue
        for word in r["text"].split():
            stream.append(word)

    pos = 0
    leaked = []
    left = []
    for line in code_lines(text):
        words = line.split()
        if not words:
            continue
        size = len(words)
        if stream[pos:pos + size] == words:
            step = size
        elif re.fullmatch(r"\d+\.", words[0]) and stream[pos:pos + size - 1] == words[1:]:
            step = size - 1
        else:
            left.append(line)
            continue
        if NOT_LAW.match(line):
            leaked.append(line)
        pos += step

    assert pos == len(stream), "chunk words that are not in the law text"
    assert leaked == [], "headings or notes inside chunk texts"

    law_left = []
    for line in left:
        if NOT_LAW.match(line):
            continue
        if line.isupper():
            continue
        law_left.append(line)

    law_left_words = 0
    for line in law_left:
        without_number = re.sub(r"^\d+\.\s+", "", line, count=1)
        law_left_words += len(without_number.split())
    assert law_left_words == dropped_words
    assert len(stream) == EXPECTED[version]["words"]
