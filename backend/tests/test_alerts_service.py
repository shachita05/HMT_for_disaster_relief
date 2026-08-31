from app.db.base import Base
from app.db.models import Claim
from app.db.session import SessionLocal, engine
from app.services.alerts_service import ALERT_SCOPE_NOTE, maybe_create_alert


def _claim(**overrides) -> Claim:
    defaults = dict(
        text="t", disaster_type="Flood", classification="TRUE", confidence=0.9,
        priority="HIGH", priority_score=6, reliability_score=80, reliability_band="HIGH",
    )
    defaults.update(overrides)
    return Claim(**defaults)


def test_high_priority_high_reliability_creates_alert_with_scope_note():
    alert = maybe_create_alert(_claim())
    assert alert is not None
    assert ALERT_SCOPE_NOTE in alert.reason_text


def test_low_priority_creates_no_alert():
    alert = maybe_create_alert(_claim(priority="LOW", priority_score=1))
    assert alert is None


def test_confident_fake_high_priority_also_alerts_even_with_low_reliability():
    alert = maybe_create_alert(
        _claim(classification="FAKE", confidence=0.9, reliability_score=10, reliability_band="LOW")
    )
    assert alert is not None


def test_unverifiable_high_priority_alerts_for_human_review():
    alert = maybe_create_alert(
        _claim(classification="UNVERIFIED", confidence=0.3, reliability_score=10, reliability_band="LOW")
    )
    assert alert is not None
    assert "flagged for human review" in alert.reason_text.lower()


def test_acknowledge_is_idempotent():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        claim = _claim()
        db.add(claim)
        db.commit()
        db.refresh(claim)
        alert = maybe_create_alert(claim)
        claim.alerts.append(alert)
        db.commit()
        db.refresh(alert)

        alert.acknowledged = True
        db.commit()
        db.refresh(alert)
        assert alert.acknowledged is True

        alert.acknowledged = True  # acknowledging again is a no-op, not an error
        db.commit()
        db.refresh(alert)
        assert alert.acknowledged is True
    finally:
        db.close()
