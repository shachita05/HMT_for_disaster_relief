from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.schemas.location import LocationOut
from app.schemas.evidence import EvidenceOut
from app.services import social_corroboration
from app.services.verification_message import build_verification_message, compute_overall_verdict

MAX_CLAIM_LENGTH = 2000


class ClaimCreate(BaseModel):
    text: str
    source: str = "manual"
    source_url: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("claim text must not be empty")
        if len(v) > MAX_CLAIM_LENGTH:
            raise ValueError(f"claim text must be at most {MAX_CLAIM_LENGTH} characters")
        return v

    @field_validator("source_url")
    @classmethod
    def source_url_scheme(cls, v: str | None) -> str | None:
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must start with http:// or https://")
        return v


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    source: str
    source_url: str | None
    submitted_at: datetime
    disaster_type: str
    classification: str
    confidence: float
    reliability_score: int | None
    reliability_band: str | None
    priority: str
    priority_score: int
    verification_status: str
    is_historical_seed: bool


class ClaimDetail(ClaimOut):
    all_disaster_types: list[str]
    top_terms: list
    priority_reasons: list[str]
    reliability_reasons: list[str]
    reason: str | None
    locations: list[LocationOut]
    evidence: list[EvidenceOut]

    def _verdict_signals(self):
        """Shared derivation used by both official_verification_message and
        overall_verdict below, so they can never read different inputs and
        drift apart. evidence_type carries the normalized fact-check rating
        directly (fact_check_false | fact_check_true | fact_check_mixed) --
        set by pipeline_service.py -- rather than needing to re-parse free
        text here, and rather than adding a new Claim column (see
        db/models.py docstring on why schema changes are avoided)."""
        has_live_official_match = any(e.evidence_type == "live_feed_match" for e in self.evidence)

        # FALSE preferred over TRUE if both are present among multiple
        # fact-checker reviews -- mirrors google_fact_check.aggregate_verdict's
        # own FALSE-beats-TRUE precedence.
        fact_check_evidence = next(
            (e for e in self.evidence if e.evidence_type == "fact_check_false"), None
        ) or next((e for e in self.evidence if e.evidence_type == "fact_check_true"), None)
        fact_check_verdict = None
        fact_check_publisher = None
        if fact_check_evidence is not None:
            fact_check_verdict = "FALSE" if fact_check_evidence.evidence_type == "fact_check_false" else "TRUE"
            fact_check_publisher = fact_check_evidence.source

        social_level, social_account_count = social_corroboration.social_level(self.evidence)

        return has_live_official_match, fact_check_verdict, fact_check_publisher, social_level, social_account_count

    @computed_field
    @property
    def official_verification_message(self) -> str:
        has_live_official_match, fact_check_verdict, fact_check_publisher, social_level, social_account_count = (
            self._verdict_signals()
        )
        return build_verification_message(
            classification=self.classification,
            confidence=self.confidence,
            reliability_band=self.reliability_band,
            has_live_official_match=has_live_official_match,
            fact_check_verdict=fact_check_verdict,
            fact_check_publisher=fact_check_publisher,
            social_level=social_level,
            social_account_count=social_account_count,
        )

    @computed_field
    @property
    def overall_verdict(self) -> str:
        """TRUE | FAKE | DISPUTED | UNVERIFIED -- see
        verification_message.compute_overall_verdict's docstring for why
        this exists as a field distinct from `classification`."""
        has_live_official_match, fact_check_verdict, _, social_level, _ = self._verdict_signals()
        return compute_overall_verdict(
            classification=self.classification,
            confidence=self.confidence,
            has_live_official_match=has_live_official_match,
            fact_check_verdict=fact_check_verdict,
            social_level=social_level,
        )


class ClaimListResponse(BaseModel):
    total: int
    items: list[ClaimOut]
