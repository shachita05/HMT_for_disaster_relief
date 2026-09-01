"""
Single source of truth for "how much independent social-media activity
exists around this claim" -- pure, no I/O, operates on already-persisted
Evidence-shaped objects (works for both the ORM Claim.evidence list and
the Pydantic EvidenceOut list, since it only touches .evidence_type/.source).

Called from three places that must never disagree with each other:
pipeline_service.py (reliability floor at write time), alerts_service.py
(alert decision), schemas/claim.py (verification message at read time).

Counts UNIQUE ACCOUNTS (Evidence.source, set by
external_feeds/mastodon_feed.py to the posting account's handle), not raw
post count -- so one account posting repeatedly can't inflate the signal.
This is a proxy for "how many independent people are reporting this," not
"how many agree it's true": Mastodon has no upvote/downvote, so it is
never valid to describe this as consensus or verification -- see
verification_message.py's module docstring for the wording rule this
feeds into.

Thresholds are a documented judgment call, not learned from data -- same
"stated as one" convention as src/utils/reliability_scorer.py and
src/utils/priority_scorer.py.
"""
HIGH_THRESHOLD = 5  # unique accounts
SOME_THRESHOLD = 1


def social_level(evidence) -> tuple[str, int]:
    """Returns (level, unique_account_count). level is HIGH/SOME/NONE."""
    accounts = {e.source for e in evidence if e.evidence_type == "social_corroboration"}
    count = len(accounts)
    if count >= HIGH_THRESHOLD:
        return "HIGH", count
    if count >= SOME_THRESHOLD:
        return "SOME", count
    return "NONE", count
