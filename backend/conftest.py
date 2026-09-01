"""
Pytest root conftest for the backend test suite.

Puts backend/ on sys.path so `import app...` works the same way it does
when uvicorn is run from inside backend/, and puts src/ on sys.path so the
backend can import the existing, unmodified pipeline (analyze_claim.py and
friends) the same way run.py already does.
"""
import os
import sys
from unittest.mock import patch

import pytest

BACKEND_DIR = os.path.dirname(__file__)
REPO_ROOT = os.path.join(BACKEND_DIR, "..")
SRC_DIR = os.path.join(REPO_ROOT, "src")

for path in (BACKEND_DIR, SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

# Force a fresh, disposable test DB rather than touching the dev hmt.db.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_hmt.db")

# Never let the pytest suite start the real background feed scheduler --
# it would make live network calls and spin up a thread outside pytest's
# control, which has no place in a default (offline-safe) test run. Feed
# fetch logic itself is tested directly with mocked requests.get calls,
# see backend/tests/test_external_feeds.py.
os.environ.setdefault("ENABLE_FEED_SCHEDULER", "false")

# Same reasoning for the Google Fact Check / NewsAPI lookups
# pipeline_service.py makes on every claim submission: blank the keys so
# they raise FeedNotConfiguredError (silently skipped, see
# pipeline_service.py) instead of making a real, per-test-run network
# call. Each search() is tested directly with a mocked requests.get, see
# test_google_fact_check.py / test_newsapi_feed.py.
os.environ["GOOGLE_FACT_CHECK_API_KEY"] = ""
os.environ["NEWS_API_KEY"] = ""

# Mastodon is keyless -- there's no key to blank the way the two sources
# above are handled, so every test gets an autouse mock returning no posts
# by default instead. A test that wants specific Mastodon results opens
# its own nested `patch(...)` for the same target, which correctly
# overrides this one for the duration of its `with` block. See
# test_mastodon_feed.py for the real search_hashtags() behavior tested
# directly against a mocked requests.get.
@pytest.fixture(autouse=True)
def _no_real_mastodon_calls():
    with patch("app.external_feeds.mastodon_feed.search_hashtags", return_value=[]):
        yield
