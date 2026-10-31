import json
import re

import numpy as np

import retrieve
from parse_ank import OUT_DIR
from retrieve import VERSIONS, Retriever, load_units, split_long


def test_versions():
    assert VERSIONS == ["2026-01-12", "2026-11-01"]


def test_split_long_keeps_all_text():
    pieces = {}
    for u in load_units("2026-11-01"):
        if u["id"] not in pieces:
            pieces[u["id"]] = []
        pieces[u["id"]].append(u["text"])

    path = OUT_DIR / "ank_2026-11-01.jsonl"
    original = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        original[r["id"]] = r["text"]

    split = [i for i, p in pieces.items() if len(p) > 1]
    assert split
    for i in split:
        joined = re.sub(r"\s+", " ", " ".join(pieces[i]))
        expected = re.sub(r"\s+", " ", original[i])
        assert joined == expected
    assert split_long("trumpas tekstas") == ["trumpas tekstas"]


def test_dense_ranks_each_part_once(monkeypatch):
    r = Retriever("2026-11-01", dense=False)
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(len(r.units), 8)).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    r.vectors = vectors / norms

    split = None
    for i, u in enumerate(r.units):
        if u["uid"].endswith("#2"):
            split = i
            break
    assert split is not None

    def fake_embed(texts):
        return r.vectors[[split]]

    monkeypatch.setattr(retrieve, "embed", fake_embed)
    ranking = r.dense("x", 50)
    ids = [p for p, _ in ranking]
    assert len(ids) == 50
    assert len(set(ids)) == 50
    expected_first = (r.units[split]["id"], (split, ranking[0][1][1]))
    assert ranking[0] == expected_first
    hit_ids = [h["id"] for h in r.search("x", 5)]
    assert hit_ids == ids[:5]
