"""
One-time (rerunnable) seed script: imports data/processed/ifnd_full.parquet
(1002 rows -- the full IFND disaster subset already run through Stages
2-7 by src/build_baseline.py / classify_ifnd.py / locate_ifnd.py, the same
file the original Streamlit prototype's dataset-overview tab used to read
live -- that prototype has since been removed, see STATUS.md) into the
database, so the React dashboard/map/claims list have realistic,
non-trivial content immediately on a fresh clone rather than starting
completely empty.

Deliberately does NOT re-run the ML pipeline on these 1002 rows -- the
parquet already has primary_type/verdict/verdict_confidence/priority/
priority_score computed, and reprocessing all of them through
analyze_claim() would be slow and pointless (same result, much more work).
Two things it CANNOT reuse from the parquet, so they're intentionally
left unset for seeded rows rather than fabricated:
  - top_terms (per-instance TF-IDF explainability) -- would require
    literally re-running the classifier per row.
  - stored-corpus verification / live-feed evidence -- these are query-
    time concepts (SourceVerifier's own reference corpus, or "recent"
    external feed events), not something that was computed once and
    can be replayed for a years-old historical headline.

Every seeded row is is_historical_seed=True, source="ifnd_dataset" --
never rendered as a live/manual submission anywhere in the UI.
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))
from location.geocode_lookup import get_coordinates  # noqa: E402
from utils.reliability_scorer import score_reliability  # noqa: E402

from app.db.base import Base
from app.db.models import Claim, Location
from app.db.session import SessionLocal, engine

PARQUET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "processed", "ifnd_full.parquet"
)


def _fix_mojibake(text: str) -> str:
    """IFND.csv is actually cp1252-encoded, but build_baseline.py (frozen,
    not touched here -- see module docstring) reads it with
    encoding="latin-1", which maps bytes 1:1 instead of decoding cp1252's
    printable characters in the 0x80-0x9F range (em-dashes, curly quotes,
    etc.) -- those come through as literal control characters that render
    as boxes/underscores in a browser. Round-tripping the already-loaded
    string through the byte values it actually came from and re-decoding
    as cp1252 repairs it for DISPLAY. This does not touch build_baseline.py,
    the trained model, or the parquet files it produced -- purely a
    presentation fix in this seed script."""
    try:
        return text.encode("latin-1").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text  # text with genuine non-latin-1 characters -- leave as-is


def _parse_date(raw) -> datetime:
    if isinstance(raw, str) and raw:
        try:
            return datetime.strptime(raw, "%b-%y").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime(2020, 1, 1, tzinfo=timezone.utc)  # fallback for the rare unparseable/missing date


def seed(db) -> int:
    df = pd.read_parquet(PARQUET_PATH)
    created = 0

    for _, row in df.iterrows():
        disaster_types = list(row["disaster_types"]) if row["disaster_types"] is not None else []
        location_level = row.get("location_level")
        city = row.get("location_city") if pd.notna(row.get("location_city")) else None
        state = row.get("location_state") if pd.notna(row.get("location_state")) else None
        confidence = float(row["verdict_confidence"]) if pd.notna(row["verdict_confidence"]) else 0.5

        # Reliability is computed here (real, not fabricated) from the
        # fields the historical dataset actually has -- confidence and
        # location specificity -- with verification/live-evidence
        # components correctly at 0, since neither was ever run for these
        # historical rows (see module docstring).
        reliability = score_reliability(
            misinfo_confidence=confidence,
            verification_matched=False,
            verification_similarity=0.0,
            verification_threshold=0.35,
            live_evidence_count=0,
            live_evidence_source_count=0,
            location_level=location_level,
            evidence_type_matches=None,
        )

        claim = Claim(
            text=_fix_mojibake(row["Statement"]),
            source="ifnd_dataset",
            source_url=None,
            submitted_at=_parse_date(row.get("Date")),
            disaster_type=row["primary_type"],
            all_disaster_types=disaster_types,
            classification=row["verdict"],
            confidence=confidence,
            top_terms=[],  # not re-derived for historical rows -- see module docstring
            reliability_score=reliability.score,
            reliability_band=reliability.band,
            reliability_reasons=reliability.reasons,
            priority=row["priority"],
            priority_score=int(row["priority_score"]),
            priority_reasons=[],
            verification_status="not_matched",  # SourceVerifier was never run against these rows
            reason=(
                f"Historical IFND record. Disaster type: {row['primary_type']}. "
                f"Verdict: {row['verdict']} ({confidence:.0%} confidence, from the original IFND label)."
            ),
            is_historical_seed=True,
        )

        if city or state:
            coords = get_coordinates(city, state)
            claim.locations.append(
                Location(
                    matched_text=city or state,
                    match_level=location_level or "none",
                    match_type="seed",  # neither "exact" nor "fuzzy" -- taken from the precomputed dataset, not re-resolved
                    locality=None,
                    city=city,
                    district=None,
                    state=state,
                    pin_code=None,
                    latitude=coords.latitude,
                    longitude=coords.longitude,
                    coordinate_precision=coords.precision,
                    is_primary=True,
                )
            )

        db.add(claim)
        created += 1

    db.commit()
    return created


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Claim).filter(Claim.is_historical_seed.is_(True)).count()
        if existing:
            print(f"{existing} historical rows already seeded -- skipping (delete hmt.db to reseed from scratch).")
        else:
            n = seed(db)
            print(f"Seeded {n} historical claims from {PARQUET_PATH}")
    finally:
        db.close()
