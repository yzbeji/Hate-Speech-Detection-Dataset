"""Remove duplicate comments from the anonymized dataset.

Batches built with different salts give the same comment different ids, so duplicates are found by
(text, created_at) instead. The first occurrence is kept; replies pointing to a removed comment are
re-pointed to the kept one, and leftover comments of a re-scraped post are moved to the kept post_hash.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path


def key(record: dict) -> tuple[str, str]:
    return record["text"], record["created_at"]


def dedupe(records: list[dict]) -> list[dict]:
    kept: dict[tuple[str, str], dict] = {}
    id_map: dict[str, str] = {}
    post_map: dict[str, str] = {}
    for record in records:
        first = kept.setdefault(key(record), record)
        if first is not record:
            id_map[record["id"]] = first["id"]
            if first["post_hash"] != record["post_hash"]:
                post_map[record["post_hash"]] = first["post_hash"]

    result = []
    for record in kept.values():
        record = dict(record)
        record["post_hash"] = post_map.get(record["post_hash"], record["post_hash"])
        if record.get("parent_id"):
            record["parent_id"] = id_map.get(record["parent_id"], record["parent_id"])
        result.append(record)
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path("data/comments.jsonl"))
    args = parser.parse_args()

    with args.path.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    result = dedupe(records)
    with args.path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in result:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    logging.info("Removed %s duplicates, %s records left in %s", len(records) - len(result), len(result), args.path)


if __name__ == "__main__":
    main()
