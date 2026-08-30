"""
CLI entry point.

    python3 run.py "your claim text here"

For the full dashboard, see the React frontend in frontend/ (talks to the
FastAPI backend in backend/) -- see the root README's "Full-stack quick
start" section.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from analyze_claim import analyze_claim, print_result  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) > 1:
        claim_text = " ".join(sys.argv[1:])
        print_result(analyze_claim(claim_text))
    else:
        print("Usage:")
        print('  python3 run.py "Heavy rainfall has caused severe flooding in Whitefield, Bengaluru."')
        print("  For the full dashboard: see the React frontend in frontend/ (README.md).")
