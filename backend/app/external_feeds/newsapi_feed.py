"""
NewsAPI (newsapi.org) -- real, keyed integration (see .env's NEWS_API_KEY).

Deliberately treated as WEAKER evidence than google_fact_check.py: NewsAPI's
/v2/everything endpoint is a relevance search over news articles, not a
fact-check verdict -- finding articles that mention similar keywords does
not confirm THIS specific claim is true, it only shows real news coverage
exists on the general topic. So, unlike Google Fact Check, a NewsAPI hit
must NEVER drive the verification message's confirm/deny wording or
override the model's classification -- it only contributes as additional
corroborating evidence, exactly like a USGS/GDACS live-feed match (see
pipeline_service.py, where its results are folded into the same
live-evidence count that feeds score_reliability()).

Same per-claim-search shape as google_fact_check.py (not a periodic geo
feed), for the same reason -- see that module's docstring.
"""
import logging
from dataclasses import dataclass
from datetime import datetime

import requests

from app.config import settings
from app.external_feeds.base import FeedNotConfiguredError
from app.external_feeds.feed_status import registry

logger = logging.getLogger(__name__)

SEARCH_URL = "https://newsapi.org/v2/everything"


@dataclass
class NewsArticle:
    source_name: str
    title: str
    url: str | None
    published_at: datetime | None


def search(query: str, page_size: int = 5) -> list[NewsArticle]:
    """Raises FeedNotConfiguredError if no API key is set. Raises
    requests.RequestException/ValueError on a real network/parsing
    failure -- not swallowed here, same reasoning as
    google_fact_check.search()."""
    if not settings.news_api_key:
        raise FeedNotConfiguredError("NEWS_API_KEY is not set -- see .env.example")

    resp = requests.get(
        SEARCH_URL,
        params={
            "q": query,
            "apiKey": settings.news_api_key,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": page_size,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    articles: list[NewsArticle] = []
    for item in data.get("articles", []):
        published_at = None
        raw_date = item.get("publishedAt")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except ValueError:
                pass
        articles.append(
            NewsArticle(
                source_name=(item.get("source") or {}).get("name") or "Unknown source",
                title=item.get("title") or query,
                url=item.get("url"),
                published_at=published_at,
            )
        )
    return articles


def canary_check() -> None:
    """Called periodically by stub_feeds.py's NewsAPIFeedSource purely to
    report an "ok"/"error" status on /api/feeds/status -- see
    google_fact_check.canary_check()'s identical purpose."""
    articles = search("flood")
    registry.record_success("NewsAPI", len(articles))
