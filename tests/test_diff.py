from diff_versions import compare

A = "Pirmasis pažeidimas užtraukia baudą nuo dešimt iki dvidešimt eurų."
B = "Antrasis visai kitas veiksmas užtraukia baudą nuo trisdešimt iki penkiasdešimt eurų."
C = "Trečioji taisyklė apie konfiskavimą ir kitas priemones."


def part(pid, text, title="T", repealed=False):
    article, _, rest = pid.partition("(")
    part_number = rest[:-1]
    if part_number == "":
        part_number = None
    return {
        "id": pid,
        "article": article,
        "part": part_number,
        "label": pid,
        "title": title,
        "text": text,
        "repealed": repealed,
    }


def kinds(rows):
    return [(r["old_id"], r["id"], r["kind"]) for r in rows]


def test_removed_part_in_the_middle():
    old = [part("9(1)", A), part("9(2)", B), part("9(3)", C)]
    new = [part("9(1)", A), part("9(2)", C)]
    rows = compare(old, new)
    assert kinds(rows) == [("9(3)", "9(2)", "renumbered"), ("9(2)", None, "removed")]


def test_added_part_in_the_middle():
    old = [part("9(1)", A), part("9(2)", C)]
    new = [part("9(1)", A), part("9(2)", B), part("9(3)", C)]
    rows = compare(old, new)
    assert kinds(rows) == [("9(2)", "9(3)", "renumbered"), (None, "9(2)", "added")]


def test_changed_fine():
    new_text = A.replace("dvidešimt", "trisdešimt")
    rows = compare([part("9(1)", A)], [part("9(1)", new_text)])
    assert kinds(rows) == [("9(1)", "9(1)", "changed")]
    assert rows[0]["fine_changed"]


def test_title_change_only():
    rows = compare([part("9(1)", A, "Old")], [part("9(1)", A, "New")])
    assert kinds(rows) == [("9(1)", "9(1)", "title_changed")]
    assert not rows[0]["fine_changed"]


def test_whole_article_repealed():
    stub = part("9", "Neteko galios nuo 2026-07-01", "Neteko galios nuo 2026-07-01", repealed=True)
    old = [part("9(1)", A, "Offence"), part("9(2)", B, "Offence")]
    rows = compare(old, [stub])
    assert kinds(rows) == [("9(1)", "9", "repealed"), ("9(2)", "9", "repealed")]
    for r in rows:
        assert r["fine_changed"]
        assert r["title"] == "Offence"


def test_changed_lower_bound_written_in_words():
    old = "bauda ne mažesnė negu penki ir ne didesnė negu devyni šimtai eurų."
    new = "bauda ne mažesnė negu dešimt ir ne didesnė negu devyni šimtai eurų."
    rows = compare([part("44", old)], [part("44", new)])
    assert kinds(rows) == [("44", "44", "changed")]
    assert rows[0]["fine_changed"]
