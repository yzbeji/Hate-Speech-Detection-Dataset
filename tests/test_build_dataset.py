import json

import pytest

from build_dataset import anonymize_text, build, username_pattern


def raw_comment(**overrides) -> dict:
    comment = {
        "comment_id": "1",
        "author_username": "ana.pop",
        "raw_text": "@ana.pop vezi https://x.ro 😡",
        "created_at": "2026-01-01T00:00:00Z",
        "parent_comment_id": None,
        "source_url": "https://www.instagram.com/p/abc/",
    }
    return comment | overrides


def test_anonymize_text_replaces_dotted_mentions_and_links() -> None:
    assert anonymize_text("@ana.pop vezi https://x.ro 😡") == "@USER vezi URL 😡"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ana.Pop esti praf", "@USER esti praf"),
        ("@ ana.pop. exact", "@USER. exact"),
        ("@/ana.pop da", "@USER da"),
        ("pentru ion_23 e mesajul", "pentru @USER e mesajul"),
        ("andrei are dreptate", "andrei are dreptate"),  # plain-word username is not touched
        ("xana.popescu", "xana.popescu"),  # only whole usernames
    ],
)
def test_anonymize_text_replaces_known_usernames_written_without_mention(text, expected) -> None:
    usernames = username_pattern(["ana.pop", "ion_23", "andrei"])
    assert anonymize_text(text, usernames) == expected


def test_build_pseudonymizes_and_deduplicates(tmp_path) -> None:
    raw = tmp_path / "raw.jsonl"
    rows = [
        raw_comment(),
        raw_comment(),  # duplicate comment_id
        raw_comment(comment_id="2", parent_comment_id="1", raw_text="ok"),
    ]
    raw.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    records = build([raw], salt="s")

    assert len(records) == 2
    parent, reply = records
    assert parent["text"] == "@USER vezi URL 😡"
    assert parent["platform"] == "instagram"
    assert "ana.pop" not in json.dumps(records)
    assert "instagram.com" not in json.dumps(records)
    assert reply["is_reply"] and reply["parent_id"] == parent["id"]
