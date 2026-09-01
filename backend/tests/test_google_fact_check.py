import pytest
from unittest.mock import MagicMock, patch

from app.config import settings
from app.external_feeds.base import FeedNotConfiguredError
from app.external_feeds.google_fact_check import FactCheckResult, aggregate_verdict, normalize_rating, search

SAMPLE_RESPONSE = {
    "claims": [
        {
            "text": "There's a flood in Nepal",
            "claimReview": [
                {
                    "publisher": {"name": "PolitiFact"},
                    "url": "https://example.com/review1",
                    "title": "Old video shared as current Nepal flood",
                    "textualRating": "False",
                }
            ],
        }
    ]
}


def test_search_raises_when_not_configured():
    with patch.object(settings, "google_fact_check_api_key", None):
        with pytest.raises(FeedNotConfiguredError):
            search("flood in Nepal")


def test_search_parses_claim_reviews_with_mocked_requests():
    with patch.object(settings, "google_fact_check_api_key", "dummy-key-for-test"):
        with patch("app.external_feeds.google_fact_check.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE)
            mock_get.return_value.raise_for_status = lambda: None
            results = search("flood in Nepal")

    assert len(results) == 1
    assert results[0].publisher == "PolitiFact"
    assert results[0].normalized_rating == "FALSE"


def test_normalize_false_variants():
    assert normalize_rating("False") == "FALSE"
    assert normalize_rating("Pants on Fire") == "FALSE"
    assert normalize_rating("Mostly False") == "FALSE"
    assert normalize_rating("Misleading") == "FALSE"


def test_normalize_true_variants():
    assert normalize_rating("True") == "TRUE"
    assert normalize_rating("Correct") == "TRUE"


def test_normalize_hedged_as_mixed():
    assert normalize_rating("Half True") == "MIXED"
    assert normalize_rating("Mostly True") == "MIXED"


def test_normalize_unknown_for_unrecognized_text():
    assert normalize_rating("Satire") == "UNKNOWN"
    assert normalize_rating("") == "UNKNOWN"


def _result(rating: str) -> FactCheckResult:
    return FactCheckResult(
        publisher="Test Publisher", title="t", url=None, textual_rating=rating, normalized_rating=rating
    )


def test_aggregate_false_wins_over_true():
    verdict = aggregate_verdict([_result("TRUE"), _result("FALSE")])
    assert verdict == "FALSE"


def test_aggregate_true_when_no_false():
    verdict = aggregate_verdict([_result("TRUE"), _result("MIXED")])
    assert verdict == "TRUE"


def test_aggregate_none_when_no_results():
    assert aggregate_verdict([]) is None
