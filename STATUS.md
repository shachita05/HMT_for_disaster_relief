# Project Status — as of this session

What follows is real, verified progress against your IFND.csv and three public benchmark datasets — not projections. Everything below actually ran.

## 1. What's done

### Data acquired and verified
| Dataset | Rows/items | What it is | Status |
|---|---|---|---|
| **IFND.csv** (yours) | 56,714 | Indian fake/true news headlines, 2015–2020 | Loaded, cleaned, EDA'd |
| **PHEME veracity** | 10,456 (1,312 true rumours, 1,090 false rumours, 8,054 non-rumours, 9 events) | Twitter rumour veracity benchmark | Downloaded + parsed |
| **HumAID** | 53,531 train / 7,793 dev / 15,160 test | 19 real disaster events, humanitarian-category labels | Downloaded (HF parquet) |
| **IDRISI** | ~20.5K human-labeled + ~57K silver, location-mention spans | Geo-resolution benchmark for crisis tweets | Cloned (215MB) |

### Baseline classifiers trained and evaluated (real numbers, not estimates)
Refined the disaster-relevance keyword filter (dropped ambiguous standalone words like "storm"/"rescue" that were pulling in political-riot and crime stories; kept unambiguous terms + contextual phrases). Result: **894 disaster-relevant rows** (512 TRUE / 382 Fake) out of 56,714.

- Baseline A (TF-IDF + Logistic Regression, trained and tested only on the disaster subset): **99% macro F1**
- Baseline B (same model trained on the full 56K dataset, evaluated on the same disaster-only test set): **98% macro F1**

## 2. The important finding — read this before you trust those numbers

That 99% is not a real skill measurement, and reporting it as your model's accuracy in the capstone would be a mistake I want to flag now rather than have a committee member catch later.

**What's actually happening:** IFND's `Web` (source) column predicts the label almost perfectly by itself — TRIBUNEINDIA, THESTATESMAN, and INDIANEXPRESS rows are 100% TRUE; AUGMENT and BOOMLIVE rows are 100% Fake. When I pulled the logistic regression's top weighted features, the words driving "FAKE" predictions were **"fact", "check", "video", "shared", "viral", "old", "image"** — i.e. the model learned to recognize *fact-check article headline formatting* ("Fact Check: Video Of X Shared As Y"), not the underlying truth of the claim. TRUE items just read like ordinary news headlines. The classifier is a source/genre detector wearing a misinformation-detector costume.

I re-ran it after stripping the obvious fact-check boilerplate phrases ("fact check", "claim:", "shared", "viral", "old video/image", etc.) — it dropped to 94% F1, still leaning heavily on "video/image/old/kerala" as top signals. That remaining signal isn't pure noise — "old footage recirculated as new disaster news" is a real and common misinformation pattern — but it's a narrow one, and 94% on this test set still doesn't tell you how the model will do on a plain Reddit comment or Telegram forward that has no fact-check-style framing at all.

**What this means for your plan:**
- Don't report the 99%/98% numbers as classifier performance in your writeup — report them alongside this diagnosis, or better, don't lead with them at all.
- The real evaluation has to happen on your **freshly collected Reddit/Telegram data** once you have it — that data won't have "Fact Check:" headline structure, so it's a much fairer test of whether the model generalizes.
- Worth adding to your methodology section as a finding, not hiding: *"we found that headline-style fake news datasets like IFND are prone to source/style leakage, which we diagnosed and controlled for."* That's a legitimate, citable methodological contribution — reviewers like seeing that a team caught this rather than reported inflated numbers.
- Practical fix for training: when you get real Reddit/Telegram data, resist the urge to only add PIB/fact-checker-style debunk text as your "false" examples — try to also capture the *original rumor as it circulated* (the tweet/post being debunked, not the debunking article), since that's what your deployed model actually needs to recognize.

## 3. One correction to the original roadmap

I'd suggested scraping **PIB Fact Check's website** (factcheck.pib.gov.in) as a source of labeled false claims. I checked it directly — it's a **citizen submission portal** (login-gated query form), not a browsable public archive of past fact-checks. PIB's actual fact-check output lives on X/Instagram/Telegram (`t.me/PIB_FactCheck`), not a scrapeable web database. Also worth noting: PIB's mandate is narrowly "claims about Government of India policies/schemes" — not general disaster misinformation, so it was always going to be a partial source at best.

**Better replacement sources**, given IFND itself already shows BOOMLIVE, FACTCRESCENDO, DIGITEYE, NEWSMETER, and THELOGICALINDIAN as fact-checker sources (so the genre is already represented in your bootstrap data): for *fresh* ongoing collection, check whether these outlets publish `ClaimReview`-tagged content — if so, the **Google Fact Check Tools API** (free, official, structured — see the script in the original roadmap) should surface them without any scraping. The Telegram channel `t.me/PIB_FactCheck` is also directly joinable via Telethon like any public channel, which is simpler than scraping their web portal anyway.

## 4. What I need from you to keep going

I can't authenticate as you, so these need your action:
1. **Reddit OAuth app** (client_id/secret) — apply at reddit.com/prefs/apps if you haven't already (flagged as urgent last time — status?)
2. **Telegram API credentials** (api_id/api_hash from my.telegram.org) — needed for both city/news channels and `t.me/PIB_FactCheck`
3. **Google Fact Check Tools API key** — free, instant, from Google Cloud Console

Once you have any of these, send them my way (or just tell me you've got them) and I'll write the actual collection runs against the real APIs rather than the generic skeleton scripts.

## Session: 2026-08-29 — full-stack rebuild

What follows is real, verified progress from this session — everything below actually ran (backend/frontend
booted, pytest/vitest suites executed, `docker compose up` tested end-to-end, a real headless-browser session
clicked through all 8 pages). Not projections.

### What was built

- **FastAPI + SQLAlchemy backend** (`backend/`) wrapping the existing, unmodified `analyze_claim()` pipeline —
  never reimplemented, verified by a regression test that diffs API output against a direct call to the same
  function (`backend/tests/test_api_claims.py::test_api_matches_cli_pipeline_output`).
- **Offline location coordinates** (`src/location/geocode_lookup.py`) from two new committed CSVs (top-400
  Indian cities via GeoNames, all state/UT centroids promoted from the old `dashboard/app.py` dict). No live
  geocoding call anywhere in the request path.
- **Baseline model comparison** (`src/misinformation/compare_baselines.py`): Random Forest and a linear-kernel
  SVM trained on the exact same split/vectorizer as the shipped Logistic Regression. Real result: SVM scored
  higher (macro F1 0.9943 vs. 0.9885) but the 0.0057 margin didn't clear the pre-registered 0.01 adoption
  threshold, so **Logistic Regression stays shipped** — see `MODEL_EVALUATION.md`.
- **Reliability scoring** (`src/utils/reliability_scorer.py`) — new, rule-based, documented like
  `priority_scorer.py`, combining ML confidence + stored/live evidence + location specificity + type coherence.
- **Live evidence feeds** (`backend/app/external_feeds/`): USGS and GDACS are real and verified against their
  live endpoints. **ReliefWeb was planned as a third no-key source and turned out not to be** — its v1 API is
  decommissioned and v2 requires an approved `appname` (HTTP 403 otherwise). Its fetch/parse code is real and
  tested via mocks, but reports `"not_configured"` status honestly rather than being silently disabled or faked
  as working.
- **Alerts, stats/map endpoints, historical seed data** (1002 rows from `ifnd_full.parquet`, idempotent).
- **React + TypeScript frontend** (`frontend/`) — all 8 spec pages, Recharts + Leaflet, verified in a real
  headless-Chromium session (not just `tsc`/build) against the live backend: zero console errors across all
  routes, the spec's own example claim produced the expected Flood/TRUE/Whitefield result, and a live HIGH-
  priority+MEDIUM-reliability submission produced a real, acknowledgeable Alert.
- **Docker packaging** — `docker compose up --build` tested for real, both containers, including a genuine
  cross-origin frontend→backend request against the dockerized frontend.

### Bugs found and fixed during this session (not just written and assumed correct)

1. `Base.metadata.create_all()` created **zero tables** on first boot — `main.py` never imported `app.db.models`,
   so SQLAlchemy had no tables registered on `Base.metadata`. Fixed with an explicit import.
2. `scikit-learn` was silently 1.9.0 in a fresh venv while the shipped `.joblib` models were pickled under 1.8.0
   (visible only as an `InconsistentVersionWarning`) — pinned in `requirements.txt`.
3. Historical claim text from IFND.csv renders as mojibake (e.g. em-dashes/curly-quotes as control characters) —
   the source file is actually cp1252 but `build_baseline.py` (frozen, not touched) reads it as latin-1. Fixed as
   a display-only repair in `seed_historical_claims.py` (byte round-trip re-decode), not by touching
   `build_baseline.py` or any trained artifact.
4. Docker: bind-mounting a host `hmt.db` file that didn't exist yet made Docker silently create a **directory**
   there instead, breaking SQLite with "unable to open database file." Fixed with a named volume for the
   containing directory instead of a single-file bind mount.
5. ReliefWeb's real API schema/auth requirements didn't match the original plan (see above) — discovered by
   actually calling the live endpoint rather than assuming the plan's premise, and corrected in the same session
   rather than shipped as a silent lie.

### What still needs your action (unchanged from before, plus one addition)

1. Reddit OAuth app (client_id/secret)
2. Telegram API credentials (api_id/api_hash)
3. Google Fact Check Tools API key
4. **New**: a ReliefWeb API `appname` approval request — https://apidoc.reliefweb.int/parameters#appname (free,
   but requires actually submitting the request; the integration code is ready and waiting)

## 5. Files in this session's project folder
```
hyperlocal-misinfo-tracker/
├── data/
│   ├── raw/IFND.csv                          (your file)
│   ├── raw/pheme/                            (downloaded, 1.1GB — see DATA_SOURCES.md to re-fetch)
│   ├── raw/humaid/                           (downloaded, ~7MB)
│   ├── raw/IDRISI/                           (downloaded, 215MB — see DATA_SOURCES.md to re-fetch)
│   └── processed/
│       ├── ifnd_annotated.parquet            (full IFND + disaster-relevance flags)
│       └── ifnd_disaster_subset.parquet      (894-row refined disaster subset)
├── src/
│   ├── eda_ifnd.py
│   └── build_baseline.py                     (trains + diagnoses both baselines)
├── outputs/
│   ├── baseline_a_disaster_only.joblib / _vectorizer.joblib
│   ├── baseline_b_general.joblib / _vectorizer.joblib
│   └── baseline_results_summary.json
└── DATA_SOURCES.md                            (exact commands to re-download PHEME/HumAID/IDRISI)
```

## Session: 2026-08-30 — removed the Streamlit dashboard

`dashboard/app.py` (the "Session: 2026-08-29" entry above, item "Real Streamlit app, tested end-to-end") has been
**deleted**, at the user's request, now that the React frontend (`frontend/`) fully replaces it — the React app
covers everything the Streamlit app did (single-claim analysis, dataset overview/charts/map) plus the full spec
(8 pages, persistence, live evidence, alerts) that Streamlit was never going to grow into.

What changed:
- `dashboard/` directory removed; `streamlit` dropped from `requirements.txt`.
- `run.py`'s usage message no longer points at it.
- Docstring references to `dashboard/app.py` in `src/analyze_claim.py`, `src/location/geocode_lookup.py`,
  `backend/app/scripts/seed_historical_claims.py`, and both `conftest.py` files updated to describe it as
  removed/historical rather than a currently-live file.
- `README.md` and `ARCHITECTURE.md` updated to describe two entry points (CLI + full-stack) instead of three.

Nothing about the underlying pipeline (`src/analyze_claim.py` and its submodules) changed — Streamlit was a thin
UI layer on top of it, and removing it doesn't affect `run.py`, the backend, or any test.
