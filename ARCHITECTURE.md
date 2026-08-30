# Architecture

## System diagram

Two entry points call the same `src/` pipeline — nothing in `src/` was forked or duplicated for the full-stack
rebuild. (A third entry point, a Streamlit dashboard, existed early in the project and was removed once the React
frontend below replaced it — see `STATUS.md`.)

```
              ┌───────────────────────────────────────────────┐
              │                      src/                        │
              │  analyze_claim.py  (the pipeline function)       │
              │  ├─ disaster/        (relevance + type)          │
              │  ├─ location/        (gazetteer + geocode)       │
              │  ├─ misinformation/  (TF-IDF+LogReg verdict)     │
              │  ├─ verification/    (stored-corpus check)       │
              │  ├─ preprocessing/   (feed text only)            │
              │  └─ utils/           (priority + reliability)    │
              └─────────────────┬───────────────┬─────────────────┘
                                 │               │
                          ┌──────▼──┐    ┌───────▼────────────┐
                          │ run.py  │    │ backend/app/        │
                          │ (CLI)   │    │ services/           │
                          │         │    │ pipeline_service.py │
                          └─────────┘    └──────────┬──────────┘
                                                     │ persists to
                       ┌──────────────────┐  ┌───────▼─────────┐
                       │ external_feeds/   │─►│ SQLite (hmt.db) │
                       │ USGS, GDACS real; │  │ Claim/Location/ │
                       │ ReliefWeb/NewsAPI │  │ Evidence/Alert  │
                       │ etc. stubs        │  └───────┬─────────┘
                       └───────────────────┘          │ served via
                                              ┌────────▼────────┐
                                              │ FastAPI routers │
                                              │ /api/claims,    │
                                              │ stats, map,     │
                                              │ alerts, feeds   │
                                              └────────┬────────┘
                                                        │ REST (JSON)
                                              ┌─────────▼────────┐
                                              │ React SPA         │
                                              │ (frontend/)       │
                                              │ 8 pages           │
                                              └───────────────────┘
```

## Module responsibility map

| Layer | Responsibility | Key files |
|---|---|---|
| Pipeline | ML/NLP/rule-based analysis, no persistence, no HTTP | `src/analyze_claim.py` and its submodules |
| Persistence | ORM models, DB session | `backend/app/db/` |
| Orchestration | Calls the pipeline, maps results to ORM rows, calls scoring/alerting | `backend/app/services/pipeline_service.py`, `alerts_service.py` |
| External data | Real/stub feed sources, matching, scheduling | `backend/app/external_feeds/` |
| API | Request/response schemas, routing, validation | `backend/app/routers/`, `backend/app/schemas/` |
| UI | Pages, components, API client, hooks | `frontend/src/` |

## The ABC "swap point" pattern

Every non-trivial pipeline stage is an abstract interface with exactly one concrete implementation today, so a
future upgrade only requires a new class implementing the same method — nothing downstream changes:

| Interface | Today's implementation | Documented future implementation |
|---|---|---|
| `DisasterClassifier` | `KeywordDisasterClassifier` (rules) | an ML classifier, same `.classify()` signature |
| `LocationExtractor` | `GazetteerLocationExtractor` (regex + gazetteer) | a spaCy/Indic-NER-based extractor |
| `MisinformationClassifier` | `TfidfLogRegClassifier` | `MuRILClassifier` / `TransformerClassifier` / `LLMComparisonClassifier` (`NotImplementedError` stubs today) |
| `ExternalFeedSource` | `USGSFeedSource`, `GDACSFeedSource`, `ReliefWebFeedSource` (real) | `NewsAPIFeedSource`, `GoogleFactCheckFeedSource`, `RedditFeedSource`, `TelegramFeedSource` (credentialed stubs, `FeedNotConfiguredError` today) |

## Database schema

```
Claim
 ├── id, text, source, source_url, submitted_at
 ├── disaster_type, all_disaster_types (JSON)
 ├── classification, confidence, top_terms (JSON)      -- the ML verdict, never conflated with Evidence below
 ├── reliability_score, reliability_band, reliability_reasons (JSON)
 ├── priority, priority_score, priority_reasons (JSON)
 ├── verification_status, reason
 ├── is_historical_seed
 ├── locations  -> Location[]  (one row per mentioned location, one flagged is_primary)
 ├── evidence   -> Evidence[]  (independently-sourced support, NEVER produced by the classifier)
 └── alerts     -> Alert[]

Location: claim_id FK, matched_text, match_level, match_type, locality/city/district/state/pin_code,
          latitude/longitude/coordinate_precision, is_primary

Evidence: claim_id FK, source ("IFND_corpus"|"USGS"|"GDACS"|"ReliefWeb"), url, evidence_type, description,
          event_timestamp, matched_confidence

Alert: claim_id FK, created_at, level, reason_text (always includes ALERT_SCOPE_NOTE), acknowledged
```

**Migration approach: `Base.metadata.create_all()`, no Alembic.** This is a single-developer, dev-scope SQLite
capstone database — the whole DB can be deleted and recreated at any point during development, so Alembic's real
value (safe, reversible, production migration history) doesn't apply yet. The stated cost: a schema change during
development means deleting `hmt.db` and reseeding. Same "don't build what you don't need yet" reasoning as the
`NotImplementedError` classifier stubs above.

## The highest-risk footgun: preprocessing vs. the trained model

`src/build_baseline.py` fit `TfidfVectorizer` on **raw, unpreprocessed** IFND text. `TfidfLogRegClassifier.predict()`
and `SourceVerifier.verify()` (both called inside `analyze_claim()`) therefore expect raw text too.

`src/preprocessing/text_preprocessor.py` exists for cleaning noisy **external-feed** text (RSS/API payloads)
before it reaches the untrained, regex-based `KeywordDisasterClassifier`/`GazetteerLocationExtractor` — cleaning
there can only reduce false positives, since neither of those was ever "trained" on anything.

**It must never be inserted ahead of the misinformation classifier or the verifier without retraining.** Doing so
would silently shift the token distribution the model sees at inference time away from what it was fit on,
degrading accuracy with no error raised. If preprocessing is ever wanted there, it has to be added to
`build_baseline.py`'s *training* text too, and `compare_baselines.py`/`MODEL_EVALUATION.md` rerun from scratch.

## Why FastAPI wraps `src/` instead of replacing it

`analyze_claim()`'s CLI (`run.py`) already worked and was already tested.
`backend/app/services/pipeline_service.py` imports `analyze_claim` with the identical `sys.path.insert` convention
`run.py` already uses, calls it unchanged, and only adds persistence + live-evidence enrichment on top.
`backend/tests/test_api_claims.py::test_api_matches_cli_pipeline_output` asserts the API's output for a fixed
input matches a direct `analyze_claim()` call, as a standing regression guard against the API ever drifting into
reimplementing pipeline logic.

## Deployment

See `docker-compose.yml`. SQLite is the default (per spec); switching to Postgres is a `DATABASE_URL` change
only — the engine in `backend/app/db/session.py` is constructed from that single variable, no code branches on
which database is in use.
