import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import requests

API = "https://get.data.gov.lt/datasets/gov/lrsk/teises_aktai/Suvestine"
ANK_DOC_ID = "4ebe66c0262311e5bf92d6af3f6a2e8b"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DEFAULT_DATES = ["2026-01-12", "2026-11-01"]


def query(expr):
    resp = requests.get(API + "?" + expr, timeout=180)
    resp.raise_for_status()
    return resp.json()["_data"]


def list_versions():
    expr = f'dokumento_id="{ANK_DOC_ID}"&select(suvestines_id,galioja_nuo,galioja_iki)&limit(2000)'
    rows = query(expr)
    return sorted(rows, key=lambda r: r["galioja_nuo"])


def version_on(day, versions):
    for v in versions:
        start = v["galioja_nuo"][:10]
        end = v["galioja_iki"]
        if not end:
            end = "9999-12-31"
        end = end[:10]
        if start <= day <= end:
            return v
    raise SystemExit(f"No consolidated version of ANK is valid on {day}")


def fetch(day, versions):
    v = version_on(day, versions)
    version_id = v["suvestines_id"]
    record = query(f'suvestines_id="{version_id}"')[0]
    text = record["tekstas_lt"]
    start = record["galioja_nuo"][:10]
    valid_to = None
    if record["galioja_iki"]:
        valid_to = record["galioja_iki"][:10]
    meta = {
        "valid_on": day,
        "valid_from": start,
        "valid_to": valid_to,
        "suvestines_id": record["suvestines_id"],
        "source_url": record["nuoroda"],
        "api_url": API + f'?suvestines_id="{record["suvestines_id"]}"',
        "revision": record["_revision"],
        "updated_at_source": record["suv_duom_atnaujinimas"],
        "fetched": date.today().isoformat(),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "chars": len(text),
        "license": "CC BY 4.0, Register of Legal Acts (TAR) via data.gov.lt",
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    text_path = RAW_DIR / f"ank_{start}.txt"
    meta_path = RAW_DIR / f"ank_{start}.json"
    text_path.write_text(text, encoding="utf-8")
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
    meta_path.write_text(meta_json + "\n", encoding="utf-8")
    return meta


def main():
    parser = argparse.ArgumentParser(description="Download consolidated versions of ANK from data.gov.lt")
    parser.add_argument("dates", nargs="*", default=DEFAULT_DATES,
                        help="dates (YYYY-MM-DD) the versions must be valid on")
    args = parser.parse_args()

    versions = list_versions()
    print(f"{len(versions)} consolidated versions listed")
    for day in args.dates:
        meta = fetch(day, versions)
        valid_from = meta["valid_from"]
        valid_to = meta["valid_to"]
        short_hash = meta["sha256"][:12]
        print(f"{day}: version {valid_from} to {valid_to}, {meta['chars']} chars, sha256 {short_hash}")


if __name__ == "__main__":
    main()
