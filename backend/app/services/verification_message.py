"""
One clear, plain-English verdict sentence synthesized from data the
pipeline already computes -- classification, the stored-corpus verification
status, the live-feed evidence, and the reliability band
(src/utils/reliability_scorer.py). This does NOT add a new source: it only
gives the existing real signals (ReliefWeb/GDACS/USGS live matches, the IFND
stored-corpus match) a single headline sentence instead of leaving the
reader to piece it together from the separate classification/reliability/
evidence panels.

Deliberately does not attempt a social-media majority-vote signal -- no
social API is configured (see stub_feeds.py), and fabricating one would
misrepresent what actually ran, which this project's docs are explicit
about never doing (see STATUS.md/ARCHITECTURE.md).
"""
from app.services.alerts_service import CONFIDENT_FAKE_THRESHOLD


def build_verification_message(
    classification: str,
    confidence: float,
    reliability_band: str | None,
    has_live_official_match: bool,
) -> str:
    if classification == "TRUE" and has_live_official_match:
        return (
            "Confirmed: official sources (ReliefWeb/GDACS/USGS) report a matching event. "
            "This claim appears accurate."
        )
    if classification == "FAKE" and confidence >= CONFIDENT_FAKE_THRESHOLD:
        return (
            "No official record of this event was found. "
            "This claim has been classified as likely misinformation."
        )
    if reliability_band == "LOW":
        return "Could not be confirmed or denied by official sources yet. Flagged for human review."
    return (
        f"Partially supported -- classified {classification} by the model, but independent "
        "official confirmation is limited."
    )
