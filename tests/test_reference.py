import pytest

from reference import judge, mcnemar, named

NOISE = {"gold": ["488(1)"], "fine": [80, 200]}
THEFT = {"gold": ["108"], "fine": [90, 400]}
NONE = {"gold": [], "fine": None}


@pytest.mark.parametrize("text, parts", [
    ("Pagal ANK 488 str. 1 d. bauda yra nuo 80 iki 200 eurų.", ["488(1)"]),
    ("Tai numato 419¹ straipsnio 1 dalis.", ["419-1(1)"]),
    ("ANK 484-1 str. ir 108 straipsnis", ["484-1", "108"]),
    ("2026 m. sausio 12 d. redakcija", []),
])
def test_named(text, parts):
    assert named(text) == parts


def test_judge_answerable():
    assert judge(NOISE, "Pagal ANK 488 str. 1 d. gresia bauda nuo aštuoniasdešimt iki dviejų šimtų eurų.")["correct"]
    s = judge(NOISE, "Pagal ANK 488 str. 2 d. gresia bauda nuo 80 iki 200 eurų.")
    assert not s["correct"]
    assert s["right_article_wrong_part"]
    assert not judge(NOISE, "Pagal ANK 488 str. 1 d. gresia bauda nuo 200 iki 300 eurų.")["correct"]
    assert judge(THEFT, "Pagal ANK 108 str. 1 d. bauda nuo 90 iki 400 eurų.")["correct"]


def test_judge_unanswerable():
    assert judge(NONE, "Atsakymo į šį klausimą ANK nerasta.")["correct"]
    assert not judge(NONE, "Pagal ANK 99 str. 1 d. bauda nuo 300 iki 1450 eurų.")["correct"]
    assert not judge(NONE, "Kokia laisvės atėmimo bausmė gresia už plėšimą?")["correct"]


def test_mcnemar():
    assert mcnemar(5, 0) == pytest.approx(0.0625)
    assert mcnemar(0, 0) == 1.0
