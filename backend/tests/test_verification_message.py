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
