from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.external_feeds.mastodon_feed import search_hashtags, to_hashtag

RECENT = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
OLD = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")

SAMPLE_TIMELINE = [
    {
        "id": "1",
        "content": "<p>Flood in <b>Nepal</b> confirmed</p>",
        "url": "https://example.social/@user1/1",
        "created_at": RECENT,
        "account": {"acct": "user1@example.social"},
        "favourites_count": 3,
        "reblogs_count": 1,
        "replies_count": 0,
    },
    {
        "id": "2",
        "content": "<p>Old post, should be filtered by recency</p>",
        "url": "https://example.social/@user2/2",
        "created_at": OLD,
        "account": {"acct": "user2@example.social"},
        "favourites_count": 0,
        "reblogs_count": 0,
        "replies_count": 0,
    },
]


def test_to_hashtag_strips_spaces_and_symbols():
    assert to_hashtag("New Delhi") == "newdelhi"
    assert to_hashtag("Flood") == "flood"
    assert to_hashtag("") == ""


def test_search_hashtags_parses_and_filters_by_recency():
    since = datetime.now(timezone.utc) - timedelta(days=3)
    with patch("app.external_feeds.mastodon_feed.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_TIMELINE)
        mock_get.return_value.raise_for_status = lambda: None
        posts = search_hashtags(["flood"], since=since)

    assert len(posts) == 1
    assert posts[0].account_handle == "user1@example.social"
    assert "Flood in Nepal confirmed" in posts[0].content_text
    assert "<b>" not in posts[0].content_text


def test_search_hashtags_dedupes_across_tags():
    since = datetime.now(timezone.utc) - timedelta(days=3)
    with patch("app.external_feeds.mastodon_feed.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_TIMELINE)
        mock_get.return_value.raise_for_status = lambda: None
        posts = search_hashtags(["flood", "nepal"], since=since)

    # same post id "1" appears in both tag timelines -- must not be duplicated
    ids = [p.id for p in posts]
    assert ids.count("1") == 1
