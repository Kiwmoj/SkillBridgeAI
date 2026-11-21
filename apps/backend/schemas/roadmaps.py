from typing import Literal, Optional

from pydantic import Field

from apps.backend.schemas.base import Form, SkillName


class RoadmapRequest(Form):
    occupation_title: str = Field(min_length=1, max_length=255)
    occupation_id: Optional[int] = Field(default=None, gt=0)
    interests: Optional[str] = Field(default=None, max_length=1000)
    current_skills: list[SkillName] = Field(default_factory=list, max_length=50)


class LearningActivityRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    roadmap_id: Optional[int] = Field(default=None, gt=0)
    status: Literal["not_started", "in_progress", "paused", "completed"] = "not_started"
    notes: Optional[str] = Field(default=None, max_length=5000)
