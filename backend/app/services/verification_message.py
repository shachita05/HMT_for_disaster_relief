"""
One clear, plain-English verdict sentence synthesized from data the
pipeline already computes -- classification, the stored-corpus verification
status, the live-feed evidence, an independent fact-checker's rating (Google
Fact Check Tools API, see external_feeds/google_fact_check.py), independent
social-media corroboration volume (Mastodon, see
external_feeds/mastodon_feed.py), and the reliability band
(src/utils/reliability_scorer.py). This does NOT add a new source beyond
what's real: it gives the existing signals (ReliefWeb/GDACS/USGS live
matches, the IFND stored-corpus match, a real fact-checker's rating, real
Mastodon posts) a single headline sentence instead of leaving the reader to
piece it together from the separate classification/reliability/evidence
panels.

Precedence, highest first:
1. An independent fact-checker's rating (PolitiFact, AFP, BOOM, etc.) --
   stronger evidence than this project's own ML model or anything else
   here, so it's checked first and its wording explicitly calls out a
   contradiction with the model's own verdict rather than silently
   overriding it.
2. High-volume independent social-media corroboration (Mastodon) -- how
   many INDEPENDENT ACCOUNTS are posting about the same topic. This is
   NEVER worded as "verified" or "consensus": Mastodon has no
   upvote/downvote, so a post count is a proxy for how much this is
   circulating, not for whether people agree it's true. Suppressed
   entirely when a fact-checker has rated the claim False -- see
   social_corroboration.py's has_fact_check_false().
3. Everything else (live official-feed match, confident-FAKE-with-no-
   record, LOW-reliability-flagged-for-review, partial support).
"""
from app.services.alerts_service import CONFIDENT_FAKE_THRESHOLD


def build_verification_message(
    classification: str,
    confidence: float,
    reliability_band: str | None,
    has_live_official_match: bool,
    fact_check_verdict: str | None = None,
    fact_check_publisher: str | None = None,
    social_level: str | None = None,
    social_account_count: int = 0,
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

    if social_level == "HIGH":
        return (
            f"{social_account_count} independent accounts have posted about a matching event on social "
            "media in the last few days -- flagged for relief-organization attention. (This reflects "
            "posting volume, not a verified consensus -- see the evidence panel for the individual posts.)"
        )

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
