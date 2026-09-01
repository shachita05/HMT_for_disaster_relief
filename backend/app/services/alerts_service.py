"""
Alert generation. A claim earns an Alert when it's BOTH high-priority
(needs relief-org attention, per priority_scorer.py's own definition of
priority as attention-worthiness independent of truth) AND either well-
supported (reliability HIGH/MEDIUM) or confidently FAKE -- a confidently-
fake, high-priority claim is exactly as alert-worthy as a confidently-true
one, since it needs to be debunked before it spreads. This mirrors
priority_scorer.py's own stated philosophy precisely (see that module's
docstring: "a highly specific, severe-sounding FAKE claim still needs
urgent attention").

ALERT_SCOPE_NOTE (defined once, in app/db/models.py, imported everywhere
an alert is shown) is included in every response so the "no emergency
services contacted" caveat can never drift out of sync between the API
and the UI.
"""
from app.db.models import ALERT_SCOPE_NOTE, Alert, Claim
from app.services import social_corroboration

CONFIDENT_FAKE_THRESHOLD = 0.65  # matches UNVERIFIED_CONFIDENCE_THRESHOLD in misinformation_classifier.py


def should_alert(claim: Claim) -> bool:
    social_level, _ = social_corroboration.social_level(claim.evidence)

    # High social corroboration is alert-worthy on its own, independent of
    # priority/reliability/fact-check -- it's a distinct "this is
    # spreading/developing right now, relief orgs should look" signal, not
    # a truth verdict. NOT suppressed by a fact-check False rating: a real
    # fact-checker debunking one specific piece of viral content doesn't
    # mean the broader event a lot of people are independently reporting
    # isn't real too -- see verification_message.py's module docstring for
    # the same reasoning applied to the headline message.
    if social_level == "HIGH":
        return True

    if claim.priority != "HIGH":
        return False
    if claim.reliability_band in ("HIGH", "MEDIUM"):
        return True
    if claim.classification == "FAKE" and claim.confidence >= CONFIDENT_FAKE_THRESHOLD:
        return True
    # Genuinely unverifiable (LOW reliability, not even confidently FAKE) but
    # still high-priority -- previously this fell through to no alert at all,
    # silently leaving an attention-worthy, unconfirmed claim unflagged. It
    # needs human/official review precisely because nothing else has
    # resolved it either way.
    if claim.reliability_band == "LOW":
        return True
    return False


def build_alert_for_claim(claim: Claim) -> Alert:
    social_level, social_account_count = social_corroboration.social_level(claim.evidence)

    reason_parts = []
    if social_level == "HIGH":
        reason_parts.append(
            f"High social media corroboration ({social_account_count} independent accounts) "
            f"around this '{claim.disaster_type}' claim."
        )
    if claim.priority == "HIGH":
        reason_parts.append(
            f"Priority is HIGH (score={claim.priority_score}) for a '{claim.disaster_type}' claim."
        )
    if claim.classification == "FAKE" and claim.confidence >= CONFIDENT_FAKE_THRESHOLD:
        reason_parts.append(
            f"Classified FAKE with {claim.confidence:.0%} confidence -- flagged so it can be "
            f"debunked before it spreads further, independent of the reliability score below."
        )
    elif claim.reliability_band == "LOW" and claim.priority == "HIGH":
        reason_parts.append(
            "Could not be verified against official sources -- flagged for human review."
        )
    if claim.reliability_band:
        reason_parts.append(f"Reliability is {claim.reliability_band} (score={claim.reliability_score}/100).")
    reason_parts.append(ALERT_SCOPE_NOTE)

    # No claim_id set here deliberately -- the caller appends this to
    # claim.alerts (an unpersisted Claim may not have an id yet); the
    # relationship sets the FK automatically on flush/commit.
    return Alert(level=claim.priority, reason_text=" ".join(reason_parts))


def maybe_create_alert(claim: Claim) -> Alert | None:
    if not should_alert(claim):
        return None
    return build_alert_for_claim(claim)
