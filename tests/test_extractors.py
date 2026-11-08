import pytest

from comment_extractor.extractors import InstagramExtractor, TikTokExtractor, extractor_for

URL = "https://www.instagram.com/p/DV1W5Fhk19i/"

# Shape of the GraphQL comments connection, with a reply that names its parent.
GRAPHQL_PAYLOAD = {
    "data": {
        "xdt_api__v1__media__media_id__comments__connection": {
            "edges": [
                {"node": {"pk": "1", "text": "Bravo @ana.pop", "created_at": 1700000000,
                          "user": {"username": "ion", "full_name": "Ion"},
                          "comment_like_count": 5, "child_comment_count": 1, "parent_comment_id": None}},
                {"node": {"pk": "2", "text": "De acord", "created_at": 1700000100,
                          "user": {"username": "ana.pop"}, "parent_comment_id": "1"}},
            ]
        }
    }
}

# Shape of the API v1 media response: the caption must not be taken for a comment,
# replies are nested under their parent.
V1_PAYLOAD = {
    "caption": {"pk": "99", "text": "Descrierea postarii", "created_at": 1699990000, "user": {"username": "page"}},
    "comments": [
        {"pk": "3", "text": "Primul", "created_at": 1700000200, "user": {"username": "maria"},
         "preview_child_comments": [
             {"pk": "4", "text": "Raspuns", "created_at": 1700000300, "user": {"username": "dan"}}
         ]}
    ],
}


def records(payload: dict) -> dict:
    extractor = InstagramExtractor()
    extractor._source_url = URL
    extractor._post_id = extractor.infer_post_id(URL)
    built = (extractor.build_record(raw, parent) for raw, parent in extractor.iter_comment_payloads(payload))
    return {r.comment_id: r for r in built if r}


def test_instagram_graphql_comments_and_replies() -> None:
    found = records(GRAPHQL_PAYLOAD)
    assert set(found) == {"1", "2"}
    assert found["1"].author_username == "ion"
    assert found["1"].like_count == 5 and found["1"].reply_count == 1
    assert found["1"].parent_comment_id is None
    assert found["2"].parent_comment_id == "1"
    assert found["1"].post_id == "DV1W5Fhk19i"


def test_instagram_v1_skips_caption_and_links_nested_replies() -> None:
    found = records(V1_PAYLOAD)
    assert set(found) == {"3", "4"}
    assert found["4"].parent_comment_id == "3"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/reel/abc/", InstagramExtractor),
        ("https://www.tiktok.com/@user/video/123", TikTokExtractor),
    ],
)
def test_extractor_for_picks_platform(url, expected) -> None:
    assert extractor_for(url) is expected


def test_extractor_for_rejects_other_sites() -> None:
    with pytest.raises(ValueError):
        extractor_for("https://evil-instagram.com/p/abc/")
