from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.external_feeds.base import FeedNotConfiguredError
from app.external_feeds.newsapi_feed import search

SAMPLE_RESPONSE = {
    "articles": [
        {
            "source": {"name": "The Hindu"},
            "title": "Heavy rains cause flooding in Bengaluru",
            "url": "https://example.com/article1",
            "publishedAt": "2026-08-29T10:00:00Z",
        }
    ]
}


def test_search_raises_when_not_configured():
    with patch.object(settings, "news_api_key", None):
        with pytest.raises(FeedNotConfiguredError):
            search("flooding in Bengaluru")


def test_search_parses_articles_with_mocked_requests():
    with patch.object(settings, "news_api_key", "dummy-key-for-test"):
        with patch("app.external_feeds.newsapi_feed.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE)
            mock_get.return_value.raise_for_status = lambda: None
            results = search("flooding in Bengaluru")

    assert len(results) == 1
    assert results[0].source_name == "The Hindu"
    assert results[0].url == "https://example.com/article1"
    assert results[0].published_at is not None
