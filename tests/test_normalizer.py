from comment_extractor.processors.text_normalizer import normalize_comment_text


def test_normalizer_keeps_emoji_and_removes_mentions_and_urls() -> None:
    text = "@user This is wild 😡 https://example.com"
    normalized = normalize_comment_text(text)
    assert "@user" not in normalized
    assert "http" not in normalized
    assert "😡" in normalized
    assert normalized == "this is wild 😡"


def test_normalizer_removes_whole_dotted_mention() -> None:
    assert normalize_comment_text("@ana.pop salut") == "salut"
