import json

from evaluate import QUESTIONS, RESULTS, error_row, rank_of, score

QUESTION = {"gold": ["488(1)"], "fine": [80, 200], "version": "2026-11-01"}
UNANSWERABLE = {"gold": [], "fine": None, "version": "2026-11-01"}


def result(answerable, citations, fine, **checks):
    all_checks = {"verified": answerable}
    all_checks.update(checks)
    return {
        "final": {"answerable": answerable, "citations": citations, "fine": fine},
        "version": "2026-11-01",
        "retrieved": ["488(1)", "488(2)", "48(1)"],
        "checks": all_checks,
    }


def test_correct_answer():
    s = score(QUESTION, result(True, ["488(1)"], [80, 200]))
    assert s["correct"]
    assert s["citation_correct"]
    assert s["fine_correct"]
    assert not s["abstained"]


def test_extra_cited_part_next_to_the_gold_part_is_still_correct():
    s = score(QUESTION, result(True, ["488(1)", "488(2)"], [80, 200]))
    assert s["correct"]
    assert not s["right_article_wrong_part"]


def test_wrong_part_and_wrong_fine():
    s = score(QUESTION, result(True, ["488(2)"], [80, 200]))
    assert not s["correct"]
    assert s["right_article_wrong_part"]
    s = score(QUESTION, result(True, ["488(1)"], [80, 300]))
    assert not s["correct"]
    assert s["fine_correct"] is False


def test_abstentions():
    assert score(QUESTION, result(False, [], [None, None]))["abstained"]
    assert not score(QUESTION, result(False, [], [None, None]))["correct"]
    assert score(UNANSWERABLE, result(False, [], [None, None]))["correct"]
    assert not score(UNANSWERABLE, result(True, ["48(1)"], [None, None]))["correct"]


def test_invalid_output_is_not_an_abstention():
    s = score(UNANSWERABLE, result(False, [], [None, None], invalid_output=True))
    assert not s["correct"]
    assert not s["abstained"]
    assert s["invalid_output"]


def test_rank_of():
    assert rank_of({"488(1)"}, ["48(1)", "488(1)"]) == 2
    assert rank_of({"488(1)"}, ["48(1)"]) is None


def test_saved_answers_match_the_current_scoring():
    questions = {}
    for split in ("dev", "test"):
        path = QUESTIONS / f"{split}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            q = json.loads(line)
            questions[q["id"]] = q

    answer_files = list(RESULTS.glob("answers_*.jsonl"))
    checked = 0
    for path in answer_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            q = questions.get(row["id"])
            if q and q["question"] == row["question"]:
                assert row["score"] == score(q, row), (path.name, row["id"])
                checked += 1
    assert checked or not answer_files


def test_failed_request_is_invalid():
    q = {
        "id": "dev-004",
        "question": "Kokia bauda grėsė 2026 m. sausio 12 d.?",
        "gold": ["99(1)"],
        "fine": [300, 1450],
        "version": "2026-01-12",
    }
    row = error_row(q, True, "ReadTimeout()")
    s = score(q, row)
    assert s["invalid_output"]
    assert not s["correct"]
    assert not s["abstained"]
    assert row["version"] == "2026-01-12"
