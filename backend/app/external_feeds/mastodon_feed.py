"""
Mastodon -- real, keyless integration (public instance, no signup).

Verified live against mastodon.social before writing this integration:
GET /api/v2/search?type=statuses returns EMPTY even for a generic "flood"
query when unauthenticated -- Mastodon's full-text status search requires
a logged-in user, anonymous callers can't use it. GET
/api/v1/timelines/tag/:hashtag is fully public, no auth, no key, and
returns real posts with real engagement counts. So this module does
hashtag-timeline lookups, not free-text search -- the only shape that
actually works without credentials.

Same per-claim-search shape as google_fact_check.py/newsapi_feed.py (not
a periodic geo feed), for the same reason -- see those modules' docstrings.

No native upvote/downvote exists on Mastodon (unlike Reddit) -- there is
no "people agree this is true" signal here. This module only reports how
many independent accounts posted about a topic; see
app/services/social_corroboration.py for how that's turned into a level,
and its docstring for why this must never be described as consensus or
verification.
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from app.external_feeds.feed_status import registry

logger = logging.getLogger(__name__)

INSTANCE = "https://mastodon.social"
TAG_TIMELINE_URL = INSTANCE + "/api/v1/timelines/tag/{tag}"

_TAG_STRIP = re.compile(r"[^a-z0-9]+")


def to_hashtag(term: str) -> str:
    return _TAG_STRIP.sub("", term.lower())


@dataclass
class SocialPost:
    id: str
    account_handle: str
    content_text: str
    url: str | None
    created_at: datetime | None
    favourites_count: int
    reblogs_count: int
    replies_count: int


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


def search_hashtags(tags: list[str], since: datetime, limit: int = 20) -> list[SocialPost]:
    """Raises requests.RequestException/ValueError on a real network/
    parsing failure -- not swallowed here, same reasoning as
    google_fact_check.search()/newsapi_feed.search(). Never raises
    FeedNotConfiguredError -- this source is keyless."""
    seen_ids: set[str] = set()
    posts: list[SocialPost] = []

    for tag in tags:
        tag = to_hashtag(tag)
        if not tag:
            continue
        resp = requests.get(TAG_TIMELINE_URL.format(tag=tag), params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        for item in resp.json():
            post_id = item.get("id")
            if not post_id or post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            created_at = None
            raw_date = item.get("created_at")
            if raw_date:
                try:
                    created_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except ValueError:
                    pass
            if created_at is not None and created_at < since:
                continue

            account = item.get("account") or {}
            posts.append(
                SocialPost(
                    id=post_id,
                    account_handle=account.get("acct") or account.get("username") or "unknown",
                    content_text=_strip_html(item.get("content", ""))[:280],
                    url=item.get("url"),
                    created_at=created_at,
                    favourites_count=item.get("favourites_count", 0),
                    reblogs_count=item.get("reblogs_count", 0),
                    replies_count=item.get("replies_count", 0),
                )
            )

    return posts


def canary_check() -> None:
    """Called once at startup purely to report an "ok"/"error" status on
    /api/feeds/status -- see google_fact_check.canary_check()'s identical
    purpose. Uses a fixed since=now (i.e. accepts whatever's returned,
    doesn't filter by recency) since this is just a connectivity check."""
    posts = search_hashtags(["flood"], since=datetime.fromtimestamp(0, tz=timezone.utc))
    registry.record_success("Mastodon", len(posts))
