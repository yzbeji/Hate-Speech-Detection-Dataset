from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import suppress

from playwright.sync_api import Page

from comment_extractor.extractors.base import PlaywrightCommentExtractor
from comment_extractor.models import CommentRecord
from comment_extractor.processors.text_normalizer import contains_link, contains_mention, normalize_comment_text

POST_ID_RE = re.compile(r"/(?:p|reel|tv)/([\w-]+)")
# The post caption has the same shape as a comment, and user objects are never comments.
SKIPPED_KEYS = {"caption", "edge_media_to_caption", "user", "owner"}
# Keys under which a comment carries its replies (API v1 and the older GraphQL shape).
REPLY_KEYS = {"preview_child_comments", "child_comments", "edge_threaded_comments"}
# Scrolls the scrollable box holding the most comments (each comment has a <time>); false if none.
SCROLL_COMMENT_LIST_JS = """() => {
  const lists = [...document.querySelectorAll('div, ul')].filter(e => {
    const overflow = getComputedStyle(e).overflowY;
    return (overflow === 'auto' || overflow === 'scroll') && e.scrollHeight > e.clientHeight && e.querySelector('time');
  });
  if (!lists.length) return false;
  const count = e => e.querySelectorAll('time').length;
  const list = lists.reduce((a, b) => (count(b) > count(a) ? b : a));
  list.scrollTop = list.scrollHeight;
  return true;
}"""


def _count(raw: dict, flat_key: str, edge_key: str) -> int:
    return raw.get(flat_key) or (raw.get(edge_key) or {}).get("count") or 0


class InstagramExtractor(PlaywrightCommentExtractor):
    platform = "instagram"
    banner_buttons = ("Decline optional cookies", "Only allow essential cookies", "Allow all cookies", "Not now")
    load_more_selectors = (
        "svg[aria-label='Load more comments']",
        # :text-matches targets the button's own span, not the containers around it.
        "span:text-matches('^View (all [0-9]+ )?repl', 'i')",
        "button:has-text('Not now')",
    )

    def infer_post_id(self, source_url: str) -> str:
        match = POST_ID_RE.search(source_url)
        return match.group(1) if match else "unknown"

    def is_comment_response(self, url: str) -> bool:
        return "graphql" in url or "comments" in url

    def iter_comment_payloads(
        self, payload: object, parent_id: str | None = None
    ) -> Iterator[tuple[dict, str | None]]:
        if isinstance(payload, list):
            for item in payload:
                yield from self.iter_comment_payloads(item, parent_id)
            return
        if not isinstance(payload, dict):
            return

        is_comment = self._looks_like_comment(payload)
        if is_comment:
            yield payload, parent_id
        for key, value in payload.items():
            if key in SKIPPED_KEYS:
                continue
            child_parent = str(payload.get("pk") or payload.get("id")) if is_comment and key in REPLY_KEYS else parent_id
            yield from self.iter_comment_payloads(value, child_parent)

    @staticmethod
    def _looks_like_comment(node: dict) -> bool:
        return (
            isinstance(node.get("text"), str)
            and bool(node.get("pk") or node.get("id"))
            and "created_at" in node
            and ("user" in node or "owner" in node)
        )

    def build_record(self, raw: dict, parent_id: str | None) -> CommentRecord | None:
        comment_id = str(raw.get("pk") or raw.get("id") or "").strip()
        text = raw["text"].strip()
        normalized = normalize_comment_text(text)
        if not comment_id or not normalized:
            return None

        user = raw.get("user") or raw.get("owner") or {}
        return CommentRecord(
            comment_id=comment_id,
            post_id=self._post_id,
            author_username=str(user.get("username") or ""),
            author_display_name=str(user.get("full_name") or ""),
            raw_text=text,
            normalized_text=normalized,
            created_at=raw["created_at"],
            like_count=_count(raw, "comment_like_count", "edge_liked_by"),
            reply_count=_count(raw, "child_comment_count", "edge_threaded_comments"),
            parent_comment_id=str(raw.get("parent_comment_id") or parent_id or "") or None,
            contains_mention=contains_mention(text),
            contains_link=contains_link(text),
            source_url=self._source_url,
        )

    def scroll(self, page: Page) -> None:
        # The comment list is a small scrollable box whose position depends on the layout,
        # so scroll the element itself instead of the mouse wheel.
        with suppress(Exception):
            if page.evaluate(SCROLL_COMMENT_LIST_JS):
                return
        super().scroll(page)

    def extract_from_dom(self, page: Page, *, max_comments: int) -> list[CommentRecord]:
        """The first comments come embedded in the page as JSON, not as a network response."""
        records: list[CommentRecord] = []
        for script in page.locator("script[type='application/json']").all_text_contents():
            try:
                payload = json.loads(script)
            except json.JSONDecodeError:
                continue
            for raw, parent_id in self.iter_comment_payloads(payload):
                with suppress(Exception):
                    if record := self.build_record(raw, parent_id):
                        records.append(record)
        return records[:max_comments]
