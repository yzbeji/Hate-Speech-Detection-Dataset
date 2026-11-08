from datetime import timezone

from comment_extractor.models import CommentRecord


def test_comment_record_from_unix_timestamp() -> None:
    record = CommentRecord(
        comment_id="1",
        post_id="vid",
        raw_text="hello 😄",
        normalized_text="hello 😄",
        created_at=1_700_000_000,
    )

    assert record.created_at.tzinfo == timezone.utc
    assert record.like_count == 0
    assert record.reply_count == 0


def test_comment_record_reads_its_own_jsonl_output() -> None:
    record = CommentRecord(comment_id="1", post_id="p", raw_text="x", normalized_text="x", created_at=1_700_000_000)
    assert CommentRecord.model_validate_json(record.model_dump_json()) == record
