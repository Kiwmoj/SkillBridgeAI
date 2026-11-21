from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.database.base import Base, utcnow


class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    occupation_title: Mapped[str] = mapped_column(String(255))
    skill_name: Mapped[str] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
