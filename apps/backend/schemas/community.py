from typing import Literal, Optional

from pydantic import BaseModel, Field

from apps.backend.models.community import CONSENT_VERSION
from apps.backend.schemas.base import Form


class ContributionRequest(Form):
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=20, max_length=10000)
    category: str = Field(min_length=2, max_length=64)
    source: Optional[str] = Field(default=None, max_length=1000)
    consent_to_training: bool = False
    copyright_confirmed: bool = False


class ContributionResponse(BaseModel):
    id: int
    title: str
    category: str
    review_status: str
    consent_to_training: bool
    quality_rating: Optional[float]


class TrainingConsentRequest(BaseModel):
    consent_enabled: bool
    disclosure_version: Literal["2026-11-21"] = CONSENT_VERSION


class ContributionReviewRequest(Form):
    status: str = Field(pattern="^(approved|rejected)$")
    deidentified: bool = False
    quality_rating: Optional[float] = Field(default=None, ge=0, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)
    public_title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    public_body: Optional[str] = Field(default=None, min_length=20, max_length=10000)
    public_source: Optional[str] = Field(default=None, max_length=1000)
