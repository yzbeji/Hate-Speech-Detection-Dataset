from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import suppress
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Request, Response, sync_playwright

from comment_extractor.models import CommentRecord

LOGGER = logging.getLogger(__name__)

MAX_IDLE_ROUNDS = 30
CLICK_TIMEOUT_MS = 5_000


class PlaywrightCommentExtractor:
    """Opens a post in a browser, scrolls, and collects comments from the site's own JSON responses.

    Subclasses describe one platform: which responses hold comments and how to turn them into records.
    """

    platform = ""
    banner_buttons: tuple[str, ...] = ()
    load_more_selectors: tuple[str, ...] = ()

    def __init__(
        self,
        *,
        profile_dir: str = ".browser-profile",
        headless: bool = True,
        scroll_delay_s: float = 1.1,
        manual_wait_seconds: int = 0,
    ) -> None:
        self.profile_dir = profile_dir
        self.headless = headless
        self.scroll_delay_s = scroll_delay_s
        self.manual_wait_seconds = max(0, manual_wait_seconds)
        self._records: dict[str, CommentRecord] = {}
        self._post_id = ""
        self._source_url = ""

    # --- platform hooks -------------------------------------------------

    def infer_post_id(self, source_url: str) -> str:
        raise NotImplementedError

    def is_comment_response(self, url: str) -> bool:
        raise NotImplementedError

    def iter_comment_payloads(self, payload: object) -> Iterator[tuple[dict, str | None]]:
        """Yield (raw comment, parent comment id) pairs found in a JSON payload."""
        raise NotImplementedError

    def build_record(self, raw: dict, parent_id: str | None) -> CommentRecord | None:
        raise NotImplementedError

    def open_comments(self, page: Page) -> None:
        """Make the comment list visible, if the page needs a click for it."""

    def scroll(self, page: Page) -> None:
        with suppress(Exception):
            page.mouse.wheel(0, 3000)

    def extract_from_dom(self, page: Page, *, max_comments: int) -> list[CommentRecord]:
        """Fallback when no comment JSON was captured."""
        return []

    # --- shared flow ----------------------------------------------------

    def extract(self, source_url: str, max_comments: int) -> list[CommentRecord]:
        self._records = {}
        # Share links carry tracking parameters (e.g. ?exln=) that can identify the sharer.
        self._source_url = urlsplit(source_url)._replace(query="", fragment="").geturl()
        self._post_id = self.infer_post_id(self._source_url)

        with sync_playwright() as p:
            # A persistent profile keeps the login between runs.
            context = p.chromium.launch_persistent_context(self.profile_dir, headless=self.headless, locale="en-US")
            page = context.pages[0] if context.pages else context.new_page()
            page.on("requestfinished", self._on_request_finished)

            try:
                page.goto(source_url, wait_until="domcontentloaded", timeout=60_000)
                self._click_first_visible(page, [f"button:has-text('{text}')" for text in self.banner_buttons])
                self._wait_for_manual_interaction()
                self.open_comments(page)
                self._scroll_until_done(page, max_comments)

                if len(self._records) < max_comments and not page.is_closed():
                    for record in self.extract_from_dom(page, max_comments=max_comments):
                        self._records.setdefault(record.comment_id, record)
            except (KeyboardInterrupt, PlaywrightError):
                pass
            finally:
                with suppress(Exception):
                    context.close()

        records = sorted(self._records.values(), key=lambda r: r.created_at)
        return records[:max_comments]

    def _scroll_until_done(self, page: Page, max_comments: int) -> None:
        idle_rounds = 0
        previous_count = 0
        while len(self._records) < max_comments and idle_rounds < MAX_IDLE_ROUNDS and not page.is_closed():
            self.scroll(page)
            time.sleep(self.scroll_delay_s)
            for selector in self.load_more_selectors:
                self._click_if_visible(page, selector)

            current_count = len(self._records)
            idle_rounds = idle_rounds + 1 if current_count == previous_count else 0
            previous_count = current_count

    def _on_request_finished(self, request: Request) -> None:
        # Listening on "requestfinished" guarantees the response body is complete.
        with suppress(Exception):
            response = request.response()
            if response:
                self._on_response(response)

    def _on_response(self, response: Response) -> None:
        if not self.is_comment_response(response.url.lower()):
            return
        try:
            payload = response.json()
        except Exception:
            return

        LOGGER.debug("Captured: %s", response.url)
        for raw, parent_id in self.iter_comment_payloads(payload):
            try:
                record = self.build_record(raw, parent_id)
            except Exception:
                continue
            if record:
                self._records.setdefault(record.comment_id, record)

    def _wait_for_manual_interaction(self) -> None:
        if not self.headless and self.manual_wait_seconds > 0:
            time.sleep(self.manual_wait_seconds)

    @staticmethod
    def _click_if_visible(page: Page, selector: str) -> bool:
        try:
            button = page.locator(selector).first
            if button.is_visible():
                # The button may sit outside the scrolled view; scrolling it into view takes time.
                button.click(timeout=CLICK_TIMEOUT_MS)
                return True
        except Exception as exc:
            LOGGER.debug("Click on %s failed: %s", selector, exc)
        return False

    @classmethod
    def _click_first_visible(cls, page: Page, selectors: list[str]) -> bool:
        return any(cls._click_if_visible(page, selector) for selector in selectors)
