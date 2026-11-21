from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator, StringConstraints
from typing import Annotated, Literal, Optional

class Form(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
CONSENT_VERSION = "2026-11-21"

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class PasswordResetRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    recovery_code: str = Field(min_length=1, max_length=100)

class PasswordConfirmation(BaseModel):
    password: str = Field(min_length=1, max_length=128)

class PortfolioReviewRequest(Form):
    send_to_provider: Literal[True]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class ProfileRequest(Form):
    education: Optional[str] = Field(default=None, max_length=255)
    interests: Optional[str] = Field(default=None, max_length=2000)
    goals: Optional[str] = Field(default=None, max_length=4000)
    location: Optional[str] = Field(default=None, max_length=255)

class ProfileResponse(ProfileRequest):
    id: int
    user_id: int

class OccupationResponse(BaseModel):
    id: int
    onet_soc_code: str
    title: str
    description: Optional[str]
    dataset_version: Optional[str]

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

class AIGenerateRequest(Form):
    purpose: str = Field(default="Career guidance", max_length=100)
    question: str = Field(min_length=1, max_length=5000)

class SkillGapRequest(Form):
    occupation_id: Optional[int] = Field(default=None, gt=0)
    occupation_title: Optional[str] = Field(default=None, max_length=255)
    current_skills: list[SkillName] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def require_occupation(self):
        if not self.occupation_id and not self.occupation_title:
            raise ValueError("Enter an occupation ID or title")
        return self

class RoadmapRequest(Form):
    occupation_title: str = Field(min_length=1, max_length=255)
    interests: Optional[str] = Field(default=None, max_length=1000)
    current_skills: list[SkillName] = Field(default_factory=list, max_length=50)

class ProjectRequest(Form):
    title: Optional[str] = Field(default=None, max_length=255)
    occupation: str = Field(min_length=1, max_length=255)
    experience: str = Field(default="", max_length=2000)

class ProjectUpdateRequest(BaseModel):
    status: str

class CustomOccupationRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)

class CareerCompareRequest(BaseModel):
    occupation_ids: list[int] = Field(min_length=2, max_length=5)

class OpportunitySaveRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    url: Optional[HttpUrl] = None
    details: Optional[str] = Field(default=None, max_length=5000)

class OpportunityStatusRequest(Form):
    application_status: Literal["saved", "preparing", "applied", "closed"]

class SkillAssessmentRequest(Form):
    occupation_title: str = Field(min_length=1, max_length=255)
    skill_name: str = Field(min_length=1, max_length=255)
    rating: float = Field(ge=0, le=5)

class LearningActivityRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    roadmap_id: Optional[int] = Field(default=None, gt=0)
    status: Literal["not_started", "in_progress", "paused", "completed"] = "not_started"
    notes: Optional[str] = Field(default=None, max_length=5000)

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

class DatasetBuildRequest(Form):
    name: str = Field(min_length=3, max_length=255)

class ModelVersionRequest(Form):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(default="skillbridge", min_length=1, max_length=64)
    status: Literal["development", "evaluated"] = "development"
    evaluation_summary: Optional[str] = Field(default=None, max_length=5000)
