from __future__ import annotations

import hashlib
import time
from collections.abc import Iterator
from datetime import datetime, timezone

from playwright.sync_api import Page

from comment_extractor.extractors.base import PlaywrightCommentExtractor
from comment_extractor.models import CommentRecord
from comment_extractor.processors.text_normalizer import contains_link, contains_mention, normalize_comment_text

COMMENT_LIST_KEYS = ("comments", "comment_list", "items", "item_list")
DOM_COMMENT_SELECTORS = (
    "[data-e2e='comment-level-1']",
    "[data-e2e='comment-item']",
    "div[class*='CommentItem']",
    "div[class*='CommentContainer']",
)


class TikTokExtractor(PlaywrightCommentExtractor):
    platform = "tiktok"
    banner_buttons = ("Reject all", "Decline", "Not now", "Close")
    load_more_selectors = (
        "button:has-text('See more comments')",
        "button:has-text('View more comments')",
        "button:has-text('Load more')",
    )

    def infer_post_id(self, source_url: str) -> str:
        parts = [p for p in source_url.rstrip("/").split("/") if p]
        if "video" in parts:
            return parts[parts.index("video") + 1].split("?")[0]
        return "unknown"

    def is_comment_response(self, url: str) -> bool:
        return "comment" in url

    def iter_comment_payloads(self, payload: object) -> Iterator[tuple[dict, str | None]]:
        if isinstance(payload, dict):
            for key in COMMENT_LIST_KEYS:
                if isinstance(payload.get(key), list):
                    for item in payload[key]:
                        yield item, None
            for value in payload.values():
                yield from self.iter_comment_payloads(value)
        elif isinstance(payload, list):
            for item in payload:
                yield from self.iter_comment_payloads(item)

    def build_record(self, raw: dict, parent_id: str | None) -> CommentRecord | None:
        if not isinstance(raw, dict):
            return None

        comment_id = str(raw.get("cid") or raw.get("id") or raw.get("comment_id") or "").strip()
        text = str(raw.get("text") or raw.get("content") or raw.get("desc") or "").strip()
        normalized = normalize_comment_text(text)
        if not comment_id or not normalized:
            return None

        user = raw.get("user") or raw.get("user_info") or {}
        created_raw = raw.get("create_time")
        created_at = created_raw if isinstance(created_raw, (int, float)) else datetime.now(timezone.utc)

        return CommentRecord(
            comment_id=comment_id,
            post_id=self._post_id or "unknown",
            author_username=str(user.get("unique_id") or user.get("username") or ""),
            author_display_name=str(user.get("nickname") or ""),
            raw_text=text,
            normalized_text=normalized,
            created_at=created_at,
            like_count=raw.get("digg_count", 0),
            reply_count=raw.get("reply_comment_total", 0),
            parent_comment_id=parent_id,
            contains_mention=contains_mention(text),
            contains_link=contains_link(text),
            source_url=self._source_url,
        )

    def open_comments(self, page: Page) -> None:
        selectors = [
            "[data-e2e='browse-comment-icon']",
            "[data-e2e='comment-icon']",
            "button[aria-label*='comment' i]",
            "[aria-label*='comment' i]",
        ]
        if self._click_first_visible(page, selectors):
            time.sleep(1)

    def extract_from_dom(self, page: Page, *, max_comments: int) -> list[CommentRecord]:
        handles = []
        for selector in DOM_COMMENT_SELECTORS:
            try:
                handles = page.query_selector_all(selector)
            except Exception:
                continue
            if handles:
                break

        results = []
        for idx, handle in enumerate(handles[:max_comments]):
            try:
                text = (handle.inner_text() or "").strip()
            except Exception:
                continue
            normalized = normalize_comment_text(text)
            if not normalized:
                continue
            results.append(
                CommentRecord(
                    # The DOM exposes no comment id or date: derive a stable id, timestamp = now.
                    comment_id=hashlib.sha1(f"{idx}:{text}".encode()).hexdigest()[:16],
                    post_id=self._post_id,
                    raw_text=text,
                    normalized_text=normalized,
                    created_at=datetime.now(timezone.utc),
                    contains_mention=contains_mention(text),
                    contains_link=contains_link(text),
                    source_url=self._source_url,
                )
            )
        return results
