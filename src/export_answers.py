import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
QUESTIONS = ROOT / "questions"
RESULTS = ROOT / "results"
NOT_FOUND = "Atsakymo į šį klausimą ANK nerasta."


def chunk_id(version, part):
    return f"ank_{version}#{part}"


def load_parts(version):
    parts = {}
    path = PROCESSED / f"ank_{version}.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        parts[row["id"]] = row
    return parts


def verdict(gold, retrieved, refused, citations, fine_ok):
    if not gold:
        if refused and not citations:
            return "correct_refusal"
        return "false_answer"
    found = False
    for part in retrieved:
        if part in gold:
            found = True
    if not found:
        return "retrieval_failure"
    if refused:
        return "wrong_refusal"
    if fine_ok is False:
        return "generation_failure"
    if not citations:
        return "citation_failure"
    for part in citations:
        if part not in gold:
            return "citation_failure"
    return "correct"


def fine_text(fine):
    if fine is None or fine[0] is None:
        return "no fine"
    return f"{fine[0]} to {fine[1]} EUR"


def evidence(row, kind):
    gold = row["gold"]
    retrieved = row["retrieved"]
    citations = row["final"]["citations"]
    if kind == "correct_refusal":
        return "No ANK part answers this question; the system gave the not-found line and cited nothing."
    if kind == "false_answer":
        return f"No ANK part answers this question, but the system answered and cited {', '.join(citations)}."
    if kind == "retrieval_failure":
        top = ", ".join(retrieved[:2])
        if citations:
            answer_part = f"the answer cites {', '.join(citations)} with {fine_text(row['final']['fine'])}"
        else:
            answer_part = "the system said the answer was not found"
        return f"{gold[0]} is not among the 5 retrieved parts (they start with {top}); {answer_part}."
    rank = retrieved.index(gold[0]) + 1
    if kind == "generation_failure":
        return (f"{gold[0]} is ranked {rank} and cited, but the answer gives {fine_text(row['final']['fine'])} "
                f"while the part says {fine_text(row['fine'])}.")
    if kind == "wrong_refusal":
        return f"{gold[0]} is ranked {rank}, but the system said the answer was not found."
    if kind == "citation_failure":
        return f"{gold[0]} is ranked {rank}, but the answer cites {', '.join(citations) or 'nothing'}."
    return f"{gold[0]} is ranked {rank} and cited; the answer gives {fine_text(row['fine'])}, as the part does."


SPECIAL_EVIDENCE = {
    "dev-004": "99(1) is ranked 1 and cited, but the answer writes the upper bound 1450 as \"1 400,50\" "
               "(fine field 300 to 140050 EUR) while the part says 300 to 1450 EUR.",
    "dev-011": "507-1 is ranked 1 and cited; the answer gives 50 to 300 EUR, as the part does, but its text names "
               "the article \"ANK 507 str. 1 d.\" instead of 507¹.",
}


def build(split):
    questions = {}
    for line in (QUESTIONS / f"{split}.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        questions[q["id"]] = q

    parts_by_version = {}
    chunks = []
    for path in sorted(PROCESSED.glob("ank_*.jsonl")):
        version = path.stem.removeprefix("ank_")
        parts_by_version[version] = load_parts(version)
        for part_id, part in parts_by_version[version].items():
            chunks.append({"id": chunk_id(version, part_id), "document": f"ank_{version}", "lang": "lt",
                           "text": part["header"] + "\n" + part["text"]})

    items = []
    for line in (RESULTS / f"answers_{split}.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        q = questions[row["id"]]
        version = row["version"]
        parts = parts_by_version[version]
        refused = not row["final"]["answerable"]
        fine_ok = row["score"].get("fine_correct")
        kind = verdict(q["gold"], row["retrieved"], refused, row["final"]["citations"], fine_ok)

        if q["gold"]:
            gold_part = parts[q["gold"][0]]
            gold_answer = gold_part["header"]
            if q["fine"]:
                gold_answer = gold_answer + f": bauda nuo {q['fine'][0]} iki {q['fine'][1]} eurų."
        else:
            gold_answer = None

        if row["id"] in SPECIAL_EVIDENCE:
            note = SPECIAL_EVIDENCE[row["id"]]
        else:
            note = evidence(row, kind)

        gold_ids = []
        for part in q["gold"]:
            gold_ids.append(chunk_id(version, part))
        retrieved_ids = []
        for part in row["retrieved"]:
            retrieved_ids.append(chunk_id(version, part))
        cited_ids = []
        for part in row["final"]["citations"]:
            cited_ids.append(chunk_id(version, part))

        kind_name = q["type"]
        if kind_name == "unanswerable":
            kind_name = "no_answer"
        items.append({
            "id": row["id"],
            "kind": kind_name,
            "wording": q["wording"],
            "question": q["question"],
            "version": version,
            "gold": gold_ids,
            "gold_answer": gold_answer,
            "retrieved": retrieved_ids,
            "answer": row["final"]["answer"],
            "citations": cited_ids,
            "verdict": kind,
            "evidence": note,
        })

    answers = {
        "system": "LitLex v2 mid-term: bge-m3 retrieval, top 5 article parts, qwen3:8b with a JSON answer and a citation check",
        "note": "Gold parts and fines were written in questions/questions.xlsx before the run. The two questions with an "
                "injected instruction are kept for the final and are not answered here.",
        "questions": items,
    }
    (RESULTS / "answers.json").write_text(json.dumps(answers, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (RESULTS / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False) + "\n", encoding="utf-8")

    counts = {}
    for item in items:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1
    print(f"{len(items)} answers: {counts}")
    print(f"{len(chunks)} chunks")
    print("-> results/answers.json, results/chunks.json")


def main():
    parser = argparse.ArgumentParser(description="Write answers.json and chunks.json with a verdict and evidence for every answer")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    args = parser.parse_args()
    build(args.split)


if __name__ == "__main__":
    main()
