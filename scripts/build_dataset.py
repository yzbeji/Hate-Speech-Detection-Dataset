"""Build the public, anonymized dataset from raw scraper output.

Raw files (data/raw/*.jsonl) hold personal data and never leave the machine.
The output keeps only pseudonymized ids and anonymized text (see docs/data-proposal.md, section 3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import secrets
from collections.abc import Iterable
from pathlib import Path

from comment_extractor.processors.text_normalizer import MENTION_RE, URL_RE

SALT_ENV = "DATASET_SALT"
DISTINCTIVE_USERNAME_RE = re.compile(r"[._\d]")


def pseudonym(value: str | None, salt: str) -> str | None:
    if not value:
        return None
    return hashlib.sha256((salt + value).encode("utf-8")).hexdigest()[:12]


def username_pattern(usernames: Iterable[str]) -> re.Pattern | None:
    """Match known usernames written without a proper mention: "ana.pop", "@ ana.pop", "@/ana.pop"."""
    # shortcut: only usernames with '.', '_' or a digit, so ordinary words are never replaced;
    # a username that looks like a plain word ("andrei") stays in the text when written without '@'.
    names = sorted({u.lower() for u in usernames if u and DISTINCTIVE_USERNAME_RE.search(u)}, key=len, reverse=True)
    if not names:
        return None
    alternatives = "|".join(map(re.escape, names))
    return re.compile(rf"(?<![\w.])(?:@[\s/]*)?(?:{alternatives})(?!\w)", re.IGNORECASE)


def anonymize_text(text: str, usernames: re.Pattern | None = None) -> str:
    text = MENTION_RE.sub("@USER", URL_RE.sub("URL", text))
    if usernames:
        text = usernames.sub("@USER", text)
    return text.strip()


def platform_of(raw: dict) -> str:
    return "tiktok" if "tiktok.com" in raw.get("source_url", "") else "instagram"


def to_record(raw: dict, salt: str, usernames: re.Pattern | None = None) -> dict:
    platform = platform_of(raw)
    prefix = "tt" if platform == "tiktok" else "ig"
    parent_id = raw.get("parent_comment_id")
    return {
        "id": f"{prefix}_{pseudonym(raw['comment_id'], salt)}",
        "platform": platform,
        "text": anonymize_text(raw["raw_text"], usernames),
        "post_hash": pseudonym(raw.get("source_url"), salt),
        "author_hash": pseudonym(raw.get("author_username"), salt),
        "parent_id": f"{prefix}_{pseudonym(parent_id, salt)}" if parent_id else None,
        "is_reply": parent_id is not None,
        "created_at": raw["created_at"],
        "like_count": raw.get("like_count", 0),
        "reply_count": raw.get("reply_count", 0),
        "contains_mention": raw.get("contains_mention", False),
        "contains_link": raw.get("contains_link", False),
    }


def read_raw(paths: list[Path]) -> list[dict]:
    """Read scraper JSONL files, keeping the first occurrence of each (platform, comment_id)."""
    seen: set[tuple[str, str]] = set()
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    logging.warning("%s:%s is not valid JSON, skipped", path, line_no)
                    continue
                key = (platform_of(raw), raw["comment_id"])
                if key not in seen:
                    seen.add(key)
                    rows.append(raw)
    return rows


def build(paths: list[Path], salt: str) -> list[dict]:
    rows = read_raw(paths)
    usernames = username_pattern(raw.get("author_username", "") for raw in rows)
    records = [to_record(raw, salt, usernames) for raw in rows]
    for record in records:
        # Hard stop: a leaked mention or link must never reach the published file.
        if MENTION_RE.search(record["text"].replace("@USER", "")) or URL_RE.search(record["text"]):
            raise ValueError(f"anonymization failed for {record['id']}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inputs", nargs="*", type=Path, help="Raw JSONL files (default: data/raw/*.jsonl)")
    parser.add_argument("--output", type=Path, default=Path("data/comments.jsonl"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    inputs = args.inputs or sorted(Path("data/raw").glob("*.jsonl"))
    if not inputs:
        parser.error("no input files: pass them as arguments or put them in data/raw/")

    salt = os.environ.get(SALT_ENV)
    if not salt:
        salt = secrets.token_hex(16)
        logging.warning("%s not set: using a random salt, ids will differ from previous builds", SALT_ENV)

    records = build(inputs, salt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    logging.info("Wrote %s records from %s file(s) to %s", len(records), len(inputs), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
