"""
Periodic background refresh of the real (no-key) external feeds --
USGS, GDACS, ReliefWeb. This is the concrete meaning of "periodic/
near-real-time monitoring" (see the spec's Section 2 requirement): a
background poll every REFRESH_INTERVAL_MINUTES, never a live stream.
NEVER describe this as "real-time" in any UI copy.

Fetched events are held in a simple in-memory cache (module-level list),
refreshed wholesale on each cycle -- there's no need for a DB table of
raw external events for a capstone-scope project; only MATCHED evidence
(evidence_matcher.py's output, attached to a specific claim) is persisted.
Credentialed stub sources (stub_feeds.py) are polled too, purely so their
FeedNotConfiguredError is caught and recorded as "not_configured" status
-- they never contribute events.
"""
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler

from app.external_feeds import mastodon_feed
from app.external_feeds.base import ExternalEvent, ExternalFeedSource, FeedNotConfiguredError
from app.external_feeds.feed_status import registry
from app.external_feeds.gdacs_feed import GDACSFeedSource
from app.external_feeds.reliefweb_feed import ReliefWebFeedSource
from app.external_feeds.stub_feeds import (
    GoogleFactCheckFeedSource,
    NewsAPIFeedSource,
    RedditFeedSource,
    TelegramFeedSource,
)
from app.external_feeds.usgs_feed import USGSFeedSource

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_MINUTES = 15

REAL_SOURCES: list[ExternalFeedSource] = [USGSFeedSource(), GDACSFeedSource(), ReliefWebFeedSource()]
STUB_SOURCES: list[ExternalFeedSource] = [
    NewsAPIFeedSource(), GoogleFactCheckFeedSource(), RedditFeedSource(), TelegramFeedSource(),
]

_lock = threading.Lock()
_event_cache: list[ExternalEvent] = []


def refresh_all() -> list[ExternalEvent]:
    """Fetches every real source and records stub-source status. Never
    raises -- individual source failures are caught and recorded by each
    source's own fetch() (real sources) or here (stub sources)."""
    events: list[ExternalEvent] = []
    for source in REAL_SOURCES:
        try:
            events.extend(source.fetch())
        except Exception:
            logger.exception("unexpected error refreshing feed %s", source.name)
            registry.record_error(source.name, "unexpected error -- see server logs")

    for source in STUB_SOURCES:
        try:
            source.fetch()
        except FeedNotConfiguredError as e:
            registry.record_not_configured(source.name, str(e))
        except NotImplementedError as e:
            registry.record_not_configured(source.name, str(e))
        except Exception:
            logger.exception("unexpected error polling stub feed %s", source.name)
            registry.record_error(source.name, "unexpected error -- see server logs")

    # Mastodon isn't a stub (keyless, no "not_configured" state) and isn't
    # a geo-event feed like REAL_SOURCES above (it's a per-claim hashtag
    # lookup, see mastodon_feed.py's module docstring) -- this canary call
    # exists purely to keep its /api/feeds/status entry current.
    try:
        mastodon_feed.canary_check()
    except Exception:
        logger.exception("unexpected error polling Mastodon")
        registry.record_error("Mastodon", "unexpected error -- see server logs")

    with _lock:
        _event_cache.clear()
        _event_cache.extend(events)
    return events


def get_cached_events() -> list[ExternalEvent]:
    with _lock:
        return list(_event_cache)


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    refresh_all()  # populate the cache immediately on startup rather than waiting a full interval
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(refresh_all, "interval", minutes=REFRESH_INTERVAL_MINUTES, id="refresh_feeds")
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
