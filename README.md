# HMT — Hyperlocal Misinformation Tracker for Disaster Relief

A disaster information analysis and misinformation tracking system, built as a BE capstone project. Given a
disaster-related claim, it runs the claim through a pipeline — relevance, disaster type, location, misinformation
classification, evidence, reliability, priority — and persists the result so a relief organization can triage
information instead of treating every report as equally trustworthy.

Every submitted claim is checked live against a real fact-checking API (Google Fact Check Tools), a real news
search (NewsAPI), and a real social-media source (Mastodon), alongside disaster feeds (USGS, GDACS) that refresh
in the background every 15 minutes. There's no continuous social-media firehose, so calling this "real-time" would
overstate it, but it's not a static offline analyzer either — the checks against fact-checkers, news, and social
posts happen at the moment a claim is submitted.

The full-stack version below (FastAPI + React) is the main way to use this project. A CLI entry point (`run.py`)
also works and calls the same underlying pipeline — handy for a one-off check without starting either server. (An
earlier Streamlit dashboard existed during development and was retired once the React frontend replaced it; see
`STATUS.md` for that history.)

This README describes what actually runs, not what was planned. `STATUS.md` has the full session-by-session log,
and `ARCHITECTURE.md` covers the system design.

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

To get real fact-check/news/social results rather than empty evidence panels, fill in `GOOGLE_FACT_CHECK_API_KEY`
and `NEWS_API_KEY` in `.env` — both have free tiers and take a couple of minutes to obtain. Mastodon needs no key
at all. See the comments in `.env.example` for where to get each one.

## CLI (no server needed)

The pipeline itself (`src/analyze_claim.py` and friends) hasn't changed since the original prototype — the
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
| Location coordinates (`src/location/geocode_lookup.py`) | Real, offline city/state centroids (top 400 cities + all states/UTs). Locality-level claims render at their city's centroid, not a street-level point — there's no live geocoding call |
| Misinformation classification (`src/misinformation/`) | Real — TF-IDF + Logistic Regression, compared against Random Forest and linear SVM on the same split (see `MODEL_EVALUATION.md`). LogReg shipped because SVM's improvement didn't clear the pre-registered adoption margin |
| UNVERIFIED band | An operational rule based on low model confidence, not a trained third class — IFND has no real UNVERIFIED ground truth |
| Stored-corpus verification (`src/verification/`) | Real, but checks our own stored IFND corpus via cosine similarity, not a live government source |
| Live evidence feeds — USGS, GDACS (`backend/app/external_feeds/`) | Real, no API key, polled every 15 minutes |
| Live evidence feed — ReliefWeb | Code and parsing are real and tested via mocks, but currently inactive — its API requires an approved `appname` we don't have (see `DATA_SOURCES.md`) |
| Fact-check lookup — Google Fact Check Tools API (`backend/app/external_feeds/google_fact_check.py`) | Real — searches real fact-checking publishers (PolitiFact, AFP, BOOM, Alt News, The Quint, etc.) live on every claim submission. A False/True rating from this API outranks the ML model's own verdict in the verification message and caps the reliability score into LOW on disagreement. It never rewrites `classification` itself, which always stays the model's raw prediction |
| News search — NewsAPI (`backend/app/external_feeds/newsapi_feed.py`) | Real — a per-claim search, using a query built from the extracted disaster type and location rather than the raw sentence (NewsAPI's search needs a short query to return anything). Treated as weaker evidence than the fact-check API on purpose: a matching article shows related coverage exists, not that this specific claim is true, so it only adds evidence rows and nudges the reliability score slightly |
| Social media corroboration — Mastodon (`backend/app/external_feeds/mastodon_feed.py`) | Real — public hashtag-timeline lookup, no key or signup required (Mastodon's free-text search needs a login, but hashtag timelines don't). Counts unique accounts posting about the same disaster type and location rather than raw post count, so one account can't inflate the signal, and is never described as "verified" or "consensus" since Mastodon has no upvote/downvote — it's a volume signal only. Five or more independent accounts floors the reliability score to at least MEDIUM and creates an alert, regardless of priority |
| Live evidence feeds — Reddit, Telegram | Not built — Reddit's free API tier has tightened significantly and Telegram's client API needs a personal phone-verified account; neither fit this project's constraints (see `STATUS.md`) |
| Reliability score (`src/utils/reliability_scorer.py`) | Real, rule-based and documented — not a trained model |
| Priority score (`src/utils/priority_scorer.py`) | Real, rule-based and additive, also documented |
| Verification verdict message (`backend/app/services/verification_message.py`) | Real — one plain-English sentence combining the fact-check rating, social corroboration volume, live official-feed matches, and reliability band, shown at the top of every claim's analysis |
| Overall verdict (`compute_overall_verdict` in `verification_message.py`) | Real — resolves a single TRUE / FAKE / DISPUTED / UNVERIFIED answer from classification plus fact-check/social/live evidence, shown as the primary badge on the claim analysis view. Kept separate from `classification`, which stays the model's raw prediction and is shown as secondary detail. DISPUTED exists for the case a plain TRUE/FAKE/UNVERIFIED can't express: a fact-checker debunked one specific piece of content while independent evidence confirms the underlying event is real |
| Alerts (`backend/app/services/alerts_service.py`) | Real — generated for high-priority claims that are well-supported, confidently fake, or genuinely unverifiable, and separately for high social-media corroboration regardless of priority. Never contacts emergency services |
| Backend API (`backend/`) | Real — FastAPI + SQLAlchemy + SQLite, wraps the pipeline above, persists every claim, location, evidence row, and alert |
| Frontend dashboard (`frontend/`) | Real — React + TypeScript SPA with charts and a Leaflet/OpenStreetMap map |
| MuRIL / IndicBERT / LLM misinformation classifiers | `NotImplementedError` stubs — needs labeled multilingual data that doesn't exist yet |

## Known limitations 

- English-only. IFND turned out to have no Hindi/regional-language content despite its reputation.
- UNVERIFIED is a confidence threshold, not a real third class.
- Stored-corpus "verification" checks our own dataset, not live government sources.
- Location extraction has known false-positive classes (documented in `location_extractor.py`), and any
  locality-level name not in the 2017-vintage gazetteer simply won't resolve.
- Map coordinates are offline centroids, not precise geocodes — see `geocode_lookup.py`.
- Priority and reliability thresholds are judgment calls, not learned from data, though each one is documented
  with the reasoning behind it.
- The original IFND baseline's reported accuracy is inflated by source/style leakage — see the diagnosis in
  `STATUS.md` and its restatement in `MODEL_EVALUATION.md`. This is a property of the dataset, not of whichever
  algorithm ships.
- ReliefWeb integration is written but inactive, pending an approved API appname.
- SQLite has no migration history (no Alembic). A dev-only capstone database doesn't need one; see
  `ARCHITECTURE.md` for the reasoning.
- Google Fact Check's search is relevance-based, not exact-match, so a short/generic submitted claim can surface a
  fact-checker's review of a specific piece of content only loosely related to what was submitted. The verification
  message and overall verdict account for this (see `DISPUTED` above), but it's worth knowing about.

## Full history

`STATUS.md` and `DATA_SOURCES.md` have the detailed session-by-session log, including every bug found and fixed
during testing — a zero-tables `Base.metadata.create_all()` bug, a Docker bind-mount gotcha, a cp1252/latin-1
mojibake fix, a NewsAPI hostname typo caught by testing against the live API, and the ReliefWeb appname-approval
discovery, among others.

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
├── frontend/                          # React + TypeScript SPA -- the project's dashboard
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

# the real feed endpoints, hit for real -- excluded from the default run
python3 -m pytest backend/tests/test_external_feeds_live.py -m network

# frontend
cd frontend && npm run test && npx tsc -b && npm run lint
```

## Not built

- Live Reddit/Telegram ingestion — both need credentials this project doesn't have (see `STATUS.md`)
- Real government API integration for stored-corpus verification (NDMA/IMD/PIB)
- MuRIL/IndicBERT fine-tuning — needs multilingual labeled data that doesn't exist yet
- A continuous social-media stream (Kafka/RabbitMQ) — the live checks are per-claim and per-15-minute-poll, not a
  standing firehose
- Image/video misinformation analysis
- Satellite or remote-sensing evidence and geospatial analysis beyond the current centroid-level mapping
- A mobile app with push notifications
- User accounts, authentication, and human-in-the-loop verification workflows
- Emergency-service contact from alerts — alerts are for relief-organization consideration only
