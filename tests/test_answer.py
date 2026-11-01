from answer import check, fine_pair, schema, sources

TEXT = ("Šauksmai, švilpimas, garsus dainavimas arba grojimas muzikos instrumentais, kitokiais garsiniais aparatais "
        "ar kiti triukšmą keliantys veiksmai gatvėse, o nakties metu ir gyvenamosiose patalpose užtraukia baudą "
        "asmenims nuo aštuoniasdešimt iki dviejų šimtų eurų ir juridinių asmenų vadovams nuo dviejų šimtų iki trijų šimtų eurų.")
HITS = [
    {"id": "488(1)", "header": "ANK 488 str. 1 d. Viešosios rimties trikdymas", "text": TEXT},
    {"id": "48(1)", "header": "ANK 48 str. 1 d. Triukšmas", "text": "Kitas tekstas be baudos."},
    {"id": "108", "header": "ANK 108 str. Smulkioji vagystė",
     "text": "Smulkioji vagystė užtraukia baudą nuo devyniasdešimt iki keturių šimtų eurų."},
]


def raw(**changes):
    base = {
        "answerable": True,
        "citations": ["488(1)"],
        "quote": "užtraukia baudą asmenims nuo aštuoniasdešimt iki dviejų šimtų eurų",
        "answer": "Pagal ANK 488 str. 1 d. bauda yra nuo 80 iki 200 eurų.",
        "fine_min": 80,
        "fine_max": 200,
    }
    result = dict(base)
    result.update(changes)
    return result


def test_good_answer_passes():
    assert check(raw(), HITS)["verified"]


def test_citations_must_be_retrieved():
    assert not check(raw(citations=[]), HITS)["citations_retrieved"]
    assert not check(raw(citations=["488(1)", "299(1)"]), HITS)["citations_retrieved"]
    assert check(raw(citations=["488(1)", "108"]), HITS)["citations_retrieved"]


def test_no_answer_is_not_verified():
    assert not check(raw(answerable=False), HITS)["verified"]


def test_fine_written_up_to_an_amount():
    assert fine_pair({"fine_min": None, "fine_max": 300}) == (0, 300)
    assert fine_pair({"fine_min": None, "fine_max": None}) == (None, None)


def test_sources_are_labelled_with_their_ids():
    text = sources(HITS[:2])
    first, second = text.split("\n\n")
    assert first.startswith("[488(1)] ANK 488 str. 1 d.")
    assert second.startswith("[48(1)] ANK 48 str. 1 d.")


def test_schema_limits_citations_to_retrieved_ids():
    s = schema(["488(1)", "48(1)"])
    properties = s["properties"]
    assert properties["citations"]["items"]["enum"] == ["488(1)", "48(1)"]
    assert list(properties)[:4] == ["answerable", "citations", "quote", "answer"]
