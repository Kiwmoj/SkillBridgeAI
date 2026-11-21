"""Pydantic request and response models grouped by domain."""
from apps.backend.schemas.auth import (
    LoginRequest,
    PasswordConfirmation,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from apps.backend.schemas.base import Form, SkillName
from apps.backend.schemas.careers import CareerCompareRequest, CustomOccupationRequest
from apps.backend.schemas.community import (
    ContributionRequest,
    ContributionResponse,
    ContributionReviewRequest,
    TrainingConsentRequest,
)
from apps.backend.schemas.guidance import AIGenerateRequest
from apps.backend.schemas.opportunities import OpportunitySaveRequest, OpportunityStatusRequest
from apps.backend.schemas.portfolio import PortfolioReviewRequest
from apps.backend.schemas.profiles import ProfileRequest
from apps.backend.schemas.projects import ProjectRequest, ProjectUpdateRequest
from apps.backend.schemas.roadmaps import LearningActivityRequest, RoadmapRequest
from apps.backend.schemas.skills import SkillAssessmentRequest, SkillGapRequest
from apps.backend.schemas.training import DatasetBuildRequest, ModelVersionRequest

__all__ = [
    "AIGenerateRequest", "CareerCompareRequest", "ContributionRequest", "ContributionResponse",
    "ContributionReviewRequest", "CustomOccupationRequest", "DatasetBuildRequest", "Form",
    "LearningActivityRequest", "LoginRequest", "ModelVersionRequest", "OpportunitySaveRequest",
    "OpportunityStatusRequest", "PasswordConfirmation", "PasswordResetRequest", "PortfolioReviewRequest",
    "ProfileRequest", "ProjectRequest", "ProjectUpdateRequest", "RegisterRequest", "RoadmapRequest",
    "SkillAssessmentRequest", "SkillGapRequest", "SkillName", "TokenResponse", "TrainingConsentRequest",
]
