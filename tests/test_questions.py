import datetime as dt
import json

import pytest
from openpyxl import load_workbook

import questions
from questions import COLUMNS, EXAMPLES, cell, check


def rows(*overrides):
    out = []
    for n, example in enumerate(EXAMPLES, 2):
        row = dict(zip(COLUMNS, example))
        if row["fine_min"] is not None:
            row["fine_min"] = str(row["fine_min"])
        if row["fine_max"] is not None:
            row["fine_max"] = str(row["fine_max"])
        row["_row"] = n
        out.append(row)
    for i, changes in overrides:
        out[i].update(changes)
    return out


def errors_of(*overrides):
    found, errors, warnings = check(rows(*overrides))
    return errors


def test_examples_are_clean():
    found, errors, warnings = check(rows())
    assert errors == []
    assert warnings == []
    assert len(found) == len(EXAMPLES)


@pytest.mark.parametrize("override, message", [
    ((0, {"gold": "9999(1)"}), "not an article part"),
    ((4, {"gold": "488(1)"}), "unanswerable questions have no gold"),
    ((1, {"wording": "legal"}), "pair p01"),
    ((5, {"injection": None}), "need an injection"),
    ((0, {"type": "other"}), "type must be one of"),
    ((1, {"id": "dev-001"}), "used more than once"),
    ((2, {"fine_min": "60", "fine_max": "140"}), "not a range in the gold text"),
    ((2, {"fine_min": "550", "fine_max": "450"}), "not a range in the gold text"),
    ((2, {"gold": "1968-01-01"}), "is a date"),
])
def test_errors(override, message):
    errors = errors_of(override)
    assert any(message in e for e in errors)


def test_warnings():
    _, errors, warnings = check(rows((2, {"fine_min": "450", "fine_max": "700"})))
    assert errors == []
    assert any("not the first range" in w for w in warnings)


def test_pairs_compare_parsed_fields():
    first = (0, {"gold": "488(1);488(2)", "fine_min": None, "fine_max": None})
    second = (1, {"gold": "488(2); 488(1)", "fine_min": None, "fine_max": None})
    assert errors_of(first, second) == []
    errors = errors_of((1, {"fine_min": "200", "fine_max": "300"}))
    assert any("same fine" in e for e in errors)


def test_test_questions_must_not_repeat_dev_questions():
    changes = {"split": "test", "pair": None, "question": EXAMPLES[0][5], "wording": "legal"}
    errors = errors_of((1, changes))
    assert any("the same question as dev-001" in e for e in errors)


def test_excel_dates_are_read_as_text():
    assert cell(dt.datetime(2026, 11, 1)) == "2026-11-01"
    assert cell(dt.date(2026, 1, 12)) == "2026-01-12"
    assert cell(600.0) == "600"
    assert cell(" 488(1) ") == "488(1)"


def test_template_build_and_freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(questions, "QUESTIONS", tmp_path)
    monkeypatch.setattr(questions, "WORKBOOK", tmp_path / "questions.xlsx")
    monkeypatch.setattr(questions, "FROZEN", tmp_path / "test.sha256")
    questions.template()
    wb = load_workbook(tmp_path / "questions.xlsx")
    assert wb.sheetnames == ["Questions", "Articles", "Changes", "Instructions"]
    assert wb["Questions"]["G2"].number_format == "@"

    ws = wb["Questions"]
    first_row = ["test-001", "test", "ordinary", "legal", None, "Kokia bauda už smulkiąją vagystę?", "108",
                 "2026-11-01", None, 90, 400, None, None]
    ws.append(first_row)
    wb.save(tmp_path / "questions.xlsx")
    questions.build()
    dev_lines = (tmp_path / "dev.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(dev_lines) == len(EXAMPLES)
    test_question = json.loads((tmp_path / "test.jsonl").read_text(encoding="utf-8"))
    assert test_question["fine"] == [90, 400]

    questions.freeze()
    questions.build()
    second_row = ["test-002", "test", "unanswerable", "legal", None, "Kiek kainuoja pasas?",
                  None, None, None, None, None, None, None]
    ws.append(second_row)
    wb.save(tmp_path / "questions.xlsx")
    with pytest.raises(SystemExit):
        questions.build()
