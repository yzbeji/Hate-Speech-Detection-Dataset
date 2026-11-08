from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CommentRecord(BaseModel):
    comment_id: str = Field(..., min_length=1)
    post_id: str = Field(..., min_length=1)
    author_username: str = ""
    author_display_name: str = ""
    raw_text: str = Field(..., min_length=1)
    normalized_text: str = Field(..., min_length=1)
    created_at: datetime
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    like_count: int = 0
    reply_count: int = 0
    parent_comment_id: Optional[str] = None
    contains_mention: bool = False
    contains_link: bool = False
    source_url: str = ""

    @field_validator("created_at", mode="before")
    @classmethod
    def _coerce_created_at(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):  # ISO string, as written to JSONL
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("created_at must be a datetime, Unix timestamp or ISO string")

    @field_validator("like_count", "reply_count", mode="before")
    @classmethod
    def _ensure_non_negative_int(cls, value: object) -> int:
        converted = int(value or 0)
        if converted < 0:
            return 0
        return converted
