"""SQLAlchemy models grouped by domain.

Importing this package registers every table on ``Base.metadata`` so Alembic autogenerate and
``Base.metadata`` consumers see the complete schema.
"""
from apps.backend.models.analytics import AIUsage
from apps.backend.models.community import (
    CONSENT_VERSION,
    ApprovedKnowledge,
    CommunityContribution,
    CommunityPolicy,
    ReviewHistory,
    TrainingConsent,
)
from apps.backend.models.occupations import (
    AlternateTitle,
    CustomOccupation,
    Descriptor,
    Occupation,
    RelatedOccupation,
    SavedCareer,
)
from apps.backend.models.learning import LessonProgress, OnetCategory, OnetElement, OnetJobZone
from apps.backend.models.opportunities import OPPORTUNITY_CATEGORIES, Opportunity
from apps.backend.models.portfolio import Portfolio
from apps.backend.models.projects import Project
from apps.backend.models.roadmaps import LearningActivity, Roadmap
from apps.backend.models.skills import SkillAssessment
from apps.backend.models.training import DatasetRecord, DatasetVersion, ModelVersion, TrainingHistory
from apps.backend.models.users import Profile, User

__all__ = [
    "AIUsage", "AlternateTitle", "ApprovedKnowledge", "CONSENT_VERSION", "CommunityContribution",
    "CommunityPolicy", "CustomOccupation", "DatasetRecord", "DatasetVersion", "Descriptor",
    "LearningActivity", "LessonProgress", "ModelVersion", "OPPORTUNITY_CATEGORIES", "Occupation", "OnetCategory",
    "OnetElement", "OnetJobZone", "Opportunity", "Portfolio", "Profile", "Project",
    "RelatedOccupation", "ReviewHistory", "Roadmap", "SavedCareer", "SkillAssessment", "TrainingConsent",
    "TrainingHistory", "User",
]
