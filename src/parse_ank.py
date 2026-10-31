import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"

CODE_START = "ADMINISTRACINIŲ NUSIŽENGIMŲ KODEKSAS"
CODE_END = "ĮGYVENDINAMI EUROPOS SĄJUNGOS TEISĖS AKTAI"

HEADING = re.compile(r"^(\d+)\s+straipsnis\.\s*(.*)$")
PART = re.compile(r"^(\d+)\.\s+(.*)$")
WORDING = re.compile(r"^(\d+)\s+straipsnio redakcija nuo (.+?)(?:\s+iki\s+(.+?))?:$")
NOTE = re.compile(r"^(Straipsnio|Papildyta|Pakeistas|Punkto|Priedo)\b.*:$")
AMENDMENT = re.compile(r"^Nr\.\s")
STRUCTURE = re.compile(r"^([IVXLC]+)\s+(DALIS|SKYRIUS)$")
LT_DATE = re.compile(r"(\d{4})\s*(?:m\.)?\s*([a-ząčęėįšųūž]+)\s+(\d{1,2})\s*d\.?")
MONTHS = {
    "sausio": 1, "vasario": 2, "kovo": 3, "balandžio": 4, "gegužės": 5, "birželio": 6,
    "liepos": 7, "rugpjūčio": 8, "rugsėjo": 9, "spalio": 10, "lapkričio": 11, "gruodžio": 12,
}
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass
class Part:
    number: str | None
    lines: list = field(default_factory=list)
    amendments: list = field(default_factory=list)


@dataclass
class Article:
    base: int
    sup: str | None
    title: str
    chapter: str
    valid_from: str | None = None
    valid_to: str | None = None
    parts: list = field(default_factory=list)
    amendments: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def key(self):
        if self.sup:
            return f"{self.base}-{self.sup}"
        return str(self.base)

    @property
    def label(self):
        if self.sup:
            return f"{self.base}{self.sup.translate(SUPERSCRIPT)}"
        return str(self.base)


def lt_date(text):
    m = LT_DATE.search(text)
    if not m or m.group(2) not in MONTHS:
        raise ValueError(f"cannot read date: {text!r}")
    year = m.group(1)
    month = MONTHS[m.group(2)]
    day = int(m.group(3))
    return f"{year}-{month:02d}-{day:02d}"


def split_number(raw, base):
    if int(raw) == base + 1:
        return int(raw), None
    if not base:
        return None
    prefix = str(base)
    if not raw.startswith(prefix):
        return None
    rest = raw[len(prefix):]
    if rest == "" or rest[0] == "0":
        return None
    return base, rest


def clean(line):
    line = line.replace("\xa0", " ")
    line = line.replace("\u202f", " ")
    line = line.replace("\u2011", "-")
    return line.strip()


def code_lines(text):
    lines = [clean(line) for line in text.split("\n")]
    start = lines.index(CODE_START)
    end = lines.index(CODE_END, start)
    trailing = ("", "priedas", "administracinių nusižengimų kodekso", "Lietuvos Respublikos")
    while end > start and lines[end - 1] in trailing:
        end -= 1
    return lines[start + 1:end]


def parse(text):
    articles = []
    problems = []
    current = None
    part = None
    base = 0
    part_base = 0
    pending_wording = None
    structure = {"DALIS": "", "SKYRIUS": ""}
    expect_title = None
    after_structure = False
    in_note = None

    for line in code_lines(text):
        if not line:
            continue

        m = STRUCTURE.match(line)
        if m:
            structure[m.group(2)] = m.group(0)
            expect_title = m.group(2)
            after_structure = True
            in_note = None
            continue

        if expect_title and line.isupper():
            structure[expect_title] += " " + line.capitalize()
            continue
        expect_title = None

        m = WORDING.match(line)
        if m:
            valid_from = lt_date(m.group(2))
            valid_to = None
            if m.group(3):
                valid_to = lt_date(m.group(3))
            pending_wording = (valid_from, valid_to)
            in_note = None
            continue

        m = HEADING.match(line)
        if m:
            raw = m.group(1)
            title = m.group(2).strip()
            in_note = None
            after_structure = False
            if current and pending_wording and raw == current.raw:
                number = (current.base, current.sup)
            else:
                number = split_number(raw, base)
                if number is None:
                    problems.append(f"unexpected article number {raw} after {base}")
                    number = (int(raw), None)
            chapter = structure["SKYRIUS"].strip()
            current = Article(number[0], number[1], title, chapter)
            current.raw = raw
            if pending_wording:
                current.valid_from = pending_wording[0]
                current.valid_to = pending_wording[1]
                pending_wording = None
            base = number[0]
            part = Part(None)
            current.parts.append(part)
            part_base = 0
            articles.append(current)
            continue

        if current is None:
            continue

        if line.startswith("TAR pastaba"):
            current.notes.append(line)
            if not in_note:
                in_note = "article"
            continue
        if NOTE.match(line):
            if after_structure:
                in_note = "structure"
            elif part.number and re.search(r"dalies|dalimi|punkt", line, re.I):
                in_note = "part"
            else:
                in_note = "article"
            continue
        if in_note and AMENDMENT.match(line):
            if in_note == "part":
                part.amendments.append(line)
            elif in_note != "structure":
                current.amendments.append(line)
            continue
        in_note = None

        m = PART.match(line)
        if m:
            number = split_number(m.group(1), part_base)
            if number:
                part_base = number[0]
                if number[1]:
                    label = f"{number[0]}-{number[1]}"
                else:
                    label = str(number[0])
                part = Part(label, [m.group(2)])
                current.parts.append(part)
                continue

        part.lines.append(line)

    return articles, problems


def pick_wordings(articles, day):
    groups = {}
    for a in articles:
        if a.key not in groups:
            groups[a.key] = []
        groups[a.key].append(a)

    kept = []
    for key, group in groups.items():
        if len(group) == 1:
            kept.append(group[0])
            continue

        dated = [a for a in group if a.valid_from]
        undated = [a for a in group if not a.valid_from]
        starts = [a.valid_from for a in dated]
        first_start = min(starts)
        day_before = date.fromisoformat(first_start) - timedelta(days=1)
        day_before = day_before.isoformat()
        for a in undated:
            if not a.valid_to:
                a.valid_to = day_before

        valid = []
        for a in group:
            start = a.valid_from
            if not start:
                start = "0000"
            if start <= day:
                if a.valid_to is None or day <= a.valid_to:
                    valid.append(a)
        if len(valid) != 1:
            raise ValueError(f"article {key}: {len(valid)} wordings valid on {day}")
        valid[0].other_wordings = len(group) - 1
        kept.append(valid[0])
    return kept


def pretty(number):
    base, dash, sup = number.partition("-")
    return base + sup.translate(SUPERSCRIPT)


def chunks(articles, meta):
    for a in articles:
        repealed = a.title.startswith("Neteko galios")
        parts = [p for p in a.parts if p.number or p.lines]
        if not parts:
            parts = [Part(None, [a.title], a.parts[0].amendments)]
        for p in parts:
            text = " ".join(p.lines).strip()
            if p.number:
                part_label = pretty(p.number)
                chunk_id = f"{a.key}({p.number})"
                label = f"{a.label}({part_label})"
                header = f"ANK {a.label} str. {part_label} d. {a.title}"
            else:
                chunk_id = a.key
                label = a.label
                header = f"ANK {a.label} str. {a.title}"
            part_repealed = repealed or text.startswith("Neteko galios")
            yield {
                "id": chunk_id,
                "article": a.key,
                "part": p.number,
                "label": label,
                "title": a.title,
                "chapter": a.chapter,
                "header": header,
                "text": text,
                "repealed": part_repealed,
                "amendments": a.amendments + p.amendments,
                "notes": a.notes,
                "version_from": meta["valid_from"],
                "version_to": meta["valid_to"],
            }


def main():
    parser = argparse.ArgumentParser(description="Split a consolidated ANK text into article parts")
    parser.add_argument("version", help="valid_from date of a downloaded version, e.g. 2026-11-01")
    args = parser.parse_args()

    meta_path = RAW_DIR / f"ank_{args.version}.json"
    text_path = RAW_DIR / f"ank_{args.version}.txt"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    text = text_path.read_text(encoding="utf-8")
    articles, problems = parse(text)
    headings = len(articles)
    articles = pick_wordings(articles, meta["valid_from"])
    rows = list(chunks(articles, meta))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"ank_{args.version}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    sup = 0
    repealed = 0
    for a in articles:
        if a.sup:
            sup += 1
        if a.title.startswith("Neteko galios"):
            repealed += 1
    numbered = len(articles) - sup

    print(f"version {meta['valid_from']} to {meta['valid_to']}")
    counts = f"headings {headings}, articles {len(articles)} ({numbered} numbered, {sup} with a superscript)"
    print(f"{counts}, repealed {repealed}")
    print(f"chunks {len(rows)} -> {out.relative_to(ROOT)}")
    for p in problems:
        print("problem:", p)


if __name__ == "__main__":
    main()
