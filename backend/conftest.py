"""
Pytest root conftest for the backend test suite.

Puts backend/ on sys.path so `import app...` works the same way it does
when uvicorn is run from inside backend/, and puts src/ on sys.path so the
backend can import the existing, unmodified pipeline (analyze_claim.py and
friends) the same way run.py already does.
"""
import os
import sys

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
