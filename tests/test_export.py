from export_answers import chunk_id, verdict


def test_verdicts_follow_retrieval_first():
    gold = ["488(1)"]
    assert verdict(gold, ["488(1)", "48(1)"], False, ["488(1)"], True) == "correct"
    assert verdict(gold, ["48(1)", "48(3)"], False, ["48(1)"], False) == "retrieval_failure"
    assert verdict(gold, ["48(1)", "48(3)"], True, [], None) == "retrieval_failure"
    assert verdict(gold, ["488(1)"], True, [], None) == "wrong_refusal"
    assert verdict(gold, ["488(1)"], False, ["488(1)"], False) == "generation_failure"
    assert verdict(gold, ["488(1)", "48(1)"], False, ["48(1)"], None) == "citation_failure"


def test_verdicts_for_questions_without_an_answer():
    assert verdict([], ["108"], True, [], None) == "correct_refusal"
    assert verdict([], ["108"], False, ["108"], None) == "false_answer"


def test_chunk_id():
    assert chunk_id("2026-11-01", "488(1)") == "ank_2026-11-01#488(1)"
