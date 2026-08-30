"""
Offline lat/lon centroid lookup -- NO live geocoding call is ever made in
the request path. The gazetteer (pincodes_kishorek.csv) has no coordinate
columns, so this module reads two small, committed CSVs instead:

  data/external/city_centroids.csv  -- top ~400 Indian cities by
      population (GeoNames cities1000, CC BY 4.0 -- see
      src/location/build_city_centroids.py and DATA_SOURCES.md)
  data/external/state_centroids.csv -- 32 state/UT capital-ish centroids,
      promoted verbatim from the original Streamlit prototype's
      STATE_COORDS dict (that prototype has since been removed in favor
      of the React frontend -- see STATUS.md)

KNOWN, PERMANENT LIMITATION -- state this plainly wherever coordinates are
shown (Map page, README): a locality-level match (e.g. "Whitefield")
renders at its CITY's centroid (e.g. Bengaluru), not a true street-level
point -- there is no locality-level coordinate data anywhere in this
project. A city-level match renders at its own centroid. If neither the
city nor the state can be matched, no point is plotted at all rather than
guessing.

Both CSVs are loaded once at process start (module-level, same pattern as
Gazetteer's first-letter buckets) -- never re-read per request.
"""
import csv
import os
from dataclasses import dataclass
from typing import Optional

from .gazetteer import _normalize

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "external")
CITY_CSV = os.path.join(DATA_DIR, "city_centroids.csv")
STATE_CSV = os.path.join(DATA_DIR, "state_centroids.csv")


@dataclass
class Coordinates:
    latitude: Optional[float]
    longitude: Optional[float]
    precision: str  # "city" | "state" | "none"


def _load_city_index() -> dict:
    index = {}
    with open(CITY_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = _normalize(row["city"])
            # keep the first (highest-population, since the source file is
            # pre-sorted) entry for a given normalized name
            index.setdefault(key, (float(row["lat"]), float(row["lon"])))
    return index


def _load_state_index() -> dict:
    index = {}
    with open(STATE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = _normalize(row["state"])
            index.setdefault(key, (float(row["lat"]), float(row["lon"])))
    return index


_CITY_INDEX = _load_city_index()
_STATE_INDEX = _load_state_index()


def get_coordinates(city: Optional[str], state: Optional[str]) -> Coordinates:
    """Offline city-centroid-first, state-centroid-fallback lookup. Never
    raises, never makes a network call. `city`/`state` are matched using
    the same RENAME_ALIASES-aware normalization the gazetteer itself uses
    (via gazetteer._normalize), so old-dataset names (e.g. "Bangalore")
    and current names (e.g. "Bengaluru") resolve to the same centroid."""
    if city:
        hit = _CITY_INDEX.get(_normalize(city))
        if hit:
            return Coordinates(hit[0], hit[1], "city")

    if state:
        hit = _STATE_INDEX.get(_normalize(state))
        if hit:
            return Coordinates(hit[0], hit[1], "state")

    return Coordinates(None, None, "none")


if __name__ == "__main__":
    tests = [
        ("Bangalore", "Karnataka"),   # old-dataset city name -> should still hit via alias-aware normalization
        (None, "Bihar"),               # state-only -> state centroid
        ("Nonexistentcityxyz", "Kerala"),  # unknown city -> falls back to state
        (None, None),                   # nothing at all -> none
    ]
    for city, state in tests:
        c = get_coordinates(city, state)
        print(f"city={city!r} state={state!r} -> {c}")
