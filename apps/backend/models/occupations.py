from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.backend.database.base import Base, utcnow


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
