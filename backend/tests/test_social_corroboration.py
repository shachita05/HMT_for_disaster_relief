from dataclasses import dataclass

from app.services.social_corroboration import HIGH_THRESHOLD, has_fact_check_false, social_level


@dataclass
class _Ev:
    evidence_type: str
    source: str


def _social(accounts: list[str]) -> list[_Ev]:
    return [_Ev(evidence_type="social_corroboration", source=a) for a in accounts]


def test_none_when_no_social_evidence():
    level, count = social_level([_Ev(evidence_type="fact_check_true", source="PolitiFact")])
    assert level == "NONE"
    assert count == 0


def test_some_below_high_threshold():
    level, count = social_level(_social(["a", "b"]))
    assert level == "SOME"
    assert count == 2


def test_high_at_threshold():
    level, count = social_level(_social([f"acct{i}" for i in range(HIGH_THRESHOLD)]))
    assert level == "HIGH"
    assert count == HIGH_THRESHOLD


def test_duplicate_accounts_counted_once():
    # same account posting 3 times must not inflate the count
    level, count = social_level(_social(["same", "same", "same"]))
    assert count == 1
    assert level == "SOME"


def test_ignores_non_social_evidence_types():
    evidence = _social(["a", "b", "c", "d", "e"]) + [_Ev(evidence_type="news_article_match", source="BBC")]
    level, count = social_level(evidence)
    assert count == 5
    assert level == "HIGH"


def test_has_fact_check_false_true_and_false_cases():
    assert has_fact_check_false([_Ev(evidence_type="fact_check_false", source="Alt News")]) is True
    assert has_fact_check_false([_Ev(evidence_type="fact_check_true", source="Alt News")]) is False
    assert has_fact_check_false([]) is False
