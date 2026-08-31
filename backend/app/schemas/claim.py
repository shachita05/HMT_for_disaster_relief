from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.schemas.location import LocationOut
from app.schemas.evidence import EvidenceOut
from app.services.verification_message import build_verification_message

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

    @computed_field
    @property
    def official_verification_message(self) -> str:
        has_live_official_match = any(e.evidence_type == "live_feed_match" for e in self.evidence)
        return build_verification_message(
            classification=self.classification,
            confidence=self.confidence,
            reliability_band=self.reliability_band,
            has_live_official_match=has_live_official_match,
        )


class ClaimListResponse(BaseModel):
    total: int
    items: list[ClaimOut]
