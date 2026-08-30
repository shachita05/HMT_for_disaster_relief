# Data sources — verified working download commands

These were tested and confirmed working in the session that produced them. Most need no authentication;
where one does (ReliefWeb, and the "still needed" list below), it's called out explicitly rather than
glossed over.

## PHEME veracity dataset (1.1GB extracted)
```bash
curl -sL -o PHEME_veracity.tar.bz2 "https://ndownloader.figshare.com/files/11767817"
tar -xzf PHEME_veracity.tar.bz2   # despite the .bz2 extension, it's actually gzip
```
9 events: Charlie Hebdo, Ferguson, Germanwings crash, Gurlitt, Ottawa shooting, Prince Toronto,
Putin missing, Sydney siege, Ebola-Essien. Each rumour has `annotation.json` with veracity
(check both `true` and `misinformation` keys — the schema is inconsistent across events, an
artifact of the dataset being built incrementally in 2016 and extended in 2018).

## HumAID (53,531 train / 7,793 dev / 15,160 test)
```bash
curl -sL -o train.parquet "https://huggingface.co/datasets/QCRI/HumAID-all/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
curl -sL -o validation.parquet "https://huggingface.co/datasets/QCRI/HumAID-all/resolve/refs%2Fconvert%2Fparquet/default/validation/0000.parquet"
curl -sL -o test.parquet "https://huggingface.co/datasets/QCRI/HumAID-all/resolve/refs%2Fconvert%2Fparquet/default/test/0000.parquet"
```
Columns: `tweet_text`, `class_label` (11 humanitarian categories, e.g. `injured_or_dead_people`,
`rescue_volunteering_or_donation_effort`, `sympathy_and_support`).

## IDRISI (215MB — location mention recognition + disambiguation)
```bash
git clone --depth 1 https://github.com/rsuwaileh/IDRISI.git
```
Two subdirectories: `LMR/` (location mention recognition — span extraction) and
`LMD/` (location mention disambiguation — resolving spans to actual geo-coordinates).
This is your direct benchmark for validating the gazetteer/NER geo-resolution module
before trusting it on your own Hindi/regional-language data.

## Still needed (require your credentials — see STATUS.md)
- Reddit (PRAW) — needs OAuth app approval
- Telegram (Telethon) — needs api_id/api_hash from my.telegram.org
- Google Fact Check Tools API — needs a free API key from Google Cloud Console
- ReliefWeb API — see the correction below. Free, but needs a requested/
  approved appname, not just any string.

## Live evidence feeds (full-stack rebuild)

Verified directly against each live endpoint while building this — two
turned out to be genuinely no-key/no-signup as planned, one did not:

- **USGS earthquakes** — `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson`
  (note: plural "earthquakes" — the commonly-guessed singular path 404s).
  No key. Confirmed working 2026-08-29.
- **GDACS** — `https://www.gdacs.org/xml/rss.xml`. Public domain, no key.
  Confirmed working 2026-08-29 (469 items, real India flood events present
  in the feed at test time).
- **ReliefWeb — CORRECTION**: originally planned as a third no-key
  source. Its v1 API is fully decommissioned (HTTP 410 on any v1 call).
  Its v2 API requires an **approved** `appname` — an arbitrary string gets
  HTTP 403 "You are not using an approved appname," with a link to
  request one at https://apidoc.reliefweb.int/parameters#appname. So this
  source's fetch/parse code is real and tested (see
  `backend/app/external_feeds/reliefweb_feed.py` and its mocked tests),
  but it is currently inactive — reported as feed status
  `"not_configured"`, same as the fully-credentialed stubs — until an
  approved appname is obtained and set as `RELIEFWEB_APPNAME` in `.env`.

## Location centroid datasets (full-stack rebuild)

Neither of these existed in the original prototype — the gazetteer
(`pincodes_kishorek.csv`) has no lat/lon columns at all, so the original
Streamlit dashboard's map (since removed, see STATUS.md) was
state-centroid-only via a hardcoded dict. These two CSVs are what
`src/location/geocode_lookup.py` reads instead (offline, no network call
at request time — see that module's docstring).

**`data/external/city_centroids.csv`** — top 400 Indian cities by
population, from GeoNames' free `cities1000` dump (every populated place
worldwide with ≥1000 people) + `admin1CodesASCII.txt` (state-code→name
mapping). CC BY 4.0, GeoNames.org. Downloaded 2026-08-29.
```bash
curl -sL -o cities1000.zip https://download.geonames.org/export/dump/cities1000.zip
curl -sL -o admin1CodesASCII.txt https://download.geonames.org/export/dump/admin1CodesASCII.txt
```
Regenerate via `python3 src/location/build_city_centroids.py` (needs
network access; nothing else in the app does).

**`data/external/state_centroids.csv`** — 32 state/UT centroids, promoted
verbatim from the old Streamlit prototype's hardcoded `STATE_COORDS` dict
(hand-verified state-capital coordinates, not derived from any external
dataset). No new sourcing risk — this was a straight move, not new data.

**Known, permanent limitation** (state this plainly anywhere coordinates
are shown): a locality-level match renders at its *city's* centroid, and
a city with no match falls back to its *state's* centroid — never a true
street-level point. There is deliberately no live geocoding call in the
request path (see `geocode_lookup.py`).
