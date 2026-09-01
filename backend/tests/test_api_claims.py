import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import engine
from app.external_feeds.google_fact_check import FactCheckResult
from app.external_feeds.newsapi_feed import NewsArticle

client = TestClient(app)

SAMPLE = "Heavy rainfall has caused severe flooding in Whitefield, Bengaluru."


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_create_claim_returns_full_analysis():
    resp = client.post("/api/claims", json={"text": SAMPLE})
    assert resp.status_code == 201
    body = resp.json()
    assert body["disaster_type"] == "Flood"
    assert len(body["locations"]) > 0
    assert body["classification"] in ("TRUE", "FAKE", "UNVERIFIED")
    assert 0.0 <= body["confidence"] <= 1.0


def test_create_then_get_claim_roundtrip():
    created = client.post("/api/claims", json={"text": SAMPLE}).json()
    fetched = client.get(f"/api/claims/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["text"] == SAMPLE
    assert fetched["disaster_type"] == created["disaster_type"]


def test_get_missing_claim_404():
    resp = client.get("/api/claims/999999")
    assert resp.status_code == 404


def test_empty_claim_text_rejected():
    resp = client.post("/api/claims", json={"text": "   "})
    assert resp.status_code == 422


def test_list_claims_filter_by_verdict():
    created = client.post("/api/claims", json={"text": SAMPLE}).json()
    resp = client.get("/api/claims", params={"verdict": created["classification"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(c["id"] == created["id"] for c in body["items"])


def test_fact_check_false_caps_reliability_low_without_changing_classification():
    fake_result = FactCheckResult(
        publisher="PolitiFact",
        title=SAMPLE,
        url="https://example.com/review",
        textual_rating="False",
        normalized_rating="FALSE",
    )
    with patch("app.external_feeds.google_fact_check.search", return_value=[fake_result]):
        resp = client.post("/api/claims", json={"text": SAMPLE})
    assert resp.status_code == 201
    body = resp.json()

    assert body["reliability_band"] == "LOW"
    assert "PolitiFact" in body["official_verification_message"]
    assert "False" in body["official_verification_message"]
    fact_check_evidence = [e for e in body["evidence"] if e["evidence_type"] == "fact_check_false"]
    assert len(fact_check_evidence) == 1
    assert fact_check_evidence[0]["source"] == "PolitiFact"


def test_newsapi_article_becomes_evidence_without_overriding_message():
    article = NewsArticle(
        source_name="The Hindu",
        title="Heavy rains cause flooding in Bengaluru",
        url="https://example.com/article1",
        published_at=None,
    )
    with patch("app.external_feeds.newsapi_feed.search", return_value=[article]):
        resp = client.post("/api/claims", json={"text": SAMPLE})
    assert resp.status_code == 201
    body = resp.json()

    news_evidence = [e for e in body["evidence"] if e["evidence_type"] == "news_article_match"]
    assert len(news_evidence) == 1
    assert news_evidence[0]["source"] == "The Hindu"
    # A NewsAPI hit alone must never claim official/fact-checked confirmation.
    assert "official sources" not in body["official_verification_message"]
    assert "fact-checker" not in body["official_verification_message"].lower()


def test_api_matches_cli_pipeline_output():
    """Regression guard: the API must wrap analyze_claim(), not reimplement it."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
    from analyze_claim import analyze_claim

    cli_result = analyze_claim(SAMPLE)
    api_result = client.post("/api/claims", json={"text": SAMPLE}).json()

    assert api_result["disaster_type"] == cli_result["disaster_type"]
    assert api_result["classification"] == cli_result["prediction"]
    assert api_result["priority"] == cli_result["priority"]
    assert api_result["priority_score"] == cli_result["priority_score"]
