# HMT — Hyperlocal Misinformation Tracker for Disaster Relief

A disaster information analysis and misinformation tracking system (BE capstone project) — **not** a live real-time
tracker. It takes a disaster-related claim, analyzes it through a real pipeline (relevance → disaster type →
location → misinformation classification → evidence → reliability → priority), and persists the result so a
relief organization can triage information through a dashboard rather than treat every report as equally
trustworthy. Any automated data ingestion it does is **periodic/near-real-time monitoring** (a 15-minute poll), never a
live stream.

The primary way to use this project is the full-stack version below (FastAPI + React). A CLI entry point
(`run.py`) also still works, calling the exact same underlying pipeline — useful for a quick one-off check without
starting either server. (An early Streamlit dashboard existed during development and was removed once the React
frontend replaced it — see `STATUS.md` if you're looking for it in history.)

Everything in this README states only what actually ran. See `STATUS.md` for the full session-by-session history
and `ARCHITECTURE.md` for the system design.

## Full-stack quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Start the backend (creates hmt.db, boots the feed scheduler)
cd backend
cp ../.env.example ../.env   # optional -- safe defaults exist without it
uvicorn app.main:app --reload
# -> http://localhost:8000/docs for the interactive API (Swagger)

# 2. (optional, in another terminal) seed 1002 historical claims so the
#    dashboard/map/claims list aren't empty on first run
cd backend
PYTHONPATH=. python3 app/scripts/seed_historical_claims.py

# 3. Start the frontend (in another terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
# -> http://localhost:5173
```

Or with Docker (see `docker-compose.yml`):

```bash
cp .env.example .env
docker compose up --build
# backend:  http://localhost:8000
# frontend: http://localhost:8080
# to seed historical data inside the container:
docker compose exec backend python app/scripts/seed_historical_claims.py
```

## CLI (no server needed)

The pipeline itself (`src/analyze_claim.py` and friends) is unmodified in its core ML/NLP/scoring logic — the
full-stack backend wraps it rather than replacing it (see `backend/app/services/pipeline_service.py`, and the
regression test in `backend/tests/test_api_claims.py` that diffs the API's output against a direct call to this
same function). For a quick one-off check without starting the backend or frontend:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 run.py "Heavy rainfall has caused severe flooding in Whitefield, Bengaluru."
```

## What's real vs. what's a placeholder

| Capability | Status |
|---|---|
| Disaster relevance + type classification (`src/disaster/`) | Real — rule-based, 13 categories |
| Location extraction (`src/location/`) | Real — India Post gazetteer (39,734 localities), fuzzy matching |
| Location coordinates (`src/location/geocode_lookup.py`) | Real, offline city/state centroids (top 400 cities + all states/UTs) — locality-level claims render at their city's centroid, never a street-level point (no live geocoding call exists) |
| Misinformation classification (`src/misinformation/`) | Real — TF-IDF + Logistic Regression, compared against Random Forest and linear SVM on the same split (see `MODEL_EVALUATION.md`); LogReg stays shipped (SVM was better but didn't clear the pre-registered adoption margin) |
| UNVERIFIED band | An **operational rule** (low model confidence), not a trained 3rd class — IFND has no real UNVERIFIED ground truth |
| Stored-corpus verification (`src/verification/`) | Real, but checks **our own stored IFND corpus** via cosine similarity — no live NDMA/IMD/PIB integration |
| Live evidence feeds — USGS, GDACS (`backend/app/external_feeds/`) | **Real**, no API key, polled every 15 minutes |
| Live evidence feed — ReliefWeb | Code and parsing are real (tested via mocks); **inactive** — its API requires an approved `appname` we don't have (see `DATA_SOURCES.md`) |
| Live evidence feeds — NewsAPI, Google Fact Check, Reddit, Telegram | **Future Enhancement** — credentials were never obtained (see `STATUS.md`) |
| Reliability score (`src/utils/reliability_scorer.py`) | Real, rule-based and fully documented — not a trained model |
| Priority score (`src/utils/priority_scorer.py`) | Real, rule-based, additive, fully documented |
| Alerts (`backend/app/services/alerts_service.py`) | Real — generated automatically for HIGH-priority + well-supported (or confidently-fake) claims. Never contacts emergency services. |
| Backend API (`backend/`) | Real — FastAPI + SQLAlchemy + SQLite, wraps the pipeline above, persists every claim/location/evidence/alert |
| Frontend dashboard (`frontend/`) | Real — React + TypeScript SPA, 8 pages, charts, a real Leaflet/OpenStreetMap map. (The project's original Streamlit dashboard has been removed now that this replaces it.) |
| MuRIL / IndicBERT / LLM misinformation classifiers | `NotImplementedError` stubs — needs labeled multilingual data that doesn't exist yet |

## Known limitations (be ready for these in your viva)

- **English-only.** IFND turned out to have no Hindi/regional-language content despite its reputation.
- **UNVERIFIED is a confidence threshold, not a real third class.**
- **Stored-corpus "verification" checks our own dataset, not live government sources.**
- **Location extraction has known false-positive classes** (documented in `location_extractor.py`), and any
  locality-level name not in the 2017-vintage gazetteer will simply not resolve.
- **Map coordinates are offline centroids, not precise geocodes** — see `geocode_lookup.py`.
- **Priority and reliability thresholds are judgment calls**, not learned from data — each one is documented
  in-line with the reasoning behind it.
- **The original IFND baseline's reported accuracy is inflated by source/style leakage** — see the diagnosis in
  `STATUS.md` and its re-statement in `MODEL_EVALUATION.md`. This is a property of the dataset, not of whichever
  algorithm ships.
- **ReliefWeb integration is written but inactive** — needs an approved API appname we don't have.
- **SQLite has no migration history** (no Alembic) — a deliberate scope decision for a dev-only capstone DB; see
  `ARCHITECTURE.md`.

## Full history

`STATUS.md` and `DATA_SOURCES.md` have the detailed session-by-session log, including every bug found and fixed
during testing and the reasoning behind each fix — including ones found during this full-stack rebuild (a
zero-tables `Base.metadata.create_all()` bug, a Docker bind-mount gotcha, a cp1252/latin-1 mojibake fix, and the
ReliefWeb appname-approval discovery).

## Project structure

```
hmt-complete-project_1/
├── data/{raw,external,processed}/     # IFND.csv, gazetteer + centroid CSVs, precomputed parquets
├── outputs/                           # trained models, baseline comparison results, demo artifacts
├── src/
│   ├── preprocessing/                 # noisy-text cleaning (feeds only, never the trained model's input)
│   ├── disaster/                      # disaster relevance + type classification
│   ├── location/                      # gazetteer, extraction, offline geocoding
│   ├── misinformation/                # TF-IDF+LogReg classifier, RF/SVM comparison
│   ├── verification/                  # stored-corpus similarity check
│   ├── utils/                         # priority + reliability scoring
│   └── analyze_claim.py               # the combined pipeline, unmodified since the original prototype
├── backend/                           # FastAPI + SQLAlchemy -- wraps src/, adds DB/evidence/alerts/API
│   └── app/{db,routers,schemas,services,external_feeds,scripts}/
├── frontend/                          # React + TypeScript SPA (8 pages) -- the project's dashboard
├── run.py                             # original CLI entry point, still functional
├── docker-compose.yml, backend/Dockerfile, frontend/Dockerfile
├── ARCHITECTURE.md                    # system design, ABC "swap points", DB schema
├── MODEL_EVALUATION.md                # LogReg vs Random Forest vs SVM, full comparison
└── requirements.txt
```

## Testing

```bash
# backend + ML/location/scoring tests (offline, mocked network calls)
python3 -m pytest src/ backend/

# the 3 real feed endpoints, hit for real -- excluded from the default run
python3 -m pytest backend/tests/test_external_feeds_live.py -m network

# frontend
cd frontend && npm run test && npx tsc -b && npm run lint
```

## Not built (deliberately, per project scope)

- Live Reddit/Telegram ingestion (needs your API credentials)
- Real government API integration for stored-corpus verification (NDMA/IMD/PIB)
- MuRIL/IndicBERT fine-tuning (needs multilingual labeled data that doesn't exist yet)
- True real-time streaming (Kafka/RabbitMQ) — the live feeds are periodic polling, honestly labeled as such
- Emergency-service contact from alerts — alerts are for relief-org consideration only

See `About.tsx` in the frontend (the About page) for the full future-enhancements list.
