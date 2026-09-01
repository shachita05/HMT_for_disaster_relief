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
