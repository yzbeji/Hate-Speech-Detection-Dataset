from __future__ import annotations

from urllib.parse import urlparse

from comment_extractor.extractors.base import PlaywrightCommentExtractor
from comment_extractor.extractors.instagram import InstagramExtractor
from comment_extractor.extractors.tiktok import TikTokExtractor

EXTRACTORS: dict[str, type[PlaywrightCommentExtractor]] = {
    "instagram.com": InstagramExtractor,
    "tiktok.com": TikTokExtractor,
}


def extractor_for(url: str) -> type[PlaywrightCommentExtractor]:
    host = urlparse(url).netloc.lower()
    for domain, extractor in EXTRACTORS.items():
        if host == domain or host.endswith("." + domain):
            return extractor
    raise ValueError(f"unsupported site: {url} (supported: {', '.join(EXTRACTORS)})")
