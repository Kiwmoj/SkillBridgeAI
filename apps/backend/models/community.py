from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.database.base import Base, utcnow

# Version of the training-consent disclosure text that users agree to; stored with each consent record.
CONSENT_VERSION = "2026-11-21"


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


class TrainingConsent(Base):
    __tablename__ = "training_consent"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    consent_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    disclosure_version: Mapped[str] = mapped_column(String(32), default=CONSENT_VERSION)
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


class CommunityPolicy(Base):
    """Single-row table whose version counter serialises community writes across connections."""
    __tablename__ = "community_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    write_version: Mapped[int] = mapped_column(Integer, default=0)
