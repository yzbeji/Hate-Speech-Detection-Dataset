from __future__ import annotations

import re

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
# Usernames may contain dots (@ana.pop); \w+ alone would leak the part after the dot.
MENTION_RE = re.compile(r"(?<!\w)@[\w.]+", re.UNICODE)
WS_RE = re.compile(r"\s+")


def normalize_comment_text(text: str) -> str:
    """Normalize text while keeping emojis for downstream sexism/sentiment signals."""
    cleaned = URL_RE.sub(" ", text)
    cleaned = MENTION_RE.sub(" ", cleaned)
    cleaned = WS_RE.sub(" ", cleaned).strip().lower()
    return cleaned


def contains_link(text: str) -> bool:
    return bool(URL_RE.search(text))


def contains_mention(text: str) -> bool:
    return bool(MENTION_RE.search(text))
