"""
One clear, plain-English verdict sentence synthesized from data the
pipeline already computes -- classification, the stored-corpus verification
status, the live-feed evidence, an independent fact-checker's rating (Google
Fact Check Tools API, see external_feeds/google_fact_check.py), and the
reliability band (src/utils/reliability_scorer.py). This does NOT add a new
source beyond what's real: it gives the existing signals (ReliefWeb/GDACS/
USGS live matches, the IFND stored-corpus match, a real fact-checker's
rating) a single headline sentence instead of leaving the reader to piece
it together from the separate classification/reliability/evidence panels.

Deliberately does not attempt a social-media majority-vote signal -- no
social API is configured (see stub_feeds.py), and fabricating one would
misrepresent what actually ran, which this project's docs are explicit
about never doing (see STATUS.md/ARCHITECTURE.md).

Precedence: an independent fact-checker's rating outranks everything else
here -- a real fact-checking publisher (PolitiFact, AFP, BOOM, etc.) is
stronger evidence than either this project's own ML model or the absence/
presence of a live official-feed event, so it's checked first and its
wording explicitly calls out a contradiction with the model's own verdict
rather than silently overriding it.
"""
from app.services.alerts_service import CONFIDENT_FAKE_THRESHOLD


def build_verification_message(
    classification: str,
    confidence: float,
    reliability_band: str | None,
    has_live_official_match: bool,
    fact_check_verdict: str | None = None,
    fact_check_publisher: str | None = None,
) -> str:
    publisher_note = f" ({fact_check_publisher})" if fact_check_publisher else ""

    if fact_check_verdict == "FALSE":
        msg = f"An independent fact-checker{publisher_note} has rated this claim False."
        if classification != "FAKE":
            msg += f" This contradicts the model's own '{classification}' verdict -- flagged for review."
        return msg
    if fact_check_verdict == "TRUE":
        msg = f"Confirmed by an independent fact-checker{publisher_note}: this claim has been rated True."
        if classification == "FAKE":
            msg += " This contradicts the model's own FAKE verdict -- flagged for review."
        return msg

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
