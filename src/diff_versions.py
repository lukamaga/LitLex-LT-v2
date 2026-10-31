import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from ltnum import amounts, norm

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
SIMILAR = 0.6


def load(version):
    path = PROCESSED / f"ank_{version}.jsonl"
    articles = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        article = row["article"]
        if article not in articles:
            articles[article] = []
        articles[article].append(row)
    return articles


def masked(text):
    return re.sub(r"\d+", "#", norm(text))


def fines(text):
    return amounts(text)


def align(old, new):
    a = [masked(row["text"]) for row in old]
    b = [masked(row["text"]) for row in new]
    pairs = []
    used_a = set()
    used_b = set()

    matcher = SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pairs.append((i1 + k, j1 + k))
                used_a.add(i1 + k)
                used_b.add(j1 + k)
        elif tag == "replace":
            scored = []
            for i in range(i1, i2):
                for j in range(j1, j2):
                    ratio = SequenceMatcher(None, a[i], b[j], autojunk=False).ratio()
                    scored.append((ratio, i, j))
            scored.sort(reverse=True)
            for ratio, i, j in scored:
                if ratio < SIMILAR:
                    break
                if i not in used_a and j not in used_b:
                    pairs.append((i, j))
                    used_a.add(i)
                    used_b.add(j)

    leftover = {}
    for i in range(len(old)):
        if i not in used_a:
            leftover[old[i]["id"]] = i
    for j, row in enumerate(new):
        if j not in used_b and row["id"] in leftover:
            i = leftover.pop(row["id"])
            pairs.append((i, j))
            used_a.add(i)
            used_b.add(j)

    removed = []
    for i in range(len(old)):
        if i not in used_a:
            removed.append(old[i])
    added = []
    for j in range(len(new)):
        if j not in used_b:
            added.append(new[j])

    pairs.sort()
    matched = []
    for i, j in pairs:
        matched.append((old[i], new[j]))
    return matched, removed, added


def entry(kind, a, b):
    if kind in ("removed", "repealed"):
        source = a
    else:
        source = b

    new_id = None
    if b:
        new_id = b["id"]
    old_id = None
    if a:
        old_id = a["id"]

    fine_changed = False
    if kind in ("changed", "repealed"):
        fine_changed = fines(a["text"]) != fines(b["text"])

    old_text = None
    if a:
        old_text = a["text"]
    new_text = None
    if b:
        new_text = b["text"]

    return {
        "id": new_id,
        "old_id": old_id,
        "label": source["label"],
        "kind": kind,
        "title": source["title"],
        "fine_changed": fine_changed,
        "old_text": old_text,
        "new_text": new_text,
    }


def compare(old_parts, new_parts):
    if not new_parts:
        return [entry("removed", a, None) for a in old_parts]
    if not old_parts:
        return [entry("added", None, b) for b in new_parts]

    stub = new_parts[0]
    if len(new_parts) == 1 and stub["repealed"] and stub["part"] is None:
        all_old_repealed = True
        for a in old_parts:
            if not a["repealed"]:
                all_old_repealed = False
                break
        if not all_old_repealed:
            rows = []
            for a in old_parts:
                if not a["repealed"]:
                    rows.append(entry("repealed", a, stub))
            return rows

    rows = []
    pairs, removed, added = align(old_parts, new_parts)
    for a, b in pairs:
        if norm(a["text"]) == norm(b["text"]):
            if a["id"] != b["id"]:
                rows.append(entry("renumbered", a, b))
            elif a["title"] != b["title"]:
                rows.append(entry("title_changed", a, b))
        elif b["repealed"] and not a["repealed"]:
            rows.append(entry("repealed", a, b))
        else:
            rows.append(entry("changed", a, b))
    for a in removed:
        rows.append(entry("removed", a, None))
    for b in added:
        rows.append(entry("added", None, b))
    return rows


def article_sort_key(article):
    numbers = []
    for x in article.split("-"):
        numbers.append(int(x))
    return numbers


def main():
    parser = argparse.ArgumentParser(description="List article parts that differ between two ANK versions")
    parser.add_argument("old", nargs="?", default="2026-01-12")
    parser.add_argument("new", nargs="?", default="2026-11-01")
    args = parser.parse_args()

    old = load(args.old)
    new = load(args.new)
    all_articles = old.keys() | new.keys()
    changes = []
    for article in sorted(all_articles, key=article_sort_key):
        old_parts = old.get(article, [])
        new_parts = new.get(article, [])
        changes += compare(old_parts, new_parts)

    out = PROCESSED / f"changes_{args.old}_{args.new}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for row in changes:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    kinds = ("changed", "added", "removed", "repealed", "renumbered", "title_changed")
    counts = {}
    for kind in kinds:
        count = 0
        for c in changes:
            if c["kind"] == kind:
                count += 1
        counts[kind] = count

    articles = set()
    for c in changes:
        if c["kind"] == "renumbered":
            continue
        part_id = c["id"]
        if not part_id:
            part_id = c["old_id"]
        articles.add(part_id.split("(")[0])

    fine_count = 0
    for c in changes:
        if c["fine_changed"]:
            fine_count += 1

    print(f"{args.old} -> {args.new}: {len(changes)} entries, real changes in {len(articles)} articles")
    print(counts)
    print(f"fine changed: {fine_count}")
    print(f"-> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
