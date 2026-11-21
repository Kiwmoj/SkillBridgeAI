from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.database.base import Base, utcnow


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    train_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_count: Mapped[int] = mapped_column(Integer, default=0)
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


class TrainingHistory(Base):
    __tablename__ = "training_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="development")
    evaluation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
