from app.services.verification_message import build_verification_message


def test_true_with_live_official_match_is_confirmed():
    msg = build_verification_message(
        classification="TRUE", confidence=0.8, reliability_band="HIGH", has_live_official_match=True
    )
    assert "Confirmed" in msg
    assert "ReliefWeb/GDACS/USGS" in msg


def test_confident_fake_says_no_official_record():
    msg = build_verification_message(
        classification="FAKE", confidence=0.9, reliability_band="LOW", has_live_official_match=False
    )
    assert "No official record" in msg
    assert "misinformation" in msg


def test_low_reliability_flags_for_human_review():
    msg = build_verification_message(
        classification="UNVERIFIED", confidence=0.3, reliability_band="LOW", has_live_official_match=False
    )
    assert "human review" in msg


def test_medium_band_without_live_match_is_partial():
    msg = build_verification_message(
        classification="TRUE", confidence=0.6, reliability_band="MEDIUM", has_live_official_match=False
    )
    assert "Partially supported" in msg
    assert "TRUE" in msg


def test_fact_check_false_overrides_true_classification():
    msg = build_verification_message(
        classification="TRUE",
        confidence=0.8,
        reliability_band="HIGH",
        has_live_official_match=True,
        fact_check_verdict="FALSE",
        fact_check_publisher="PolitiFact",
    )
    assert "False" in msg
    assert "PolitiFact" in msg
    assert "contradicts" in msg.lower()


def test_fact_check_true_agrees_with_true_classification_no_contradiction_note():
    msg = build_verification_message(
        classification="TRUE",
        confidence=0.8,
        reliability_band="HIGH",
        has_live_official_match=False,
        fact_check_verdict="TRUE",
        fact_check_publisher="AFP Fact Check",
    )
    assert "Confirmed" in msg
    assert "contradicts" not in msg.lower()


def test_fact_check_takes_precedence_over_live_official_match():
    msg = build_verification_message(
        classification="TRUE",
        confidence=0.9,
        reliability_band="HIGH",
        has_live_official_match=True,
        fact_check_verdict="FALSE",
        fact_check_publisher="BOOM",
    )
    assert "ReliefWeb" not in msg
    assert "False" in msg


def test_high_social_corroboration_message():
    msg = build_verification_message(
        classification="UNVERIFIED",
        confidence=0.3,
        reliability_band="LOW",
        has_live_official_match=False,
        social_level="HIGH",
        social_account_count=7,
    )
    assert "7 independent accounts" in msg
    assert "relief-organization" in msg
    # must explicitly disclaim consensus/verification, never assert it outright --
    # see social_corroboration.py's docstring on why this is a volume signal only
    assert "not a verified consensus" in msg.lower()


def test_fact_check_false_and_high_social_corroboration_both_shown():
    # Neither signal should silently hide the other -- a fact-checker
    # debunking one specific piece of viral content doesn't mean the
    # broader event isn't real, and vice versa. See this module's
    # docstring for the real "floods in nepal" case that surfaced this.
    msg = build_verification_message(
        classification="TRUE",
        confidence=0.8,
        reliability_band="HIGH",
        has_live_official_match=False,
        fact_check_verdict="FALSE",
        fact_check_publisher="PolitiFact",
        social_level="HIGH",
        social_account_count=10,
    )
    assert "False" in msg
    assert "PolitiFact" in msg
    assert "10 independent accounts" in msg


def test_fact_check_false_alone_still_uses_original_wording():
    # without high social corroboration, the simpler single-signal message stays
    msg = build_verification_message(
        classification="TRUE",
        confidence=0.8,
        reliability_band="HIGH",
        has_live_official_match=False,
        fact_check_verdict="FALSE",
        fact_check_publisher="PolitiFact",
        social_level="SOME",
        social_account_count=2,
    )
    assert "has rated this claim False" in msg
    assert "independent accounts" not in msg
