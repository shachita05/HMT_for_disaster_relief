"""
Explicit, env-var-ready stubs for sources that need real credentials this
project does not have (see STATUS.md "What I need from you to keep
going" -- Reddit OAuth and Telegram api_id/api_hash were never obtained).
Google Fact Check Tools API and NewsAPI are the two exceptions -- real
keys were obtained, so their FeedSource classes below are real, working
canary checks (see google_fact_check.py/newsapi_feed.py for the actual
per-claim searches used by pipeline_service.py; these classes only prove
the key/connection work, for the /api/feeds/status dot).

Mirrors the existing NotImplementedError convention in
src/misinformation/misinformation_classifier.py's MuRILClassifier/
TransformerClassifier/LLMComparisonClassifier stubs: the shape of the
integration is visible and explainable in a viva, but it does not
silently no-op or fake data -- fetch() raises FeedNotConfiguredError
naming the exact missing env var, and the caller (scheduler.py) records
that as feed status "not_configured", visibly distinct from "error".
"""
from app.config import settings
from app.external_feeds import google_fact_check, newsapi_feed
from app.external_feeds.base import ExternalEvent, ExternalFeedSource, FeedNotConfiguredError


class NewsAPIFeedSource(ExternalFeedSource):
    name = "NewsAPI"

    def fetch(self) -> list[ExternalEvent]:
        # Real call (see newsapi_feed.canary_check) -- same pattern as
        # GoogleFactCheckFeedSource below: never contributes ExternalEvents
        # here, since this is a claim-text search API, not a geo/disaster
        # event feed. Real per-claim results are fetched in
        # pipeline_service.py instead.
        newsapi_feed.canary_check()
        return []


class GoogleFactCheckFeedSource(ExternalFeedSource):
    name = "GoogleFactCheck"

    def fetch(self) -> list[ExternalEvent]:
        # Real call (see google_fact_check.canary_check) -- raises
        # FeedNotConfiguredError if unconfigured, or lets a real network
        # error propagate to scheduler.py's own try/except (which already
        # records "error" status for any unexpected exception from a stub
        # source -- see refresh_all()). Never contributes ExternalEvents:
        # this is a claim-text search API, not a geo/disaster event feed,
        # so its real results are fetched per-claim in pipeline_service.py
        # instead, independent of this periodic canary poll.
        google_fact_check.canary_check()
        return []


class RedditFeedSource(ExternalFeedSource):
    name = "Reddit"

    def fetch(self) -> list[ExternalEvent]:
        if not (settings.reddit_client_id and settings.reddit_client_secret):
            raise FeedNotConfiguredError("REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET are not set -- see .env.example")
        raise NotImplementedError("Reddit (PRAW) integration not written -- OAuth app was never approved (see STATUS.md)")


class TelegramFeedSource(ExternalFeedSource):
    name = "Telegram"

    def fetch(self) -> list[ExternalEvent]:
        if not (settings.telegram_api_id and settings.telegram_api_hash):
            raise FeedNotConfiguredError("TELEGRAM_API_ID/TELEGRAM_API_HASH are not set -- see .env.example")
        raise NotImplementedError("Telegram (Telethon) integration not written -- credentials were never obtained (see STATUS.md)")
