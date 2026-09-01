"""
Wraps the EXISTING, unmodified analysis pipeline (src/analyze_claim.py) and
persists its result to the DB. This file does not reimplement any ML/NLP
logic -- it only maps analyze_claim()'s return dict onto ORM rows.

IMPORTANT -- do not "helpfully" clean/normalize `text` before calling
analyze_claim() here. TfidfLogRegClassifier.predict() and
SourceVerifier.verify() (called inside analyze_claim()) both run on
whatever text they're given, and the shipped model was trained on raw,
unpreprocessed IFND headline text (see src/build_baseline.py). Any new
cleaning step inserted ahead of that call would silently shift the token
distribution the model sees at inference time away from what it was fit
on, degrading accuracy with no error raised. See ARCHITECTURE.md and
src/preprocessing/text_preprocessor.py's own docstring for the full
explanation. The preprocessing module in this project is deliberately
wired only in front of external-feed text (app/external_feeds/), never here.
"""
import sys
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from analyze_claim import analyze_claim  # noqa: E402
from location.geocode_lookup import get_coordinates  # noqa: E402
from verification.source_verifier import MATCH_THRESHOLD  # noqa: E402
from utils.reliability_scorer import score_reliability  # noqa: E402

import logging

from app.db.models import Claim, Location, Evidence
from app.external_feeds import google_fact_check, mastodon_feed, newsapi_feed
from app.external_feeds.base import FeedNotConfiguredError
from app.external_feeds.evidence_matcher import ClaimGeoContext, find_matches
from app.external_feeds.scheduler import get_cached_events
from app.services import social_corroboration
from app.services.alerts_service import maybe_create_alert

logger = logging.getLogger(__name__)


def _topic_terms(result: dict) -> tuple[str | None, str | None]:
    """(disaster_type, place) extracted from analyze_claim()'s result --
    shared by _news_query (NewsAPI) and the Mastodon hashtag list below, so
    both external searches key off the same signal instead of duplicating
    this extraction logic."""
    loc = result.get("location") or {}
    place = loc.get("city") or loc.get("district") or loc.get("state")
    disaster_type = result.get("disaster_type")
    disaster_type = disaster_type if disaster_type and disaster_type != "None" else None
    return disaster_type, place


def _news_query(result: dict, text: str) -> str:
    """NewsAPI's /v2/everything does a strict all-terms match, not a fuzzy/
    semantic one (unlike Google Fact Check's claims:search) -- passing a
    full raw claim sentence very often returns zero results simply because
    not every word co-occurs in any one article. A short, targeted query
    built from what the pipeline already extracted (disaster type +
    location) matches real coverage far more often. Falls back to the raw
    text only if neither signal was extracted."""
    disaster_type, place = _topic_terms(result)
    if disaster_type and place:
        return f"{disaster_type} {place}"
    if disaster_type or place:
        return disaster_type or place
    return text


def analyze_and_persist(
    db: Session, text: str, source: str = "manual", source_url: str | None = None
) -> Claim:
    result = analyze_claim(text)

    claim = Claim(
        text=text,
        source=source,
        source_url=source_url,
        submitted_at=datetime.now(timezone.utc),
        disaster_type=result["disaster_type"],
        all_disaster_types=result["all_disaster_types"],
        classification=result["prediction"],
        confidence=result["confidence_raw"],
        top_terms=list(result["top_terms"]),  # list of (term, contribution) tuples -> JSON array of arrays
        priority=result["priority"],
        priority_score=result["priority_score"],
        priority_reasons=result["priority_reasons"],
        verification_status="matched" if result["verification"]["matched"] else "not_matched",
        reason=result["reason"],
    )

    primary_coords = None
    for loc in result["all_locations"]:
        coords = get_coordinates(loc["city"], loc["state"])
        if loc["is_primary"]:
            primary_coords = coords
        claim.locations.append(
            Location(
                matched_text=loc["text"],
                match_level=loc["level"],
                match_type=loc["match_type"],
                locality=loc["locality"],
                city=loc["city"],
                district=loc["district"],
                state=loc["state"],
                pin_code=loc["pin_code"],
                latitude=coords.latitude,
                longitude=coords.longitude,
                coordinate_precision=coords.precision,
                is_primary=loc["is_primary"],
            )
        )

    if result["verification"]["matched"]:
        claim.evidence.append(
            Evidence(
                source="IFND_corpus",
                evidence_type="corpus_similarity",
                description=(
                    f'Similar to a stored TRUE-labeled record: '
                    f'"{result["verification"]["matched_claim"]}"'
                ),
                matched_confidence=result["verification"]["similarity_raw"],
                # source_note is deliberately NOT dropped here -- it's
                # surfaced by the API/UI alongside this Evidence row so the
                # "not live NDMA/IMD/PIB" caveat travels with the data,
                # not just in code comments.
            )
        )

    # Live external evidence -- matched against the in-memory cache the
    # background scheduler (app/external_feeds/scheduler.py) refreshes
    # periodically. If the scheduler hasn't run yet (e.g. disabled in
    # tests) the cache is simply empty, which correctly yields "no live
    # evidence found" rather than a fabricated match.
    location_level = result["location"]["match_level"] if result["location"] else None
    live_matches = []
    evidence_type_matches = None
    if primary_coords is not None:
        ctx = ClaimGeoContext(
            disaster_type=result["disaster_type"],
            latitude=primary_coords.latitude,
            longitude=primary_coords.longitude,
            location_level=location_level,
            country_hint="India",
            submitted_at=claim.submitted_at,
        )
        cached_events = get_cached_events()
        live_matches = find_matches(ctx, cached_events, require_type=True)
        if live_matches:
            evidence_type_matches = True
        elif find_matches(ctx, cached_events, require_type=False):
            # something geographically/recency-relevant happened nearby,
            # just not of the claimed disaster type -- see
            # evidence_matcher.find_matches' docstring
            evidence_type_matches = False

    for event in live_matches:
        claim.evidence.append(
            Evidence(
                source=event.source,
                url=event.url,
                evidence_type="live_feed_match",
                description=event.description or event.title,
                event_timestamp=event.event_timestamp,
                matched_confidence=1.0,  # binary match (type+geo+recency all satisfied), not a similarity score
            )
        )

    # Independent fact-checker lookup (Google Fact Check Tools API) --
    # never allowed to break claim analysis if unconfigured/unreachable,
    # same "external machinery must not take down the request" rule as
    # everything else in external_feeds/. See google_fact_check.py for why
    # this is a per-claim call rather than the scheduler's cached feeds.
    fact_check_results: list[google_fact_check.FactCheckResult] = []
    try:
        fact_check_results = google_fact_check.search(text)
    except FeedNotConfiguredError:
        pass
    except Exception:
        logger.exception("Google Fact Check lookup failed for submitted claim")

    for fc in fact_check_results:
        if fc.normalized_rating not in ("FALSE", "TRUE", "MIXED"):
            continue
        claim.evidence.append(
            Evidence(
                source=fc.publisher,
                url=fc.url,
                evidence_type=f"fact_check_{fc.normalized_rating.lower()}",
                description=f"{fc.textual_rating}: {fc.title} (via Google Fact Check Tools API)",
                matched_confidence=1.0,
            )
        )
    fact_check_verdict = google_fact_check.aggregate_verdict(fact_check_results)

    # NewsAPI -- corroborating evidence only, NOT a verdict (see
    # newsapi_feed.py's module docstring: a relevance-search hit shows
    # related news coverage exists, it does not confirm this specific
    # claim). Folded into the same live-evidence count USGS/GDACS/ReliefWeb
    # feed into, never into evidence_type_matches (no structured disaster
    # type on a free-text news article), and never into the verification
    # message/reliability override the way a fact-checker's explicit
    # rating is above -- that stays fact-check-only, deliberately.
    news_articles: list[newsapi_feed.NewsArticle] = []
    try:
        news_articles = newsapi_feed.search(_news_query(result, text))
    except FeedNotConfiguredError:
        pass
    except Exception:
        logger.exception("NewsAPI lookup failed for submitted claim")

    for article in news_articles[:3]:
        claim.evidence.append(
            Evidence(
                source=article.source_name,
                url=article.url,
                evidence_type="news_article_match",
                description=f"{article.title} (via NewsAPI)",
                event_timestamp=article.published_at,
                matched_confidence=0.6,  # a relevance-search hit, not a verified/geo-matched event
            )
        )

    # Mastodon -- how many INDEPENDENT accounts are posting about the same
    # topic, not a verdict and not "consensus" (no upvote/downvote exists
    # on Mastodon -- see social_corroboration.py's docstring). Every
    # matched post is persisted (not capped) so should_alert() and the
    # verification message can derive the true unique-account count from
    # what's actually stored, via the same shared helper.
    disaster_type, place = _topic_terms(result)
    hashtags = [t for t in (disaster_type, place) if t]
    social_posts: list[mastodon_feed.SocialPost] = []
    if hashtags:
        try:
            social_posts = mastodon_feed.search_hashtags(
                hashtags, since=claim.submitted_at - timedelta(days=3)
            )
        except Exception:
            logger.exception("Mastodon lookup failed for submitted claim")

    for post in social_posts:
        engagement = post.favourites_count + post.reblogs_count + post.replies_count
        claim.evidence.append(
            Evidence(
                source=post.account_handle,
                url=post.url,
                evidence_type="social_corroboration",
                description=f"{post.content_text} -- {engagement} engagement (via Mastodon)",
                event_timestamp=post.created_at,
                matched_confidence=0.5,
            )
        )

    reliability = score_reliability(
        misinfo_confidence=result["confidence_raw"],
        verification_matched=result["verification"]["matched"],
        verification_similarity=result["verification"]["similarity_raw"],
        verification_threshold=MATCH_THRESHOLD,
        live_evidence_count=len(live_matches) + len(news_articles),
        live_evidence_source_count=len({e.source for e in live_matches} | {a.source_name for a in news_articles}),
        location_level=location_level,
        evidence_type_matches=evidence_type_matches,
    )

    # A real fact-checker's rating outranks the model's own verdict (see
    # verification_message.py's module docstring for the same precedence
    # rule applied to the headline message). Never rewrite
    # claim.classification itself -- that would misrepresent what the ML
    # model actually predicted; only the reliability band is overridden,
    # capped into LOW so should_alert() flags it for human review too.
    contradicts_fact_check = (
        fact_check_verdict == "FALSE" and claim.classification != "FAKE"
    ) or (
        fact_check_verdict == "TRUE" and claim.classification == "FAKE"
    )
    if contradicts_fact_check:
        reliability.score = min(reliability.score, 30)
        reliability.band = "LOW"
        reliability.reasons.append(
            "Reliability capped at LOW: an independent fact-checker's rating contradicts the model's verdict."
        )

    # High-volume independent social corroboration floors an otherwise-LOW
    # band up to MEDIUM -- but never when a fact-checker has explicitly
    # rated this claim FALSE (that still wins outright, checked here via
    # fact_check_verdict rather than re-deriving from evidence since this
    # runs before commit). Never downgrades an already-HIGH/MEDIUM band.
    social_band, social_account_count = social_corroboration.social_level(claim.evidence)
    if social_band == "HIGH" and fact_check_verdict != "FALSE" and reliability.band == "LOW":
        reliability.score = max(reliability.score, 55)
        reliability.band = "MEDIUM"
        reliability.reasons.append(
            f"Reliability raised to MEDIUM: {social_account_count} independent social media accounts "
            "are posting about a matching event."
        )

    claim.reliability_score = reliability.score
    claim.reliability_band = reliability.band
    claim.reliability_reasons = reliability.reasons

    alert = maybe_create_alert(claim)
    if alert is not None:
        claim.alerts.append(alert)

    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
