"""
Repo-root pytest conftest -- puts src/ on sys.path so every test under
src/*/tests/ can `from disaster.disaster_classifier import ...` etc., the
same way analyze_claim.py and run.py already do via their own
sys.path.insert calls.
"""
import os
import sys

SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
