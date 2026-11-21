from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="student")
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    recovery_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete")

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    education: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interests: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user = relationship("User", back_populates="profile")

class Occupation(Base):
    __tablename__ = "occupations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    onet_soc_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    titles = relationship("AlternateTitle", cascade="all, delete", back_populates="occupation")

class AlternateTitle(Base):
    __tablename__ = "alternate_titles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occupation_id: Mapped[int] = mapped_column(ForeignKey("occupations.id"))
    title: Mapped[str] = mapped_column(String(255), index=True)
    occupation = relationship("Occupation", back_populates="titles")
    __table_args__ = (UniqueConstraint("occupation_id", "title"),)

class Descriptor(Base):
    __tablename__ = "descriptors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occupation_id: Mapped[int] = mapped_column(ForeignKey("occupations.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    element_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    scale: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

class RelatedOccupation(Base):
    __tablename__ = "related_occupations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occupation_id: Mapped[int] = mapped_column(ForeignKey("occupations.id"), index=True)
    related_onet_soc_code: Mapped[str] = mapped_column(String(32), index=True)
    related_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    __table_args__ = (
        UniqueConstraint("occupation_id", "related_onet_soc_code"),
    )

class Roadmap(Base):
    __tablename__ = "roadmaps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    occupation_title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(1024))
    evaluation: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(32), default="image/png")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CommunityContribution(Base):
    __tablename__ = "community_contributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    quality_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    consent_to_training: Mapped[bool] = mapped_column(Boolean, default=False)
    deidentified: Mapped[bool] = mapped_column(Boolean, default=False)
    copyright_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    train_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="development")
    evaluation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=True)
    application_status: Mapped[str] = mapped_column(String(32), default="saved")

class SavedCareer(Base):
    __tablename__ = "saved_careers"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    occupation_id: Mapped[int] = mapped_column(ForeignKey("occupations.id"), primary_key=True)

class CustomOccupation(Base):
    __tablename__ = "custom_occupations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrainingConsent(Base):
    __tablename__ = "training_consent"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    consent_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    disclosure_version: Mapped[str] = mapped_column(String(32), default="2026-11-21")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ApprovedKnowledge(Base):
    __tablename__ = "approved_knowledge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_contribution_id: Mapped[int] = mapped_column(ForeignKey("community_contributions.id"), unique=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), index=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ReviewHistory(Base):
    __tablename__ = "review_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contribution_id: Mapped[int] = mapped_column(ForeignKey("community_contributions.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    quality_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AIUsage(Base):
    __tablename__ = "ai_usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    feature: Mapped[str] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    occupation_title: Mapped[str] = mapped_column(String(255))
    skill_name: Mapped[str] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class LearningActivity(Base):
    __tablename__ = "learning_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    roadmap_id: Mapped[int | None] = mapped_column(ForeignKey("roadmaps.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="not_started")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TrainingHistory(Base):
    __tablename__ = "training_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class DatasetRecord(Base):
    __tablename__ = "dataset_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id"),
        index=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    contribution_id: Mapped[int] = mapped_column(ForeignKey("community_contributions.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64))
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    split: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class CommunityPolicy(Base):
    __tablename__ = "community_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    write_version: Mapped[int] = mapped_column(Integer, default=0)
