import argparse
import json
import re
import subprocess
import time

from evaluate import KEYS, RESULTS, frac, load_questions, table, write
from ltnum import stated

BASE_MODEL = "llama3-8b-base"
V1_MODEL = "litlex-v1"
V1_PROMPT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{}

### Response:
"""
MAX_NEW_TOKENS = 256
CLOSED = """You are a legal information assistant for the Lithuanian Code of Administrative Offences (ANK).
Answer the question from what you know, in Lithuanian, in one or two sentences. Name the article part the way ANK does, for example "ANK 488 str. 1 d." for a part or "ANK 108 str." for an article without parts, and give the fine for natural persons in euros.
If you do not know the answer or ANK does not cover the question, reply exactly: Atsakymo į šį klausimą ANK nerasta."""
SYSTEMS = ("base", "v1", "closed", "rag")
SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
REFUSAL = re.compile(r"nerast|nėra\b|nereglamentuo|nežino", re.I)
CITE = re.compile(
    r"\b(\d+)"
    r"(?:\s*([⁰¹²³⁴⁵⁶⁷⁸⁹]+)|-(\d+))?"
    r"\s*(?:str\b\.?|straipsn\w*)"
    r"(?:\s*,?\s*(\d+)\s*(?:d\b\.?|dal\w*))?",
    re.I,
)


def named(text):
    out = []
    for m in CITE.finditer(text or ""):
        article = m[1]
        if m[2]:
            article = article + "-" + m[2].translate(SUPERSCRIPT)
        elif m[3]:
            article = article + "-" + m[3]
        if m[4]:
            out.append(f"{article}({m[4]})")
        else:
            out.append(article)
    return out


def judge(q, text):
    if not text:
        text = ""
    parts = named(text)
    found, singles = stated(text)
    gold = set(q["gold"])
    abstained = not parts and not found and not singles
    if not gold:
        refused = bool(REFUSAL.search(text))
        return {"named": parts, "fine": None, "correct": abstained and refused, "abstained": abstained}

    hit = False
    for p in parts:
        if p in gold:
            hit = True
            break
        if p.endswith("(1)") and p[:-3] in gold:
            hit = True
            break

    if found:
        fine = list(found[0])
    else:
        fine = None
    if not q["fine"]:
        fine_ok = None
    else:
        fine_ok = fine == q["fine"]

    gold_articles = {g.split("(")[0] for g in gold}
    wrong_part = False
    if not hit:
        for p in parts:
            if p.split("(")[0] in gold_articles:
                wrong_part = True
                break

    return {
        "named": parts,
        "fine": fine,
        "part_named": hit,
        "right_article_wrong_part": wrong_part,
        "fine_correct": fine_ok,
        "abstained": abstained,
        "correct": hit and fine_ok is not False,
    }


def mcnemar(b, c):
    from math import comb

    n = b + c
    if n == 0:
        return 1.0
    total = 0
    for i in range(min(b, c) + 1):
        total += comb(n, i)
    p = 2 * total / 2 ** n
    return min(1.0, p)


def questions_for(split):
    return [q for q in load_questions(split) if q["type"] != "adversarial"]


def run_llama(split, adapter):
    import requests

    from answer import OLLAMA, SEED

    if adapter:
        model = V1_MODEL
        system = "v1"
    else:
        model = BASE_MODEL
        system = "base"
    rows = []
    try:
        for q in questions_for(split):
            options = {"temperature": 0, "seed": SEED, "num_predict": MAX_NEW_TOKENS, "num_ctx": 2048}
            body = {
                "model": model,
                "prompt": V1_PROMPT.format(q["question"]),
                "raw": True,
                "stream": False,
                "options": options,
            }
            t0 = time.perf_counter()
            resp = requests.post(f"{OLLAMA}/api/generate", json=body, timeout=900)
            resp.raise_for_status()
            data = resp.json()
            row = {}
            for key in KEYS:
                row[key] = q[key]
            row["question"] = q["question"]
            row["system"] = system
            row["answer"] = data["response"].strip()
            row["output_tokens"] = data.get("eval_count")
            row["seconds"] = round(time.perf_counter() - t0, 1)
            row["model"] = model
            rows.append(row)
            print(f"{q['id']}: {row['answer'][:100]}", flush=True)
    finally:
        subprocess.run(["ollama", "stop", model], capture_output=True)
    if adapter:
        name = "LitLex v1"
    else:
        name = "Llama 3 8B without the adapter"
    title = f"# {name} on {split} ({len(rows)} questions, greedy, at most {MAX_NEW_TOKENS} new tokens)"
    write(f"reference_{split}_{system}", rows, title)


def run_closed(split):
    from answer import LLM_MODEL, chat, unload

    rows = []
    try:
        for q in questions_for(split):
            t0 = time.perf_counter()
            messages = [
                {"role": "system", "content": CLOSED},
                {"role": "user", "content": f"Klausimas: {q['question']}"},
            ]
            data = chat(messages)
            row = {}
            for key in KEYS:
                row[key] = q[key]
            row["question"] = q["question"]
            row["system"] = "closed"
            row["answer"] = data["message"]["content"].strip()
            row["output_tokens"] = data.get("eval_count")
            row["seconds"] = round(time.perf_counter() - t0, 1)
            row["model"] = LLM_MODEL
            rows.append(row)
            print(f"{q['id']}: {row['answer'][:100]}", flush=True)
    finally:
        unload()
    write(f"reference_{split}_closed", rows, f"# qwen3:8b without retrieval on {split} ({len(rows)} questions)")


def load(name):
    path = RESULTS / f"{name}.jsonl"
    if not path.exists():
        raise SystemExit(f"results/{name}.jsonl does not exist; run that step first")
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[r["id"]] = r
    return rows


def report(split):
    qs = {}
    for q in questions_for(split):
        qs[q["id"]] = q

    runs = {}
    for s in SYSTEMS:
        if s == "rag":
            file_name = f"answers_{split}"
        else:
            file_name = f"reference_{split}_{s}"
        kept = {}
        for i, r in load(file_name).items():
            if i in qs:
                kept[i] = r
        runs[s] = kept

    for name, rows in runs.items():
        same = set(rows) == set(qs)
        if same:
            for i in qs:
                if rows[i]["question"] != qs[i]["question"]:
                    same = False
                    break
        if not same:
            raise SystemExit(f"the {name} run answered other questions; run it again")

    answers = {}
    for s, rows in runs.items():
        texts = {}
        for i, r in rows.items():
            if s == "rag":
                texts[i] = r["final"]["answer"]
            else:
                texts[i] = r["answer"]
        answers[s] = texts

    scores = {}
    for s in SYSTEMS:
        system_scores = {}
        for i in qs:
            system_scores[i] = judge(qs[i], answers[s][i])
        scores[s] = system_scores

    answerable = [i for i in qs if qs[i]["gold"]]
    unanswerable = [i for i in qs if not qs[i]["gold"]]
    with_fine = [i for i in answerable if qs[i]["fine"]]
    title = {
        "base": "Llama 3 8B, no retrieval",
        "v1": "LitLex v1, no retrieval",
        "closed": "qwen3:8b, no retrieval",
        "rag": "qwen3:8b with bge-m3 retrieval",
    }

    intro = "Every answer is scored from its text in the same way: "
    intro += "correct means a gold part is named and the first fine stated is the gold fine; "
    intro += "on an unanswerable question, correct means the answer says it was not found and "
    intro += "gives no ANK part and no amount."
    lines = [f"# Closed-book references on {split} ({len(qs)} questions, the injected ones left out)", "", intro, ""]

    metrics = [
        ("correct on answerable questions", answerable, "correct"),
        ("gold part named", answerable, "part_named"),
        ("right article but wrong part", answerable, "right_article_wrong_part"),
        ("fine correct", with_fine, "fine_correct"),
        ("no part and no amount on answerable questions", answerable, "abstained"),
        ("said not found on unanswerable questions", unanswerable, "correct"),
    ]
    body = []
    for label, ids, key in metrics:
        row = [label]
        for s in SYSTEMS:
            count = 0
            for i in ids:
                if scores[s][i][key]:
                    count += 1
            row.append(frac(count, len(ids)))
        body.append(row)

    header = ["metric"]
    for s in SYSTEMS:
        header.append(title[s])
    lines.append(table(header, body))

    pairs_intro = "The first two change one thing: the adapter, then the retrieval. "
    pairs_intro += "The last one changes the model, the training "
    pairs_intro += "and the retrieval at once, so it is a reference, not a controlled comparison."
    lines += ["", "## Paired comparisons (exact McNemar test, all questions)", "", pairs_intro, ""]
    pairs = []
    for a, b in (("v1", "base"), ("rag", "closed"), ("rag", "v1")):
        only_a = 0
        only_b = 0
        for i in qs:
            a_right = scores[a][i]["correct"]
            b_right = scores[b][i]["correct"]
            if a_right and not b_right:
                only_a += 1
            if b_right and not a_right:
                only_b += 1
        p_value = mcnemar(only_a, only_b)
        pairs.append((f"{title[a]} vs {title[b]}", only_a, only_b, f"{p_value:.3f}"))
    lines.append(table(("comparison", "only the first right", "only the second right", "p"), pairs))

    lines += ["", "## Per question", ""]
    rows = []
    for i, q in qs.items():
        gold_text = ";".join(q["gold"])
        if not gold_text:
            gold_text = "none"
        if q["fine"]:
            fine_text = "-".join([str(x) for x in q["fine"]])
        else:
            fine_text = ""
        row = [i, q["type"], gold_text, fine_text]
        for s in SYSTEMS:
            text = " ".join(answers[s][i].split())
            text = text.replace("|", "/")[:220]
            if scores[s][i]["correct"]:
                text += " (yes)"
            else:
                text += " (no)"
            row.append(text)
        rows.append(row)

    header = ["id", "type", "gold", "fine"]
    for s in SYSTEMS:
        header.append(title[s])
    lines.append(table(header, rows))

    out = []
    for i in qs:
        item = {"id": i, "question": qs[i]["question"]}
        for s in SYSTEMS:
            entry = {"answer": answers[s][i]}
            entry.update(scores[s][i])
            item[s] = entry
        out.append(item)
    write(f"reference_{split}", out, "\n".join(lines))


def main():
    description = "Closed-book reference runs: Llama 3 8B, LitLex v1 and qwen3:8b without retrieval"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("command", choices=["base", "v1", "closed", "report"])
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    args = parser.parse_args()
    if args.command in ("base", "v1"):
        run_llama(args.split, adapter=args.command == "v1")
    elif args.command == "closed":
        run_closed(args.split)
    else:
        report(args.split)


if __name__ == "__main__":
    main()
