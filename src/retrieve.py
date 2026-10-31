import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
INDEX = ROOT / "data" / "index"

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "bge-m3"
DEFAULT_VERSION = "2026-11-01"
VERSIONS = []
for processed_file in PROCESSED.glob("ank_*.jsonl"):
    VERSIONS.append(processed_file.stem.removeprefix("ank_"))
VERSIONS.sort()
MAX_CHARS = 1500
CANDIDATES = 100


def split_long(text):
    if len(text) <= MAX_CHARS:
        return [text]
    before_list_item = r"(?<=[;:.])\s+(?=\d+\)\s)"
    before_sentence = r"(?<=\.)\s+(?=[A-ZĄČĘĖĮŠŲŪŽ])"
    pieces = re.split(before_list_item + "|" + before_sentence, text)
    out = []
    buf = ""
    for piece in pieces:
        new_length = len(buf) + len(piece) + 1
        if buf and new_length > MAX_CHARS:
            out.append(buf)
            buf = piece
        else:
            buf = f"{buf} {piece}".strip()
    if buf:
        out.append(buf)
    return out


def load_units(version):
    units = []
    path = PROCESSED / f"ank_{version}.jsonl"
    if not path.is_file():
        raise SystemExit(f"ANK version {version} is not parsed; available: {', '.join(VERSIONS)}")
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        pieces = split_long(row["text"])
        for i, piece in enumerate(pieces, 1):
            if len(pieces) == 1:
                uid = row["id"]
            else:
                uid = f"{row['id']}#{i}"
            unit = dict(row)
            unit["uid"] = uid
            unit["text"] = piece
            units.append(unit)
    return units


def embed(texts, batch=32):
    vectors = []
    for start in range(0, len(texts), batch):
        body = {"model": EMBED_MODEL, "input": texts[start:start + batch]}
        resp = requests.post(f"{OLLAMA}/api/embed", json=body, timeout=600)
        resp.raise_for_status()
        vectors.extend(resp.json()["embeddings"])
    matrix = np.asarray(vectors, dtype=np.float32)
    lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / lengths


def model_digest():
    resp = requests.get(f"{OLLAMA}/api/tags", timeout=60)
    tags = resp.json()["models"]
    for m in tags:
        if m["name"].split(":")[0] == EMBED_MODEL:
            return m["digest"]
    return None


class Retriever:
    def __init__(self, version=DEFAULT_VERSION, dense=True):
        self.version = version
        self.units = load_units(version)
        if dense:
            self.vectors = self._dense_index()
        else:
            self.vectors = None

    @staticmethod
    def dense_text(unit):
        return f"{unit['header']}\n{unit['text']}"

    def _dense_index(self):
        docs = [self.dense_text(u) for u in self.units]
        joined = "\n\0".join(docs)
        fingerprint = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        digest = model_digest()
        vec_path = INDEX / f"dense_{self.version}.npy"
        meta_path = INDEX / f"dense_{self.version}.json"
        if vec_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            vectors = np.load(vec_path)
            same_docs = meta.get("fingerprint") == fingerprint
            same_model = meta.get("model") == EMBED_MODEL
            same_digest = meta.get("digest") == digest
            if same_docs and same_model and same_digest and len(vectors) == len(docs):
                return vectors
        print(f"embedding {len(docs)} units with {EMBED_MODEL}...")
        vectors = embed(docs)
        INDEX.mkdir(parents=True, exist_ok=True)
        np.save(vec_path, vectors)
        meta = {"model": EMBED_MODEL, "digest": digest, "units": len(docs), "fingerprint": fingerprint}
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return vectors

    def dense(self, query, n=CANDIDATES):
        query_vector = embed([query])[0]
        scores = self.vectors @ query_vector
        order = np.argsort(-scores, kind="stable")
        best = {}
        for i in order:
            part = self.units[i]["id"]
            if part not in best:
                best[part] = (int(i), float(scores[i]))
                if len(best) == n:
                    break
        return list(best.items())

    def search(self, query, k=5):
        ranking = self.dense(query)
        hits = []
        for part, position in ranking[:k]:
            index, score = position
            hit = dict(self.units[index])
            hit["score"] = score
            hits.append(hit)
        return hits


def main():
    parser = argparse.ArgumentParser(description="Search ANK article parts with bge-m3")
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--version", choices=VERSIONS, default=DEFAULT_VERSION)
    args = parser.parse_args()

    retriever = Retriever(args.version)
    hits = retriever.search(args.query, args.k)
    for rank, hit in enumerate(hits, 1):
        title = hit["title"][:80]
        print(f"  {rank}. {hit['label']:<10} {hit['score']:.4f}  {title}")


if __name__ == "__main__":
    main()
