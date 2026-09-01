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
1. Fact-check FALSE + HIGH social corroboration BOTH present -- shown
   together, neither hides the other. Discovered from real testing: Google
   Fact Check's search is a relevance search, not an exact match, so a
   vague/generic submitted claim (e.g. "floods in nepal") can surface a
   real fact-checker's review of a SPECIFIC piece of misinformation (an
   old video reused, a fake rescue story) that is only loosely related to
   the submitted text -- while separately, real social-media volume and
   news coverage confirm the underlying event itself is genuinely
   happening. These are not necessarily a contradiction: the event can be
   real AND a specific piece of viral content about it can be fake. Silently
   letting fact-check win outright (the old behavior) buried real
   corroborating evidence and implied the whole event was false when only
   some specific content about it was.
2. Fact-check verdict alone (FALSE or TRUE, no high social corroboration)
   -- stronger evidence than this project's own ML model or anything else
   here, so its wording explicitly calls out a contradiction with the
   model's own verdict rather than silently overriding it.
3. High-volume independent social-media corroboration (Mastodon) alone --
   how many INDEPENDENT ACCOUNTS are posting about the same topic. NEVER
   worded as "verified" or "consensus": Mastodon has no upvote/downvote,
   so a post count is a proxy for how much this is circulating, not for
   whether people agree it's true.
4. Everything else (live official-feed match, confident-FAKE-with-no-
   record, LOW-reliability-flagged-for-review, partial support).
"""
from app.services.alerts_service import CONFIDENT_FAKE_THRESHOLD


def compute_overall_verdict(
    classification: str,
    confidence: float,
    has_live_official_match: bool,
    fact_check_verdict: str | None = None,
    social_level: str | None = None,
) -> str:
    """TRUE | FAKE | DISPUTED | UNVERIFIED -- a single resolved answer for
    when to show the user ONE final verdict, distinct from `classification`
    (which always stays the model's raw, unmodified prediction -- never
    overwritten, never even read by callers as "the" answer on its own).

    Added because of a real, observed UX problem: for a generic query like
    "floods in nepal", the model's own confidence lands below its
    TRUE/FAKE threshold (reports UNVERIFIED) while fact-check + social +
    news evidence gathered afterward paints a much clearer picture -- a
    user reasonably expects ONE headline answer, not five separate signals
    to reconcile themselves. `classification` stays visible as secondary
    detail (see ClaimAnalysisView.tsx) precisely so this resolved verdict
    is never mistaken for "what the model predicted."

    Mirrors build_verification_message()'s precedence order below --
    keep the two in sync if either changes.
    """
    if fact_check_verdict == "FALSE" and social_level == "HIGH":
        return "DISPUTED"
    if fact_check_verdict == "FALSE":
        return "FAKE"
    if fact_check_verdict == "TRUE":
        return "TRUE"
    if classification == "FAKE" and confidence >= CONFIDENT_FAKE_THRESHOLD:
        return "FAKE"
    if classification == "TRUE" and has_live_official_match:
        return "TRUE"
    if social_level == "HIGH":
        return "TRUE"
    return classification if classification in ("TRUE", "FAKE") else "UNVERIFIED"


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

    if fact_check_verdict == "FALSE" and social_level == "HIGH":
        return (
            f"A fact-checker{publisher_note} found specific debunked content related to this topic "
            f"(rated False), but {social_account_count} independent accounts and news coverage separately "
            "indicate a real, ongoing event -- these may describe different specific claims about the same "
            "broader situation. Flagged for review; see the evidence panel for details."
        )

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
