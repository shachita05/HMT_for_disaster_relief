"""
Google Fact Check Tools API -- real, keyed integration (see .env's
GOOGLE_FACT_CHECK_API_KEY). Unlike USGS/GDACS/ReliefWeb (periodic,
claim-independent event feeds matched geographically after the fact by
evidence_matcher.py), this API is a claim-text search: you query it with
the actual submitted claim text and it returns other publishers'
(PolitiFact, AFP Fact Check, BOOM, etc.) fact-check reviews of matching
claims, each with a free-text "textual rating" (e.g. "False", "Mostly
True", "Pants on Fire"). That shape doesn't fit ExternalFeedSource's
no-argument fetch() -- see pipeline_service.py for the per-claim call
site; stub_feeds.py's GoogleFactCheckFeedSource still exists only so the
periodic scheduler can canary-check credentials/connectivity for the
/api/feeds/status dot.

Rating normalization is a small ordered rule set (checked FALSE-ish
keywords before TRUE-ish, so e.g. "Mostly False" or "Half True" land in
the bucket a human would expect) -- documented and defensible, not a
trained classifier, matching this project's existing rule-based-scoring
convention (see src/utils/reliability_scorer.py's own docstring).
"""
import logging
from dataclasses import dataclass
from typing import Literal

import requests

from app.config import settings
from app.external_feeds.base import FeedNotConfiguredError
from app.external_feeds.feed_status import registry

logger = logging.getLogger(__name__)

SEARCH_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

Rating = Literal["FALSE", "TRUE", "MIXED", "UNKNOWN"]

_FALSE_KEYWORDS = ("false", "fake", "hoax", "pants on fire", "incorrect", "fabricated", "misleading", "scam")
_TRUE_KEYWORDS = ("true", "correct", "accurate", "confirmed", "verified")
_HEDGE_KEYWORDS = ("half", "mostly", "partly", "partial", "mixture", "mixed")


@dataclass
class FactCheckResult:
    publisher: str
    title: str
    url: str | None
    textual_rating: str
    normalized_rating: Rating


def normalize_rating(textual_rating: str) -> Rating:
    text = (textual_rating or "").strip().lower()
    if not text:
        return "UNKNOWN"
    if any(k in text for k in _FALSE_KEYWORDS):
        return "FALSE"
    if any(h in text for h in _HEDGE_KEYWORDS):
        return "MIXED"
    if any(k in text for k in _TRUE_KEYWORDS):
        return "TRUE"
    return "UNKNOWN"


def aggregate_verdict(results: list[FactCheckResult]) -> Rating | None:
    """FALSE beats TRUE beats MIXED -- a single credible false-rating from
    a real fact-checker is significant enough to flag even if other
    reviews found the same claim (or a similar one) true."""
    ratings = {r.normalized_rating for r in results}
    if "FALSE" in ratings:
        return "FALSE"
    if "TRUE" in ratings:
        return "TRUE"
    if "MIXED" in ratings:
        return "MIXED"
    return None


def search(query: str, page_size: int = 5) -> list[FactCheckResult]:
    """Raises FeedNotConfiguredError if no API key is set. Raises
    requests.RequestException/ValueError on a real network/parsing
    failure -- deliberately NOT swallowed here (unlike ExternalFeedSource
    subclasses) so callers can tell "no results" apart from "the lookup
    failed"; each caller (stub_feeds.py's canary poll, pipeline_service.py's
    per-claim lookup) decides for itself how to handle that."""
    if not settings.google_fact_check_api_key:
        raise FeedNotConfiguredError("GOOGLE_FACT_CHECK_API_KEY is not set -- see .env.example")

    resp = requests.get(
        SEARCH_URL,
        params={"query": query, "key": settings.google_fact_check_api_key, "pageSize": page_size},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[FactCheckResult] = []
    for claim in data.get("claims", []):
        for review in claim.get("claimReview", []):
            textual_rating = review.get("textualRating", "")
            publisher = (review.get("publisher") or {}).get("name") or "Unknown publisher"
            results.append(
                FactCheckResult(
                    publisher=publisher,
                    title=claim.get("text") or review.get("title") or query,
                    url=review.get("url"),
                    textual_rating=textual_rating,
                    normalized_rating=normalize_rating(textual_rating),
                )
            )
    return results


def canary_check() -> None:
    """Called periodically by stub_feeds.py's GoogleFactCheckFeedSource
    purely to report an "ok"/"error" status on /api/feeds/status -- a
    generic query just to prove the key/connection works, independent of
    any real claim."""
    results = search("flood")
    registry.record_success("GoogleFactCheck", len(results))
