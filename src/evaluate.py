import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "questions"
RESULTS = ROOT / "results"
K = 5
DEPTH = 10
KEYS = ("id", "type", "wording", "pair", "gold", "fine")


def load_questions(split):
    path = QUESTIONS / f"{split}.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    if not rows:
        name = path.relative_to(ROOT)
        raise SystemExit(f"{name} has no questions; fill questions/questions.xlsx and run src/questions.py build")
    return rows


def rank_of(gold, ranking):
    for position, part in enumerate(ranking, 1):
        if part in gold:
            return position
    return None


def frac(k, n):
    if not n:
        return "0/0"
    percent = 100 * k / n
    return f"{k}/{n} ({percent:.0f}%)"


def table(header, rows):
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for row in rows:
        cells = [str(x) for x in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def groups(row):
    return ["all", f"type: {row['type']}", f"wording: {row['wording']}"]


def write(name, rows, report):
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (RESULTS / f"{name}.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\n-> results/{name}.jsonl, results/{name}.md")


def retrieval(split):
    from retrieve import Retriever, embed

    questions = [q for q in load_questions(split) if q["gold"]]
    embed(["šiltas paleidimas"])
    retrievers = {}
    rows = []
    for q in questions:
        version = q["version"]
        if version not in retrievers:
            retrievers[version] = Retriever(version)
        t0 = time.perf_counter()
        hits = retrievers[version].search(q["question"], DEPTH)
        ms = (time.perf_counter() - t0) * 1000
        ranking = [h["id"] for h in hits]
        row = {}
        for key in KEYS:
            row[key] = q[key]
        row["question"] = q["question"]
        row["version"] = q["version"]
        row["ranking"] = ranking
        row["rank"] = rank_of(set(q["gold"]), ranking)
        row["retrieval_ms"] = round(ms, 1)
        rows.append(row)

    by = defaultdict(list)
    for r in rows:
        for g in groups(r):
            by[g].append(r)
    lines = []
    lines.append(f"# bge-m3 retrieval on {split} ({len(questions)} answerable questions)")
    lines.append("")
    intro = f"hit@1 = gold part ranked first, recall@{K} = gold part in the top {K}, MRR@{DEPTH}. "
    intro += "Each question is searched in the version given in its row."
    lines.append(intro)
    lines.append("")

    other_groups = [g for g in by if g != "all"]
    names = ["all"] + sorted(other_groups)
    body = []
    for name in names:
        subset = by[name]
        n = len(subset)
        hit1 = 0
        hitk = 0
        reciprocal_sum = 0
        for r in subset:
            rank = r["rank"]
            if rank == 1:
                hit1 += 1
            if rank and rank <= K:
                hitk += 1
            if rank:
                reciprocal_sum += 1 / rank
        mrr = reciprocal_sum / n
        body.append((name, frac(hit1, n), frac(hitk, n), f"{mrr:.3f}"))
    lines.append(table(("questions", "hit@1", f"recall@{K}", f"MRR@{DEPTH}"), body))

    per = defaultdict(dict)
    for r in rows:
        if r["pair"]:
            found = bool(r["rank"]) and r["rank"] <= K
            per[r["pair"]][r["wording"]] = found
    complete = [p for p in per.values() if len(p) == 2]
    if complete:
        legal_found = 0
        everyday_found = 0
        only_legal = 0
        only_everyday = 0
        for p in complete:
            legal = p["legal"]
            everyday = p["everyday"]
            if legal:
                legal_found += 1
            if everyday:
                everyday_found += 1
            if legal and not everyday:
                only_legal += 1
            if everyday and not legal:
                only_everyday += 1
        lines.append("")
        lines.append(f"## Wording pairs (recall@{K}, the same question asked in legal and in everyday words)")
        lines.append("")
        header = ("legal found", "everyday found", "only legal", "only everyday", "pairs")
        pair_row = (legal_found, everyday_found, only_legal, only_everyday, len(complete))
        lines.append(table(header, [pair_row]))

    lines += ["", "## Per question", ""]
    per_question = []
    for r in rows:
        gold_text = ";".join(r["gold"])
        if r["rank"]:
            rank_text = r["rank"]
        else:
            rank_text = f"not in top {DEPTH}"
        top3 = ", ".join(r["ranking"][:3])
        per_question.append((r["id"], r["type"], r["wording"], gold_text, rank_text, top3))
    lines.append(table(("id", "type", "wording", "gold", "rank of gold", "top 3"), per_question))

    times = [r["retrieval_ms"] for r in rows]
    median_ms = statistics.median(times)
    lines += ["", "## Time (measured, bge-m3 loaded, qwen3:8b not loaded)", ""]
    lines.append(f"Median time per question: {median_ms:.1f} ms.")
    write(f"retrieval_{split}", rows, "\n".join(lines))


def score(q, result):
    final = result["final"]
    invalid = bool(result["checks"].get("invalid_output") or result.get("error"))
    gold = set(q["gold"])
    if not gold:
        abstained = not final["answerable"] and not invalid
        return {"correct": abstained, "abstained": abstained, "invalid_output": invalid}

    cited = False
    for c in final["citations"]:
        if c in gold:
            cited = True
            break

    gold_articles = {g.split("(")[0] for g in gold}
    if not q["fine"]:
        fine_ok = None
    else:
        fine_ok = final["fine"] == q["fine"]

    correct = final["answerable"] and cited and fine_ok is not False
    abstained = not final["answerable"] and not invalid

    wrong_part = False
    if not cited:
        for c in final["citations"]:
            if c.split("(")[0] in gold_articles:
                wrong_part = True
                break

    gold_retrieved = bool(gold & set(result["retrieved"]))
    return {
        "correct": correct,
        "abstained": abstained,
        "invalid_output": invalid,
        "citation_correct": cited,
        "right_article_wrong_part": wrong_part,
        "fine_correct": fine_ok,
        "gold_retrieved": gold_retrieved,
    }


def error_row(question, strict, error):
    from answer import LLM_MODEL, NOT_FOUND, NUM_CTX

    final = {"answerable": False, "answer": NOT_FOUND, "citations": [], "fine": [None, None]}
    return {
        "question": question["question"],
        "version": question["version"],
        "method": "dense",
        "k": K,
        "strict": strict,
        "model": LLM_MODEL,
        "num_ctx": NUM_CTX,
        "retrieved": [],
        "raw": None,
        "raw_text": None,
        "checks": {"verified": False},
        "error": error,
        "final": final,
        "prompt_tokens": None,
        "output_tokens": None,
        "done_reason": None,
        "context_full": False,
        "load_ms": None,
        "generation_ms": None,
        "retrieval_ms": None,
        "wall_ms": None,
    }


def answers(split, strict):
    import requests

    from answer import Answerer, unload, warm_up

    questions = load_questions(split)
    held = [q["id"] for q in questions if q["type"] == "adversarial"]
    if held:
        print(f"skipped {', '.join(held)}: adversarial questions are answered later, with the injection test")
    questions = [q for q in questions if q["type"] != "adversarial"]
    answerer = Answerer(K, strict)
    rows = []
    try:
        warm_up()
        for n, q in enumerate(questions, 1):
            try:
                result = answerer.answer(q["question"], q["version"])
            except requests.RequestException as e:
                result = error_row(q, strict, repr(e))
            row = {}
            for key in KEYS:
                row[key] = q[key]
            row["gold_version"] = q["version"]
            row.update(result)
            row["score"] = score(q, result)
            rows.append(row)
            if row["score"]["correct"]:
                status = "ok"
            else:
                status = "wrong"
            print(f"{n}/{len(questions)} {q['id']}: {status}", flush=True)
    finally:
        unload()
    report(rows, split, strict)


def name_of(split, strict):
    if strict:
        suffix = ""
    else:
        suffix = "_not_strict"
    return f"answers_{split}{suffix}"


def report(rows, split, strict):
    answerable = [r for r in rows if r["gold"]]
    unanswerable = [r for r in rows if not r["gold"]]
    with_fine = [r for r in answerable if r["fine"]]
    claimed = []
    for r in rows:
        raw = r["raw"] or {}
        if raw.get("answerable"):
            claimed.append(r)

    def count(selected, key):
        total = 0
        for r in selected:
            if r["score"][key]:
                total += 1
        return total

    if strict:
        mode = "strict"
    else:
        mode = "not strict"
    lines = [f"# Answers on {split} ({len(rows)} questions, bge-m3 retrieval, top {K}, {mode})", ""]

    verified = 0
    for r in claimed:
        if r["checks"].get("verified"):
            verified += 1

    n_answerable = len(answerable)
    n_unanswerable = len(unanswerable)
    body = [
        ("correct answer (right part cited, right fine if asked)", frac(count(answerable, "correct"), n_answerable)),
        ("gold part among the retrieved sources", frac(count(answerable, "gold_retrieved"), n_answerable)),
        ("gold part cited", frac(count(answerable, "citation_correct"), n_answerable)),
        ("right article but wrong part cited", frac(count(answerable, "right_article_wrong_part"), n_answerable)),
        ("fine correct", frac(count(with_fine, "fine_correct"), len(with_fine))),
        ("abstained although ANK has the answer", frac(count(answerable, "abstained"), n_answerable)),
        ("abstained on unanswerable questions", frac(count(unanswerable, "abstained"), n_unanswerable)),
        ("invalid, cut-off or failed model outputs", frac(count(rows, "invalid_output"), len(rows))),
        ("model answers that passed the citation check", frac(verified, len(claimed))),
    ]
    lines.append(table(("metric", "count"), body))

    by = defaultdict(list)
    for r in rows:
        for g in groups(r):
            by[g].append(r)
    lines += ["", "## Correct answers by type and wording", ""]
    group_rows = []
    for g in sorted(by):
        group_rows.append((g, frac(count(by[g], "correct"), len(by[g]))))
    lines.append(table(("questions", "correct"), group_rows))

    timed = [r for r in rows if r["generation_ms"] is not None]
    if timed:
        gen = [r["generation_ms"] / 1000 for r in timed]
        prompt_tokens = [r["prompt_tokens"] for r in timed]
        output_tokens = [r["output_tokens"] for r in timed]
        retrieval_times = [r["retrieval_ms"] for r in timed]
        context_full = 0
        for r in timed:
            if r["context_full"]:
                context_full += 1
        prompt_mean = statistics.mean(prompt_tokens)
        output_mean = statistics.mean(output_tokens)
        gen_median = statistics.median(gen)
        gen_max = max(gen)
        retrieval_median = statistics.median(retrieval_times)
        lines += ["", "## Resources (measured; models loaded before the first question)", ""]
        resources = [
            ("prompt tokens, mean", f"{prompt_mean:.0f}"),
            ("output tokens, mean", f"{output_mean:.0f}"),
            ("generation time (prompt and output), median / max", f"{gen_median:.1f} s / {gen_max:.1f} s"),
            ("retrieval time, median", f"{retrieval_median:.0f} ms"),
            ("prompts that filled the context window", frac(context_full, len(timed))),
        ]
        lines.append(table(("measure", "value"), resources))

    def checks_cell(r):
        if r["score"]["invalid_output"]:
            return "invalid output"
        raw = r["raw"] or {}
        if not raw.get("answerable"):
            return "no answer"
        if r["checks"].get("verified"):
            return "pass"
        failed = []
        for k, v in r["checks"].items():
            if v is False and k != "verified":
                failed.append(k)
        return "fail: " + ", ".join(failed)

    lines += ["", "## Per question", ""]
    per_question = []
    for r in rows:
        gold_text = ";".join(r["gold"])
        if not gold_text:
            gold_text = "none"
        retrieved_text = ", ".join(r["retrieved"])
        answer_text = " ".join(r["final"]["answer"].split())
        answer_text = answer_text.replace("|", "/")
        if r["score"]["correct"]:
            correct_text = "yes"
        else:
            correct_text = "no"
        per_question.append((r["id"], r["type"], gold_text, r["version"], retrieved_text,
                             answer_text, checks_cell(r), correct_text))
    header = ("id", "type", "gold", "version", "retrieved", "final answer", "checks", "correct")
    lines.append(table(header, per_question))
    write(name_of(split, strict), rows, "\n".join(lines))


def load_results(split, strict):
    path = RESULTS / f"{name_of(split, strict)}.jsonl"
    if not path.exists():
        raise SystemExit(f"{path.relative_to(ROOT)} does not exist; run evaluate.py answers first")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rows.append(json.loads(line))
    return rows


def rescore(split, strict):
    questions = {}
    for q in load_questions(split):
        questions[q["id"]] = q
    rows = []
    for r in load_results(split, strict):
        q = questions.get(r["id"])
        if q is None or q["question"] != r["question"]:
            print(f"skipped {r['id']}: the question changed or was removed")
            continue
        row = dict(r)
        for key in KEYS:
            row[key] = q[key]
        row["gold_version"] = q["version"]
        row["score"] = score(q, r)
        rows.append(row)
    report(rows, split, strict)


def main():
    parser = argparse.ArgumentParser(description="Evaluate retrieval and answers on a question split")
    sub = parser.add_subparsers(dest="command", required=True)

    r = sub.add_parser("retrieval", help="hit@1, recall@5 and MRR@10 for bge-m3")
    r.add_argument("--split", default="dev", choices=["dev", "test"])

    a = sub.add_parser("answers", help="answer every question with qwen3:8b and score the answers")
    a.add_argument("--split", default="dev", choices=["dev", "test"])
    a.add_argument("--no-strict", action="store_true")

    s = sub.add_parser("rescore", help="score stored answers again without calling the models")
    s.add_argument("--split", default="dev", choices=["dev", "test"])
    s.add_argument("--no-strict", action="store_true")

    args = parser.parse_args()
    if args.command == "retrieval":
        retrieval(args.split)
    elif args.command == "answers":
        answers(args.split, not args.no_strict)
    else:
        rescore(args.split, not args.no_strict)


if __name__ == "__main__":
    main()
