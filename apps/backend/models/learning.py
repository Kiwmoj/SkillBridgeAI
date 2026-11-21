"""O*NET reference data and per-user learning progress used by the Learning Center and career profiles."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.database.base import Base, utcnow


class OnetElement(Base):
    """An O*NET Content Model element (skill, knowledge area, ability, activity…) and its official definition."""
    __tablename__ = "onet_elements"
    element_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class OnetJobZone(Base):
    __tablename__ = "onet_job_zones"
    zone: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    training: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[str | None] = mapped_column(Text, nullable=True)


class OnetCategory(Base):
    """Labels for categorical scales, e.g. education level 6 = Bachelor's Degree."""
    __tablename__ = "onet_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    element_id: Mapped[str] = mapped_column(String(32), index=True)
    scale_id: Mapped[str] = mapped_column(String(8))
    category: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("element_id", "scale_id", "category"),)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    element_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "element_id"),)
