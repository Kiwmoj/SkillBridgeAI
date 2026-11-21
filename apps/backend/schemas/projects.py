from typing import Optional

from pydantic import BaseModel, Field

from apps.backend.schemas.base import Form


class ProjectRequest(Form):
    title: Optional[str] = Field(default=None, max_length=255)
    occupation: str = Field(min_length=1, max_length=255)
    occupation_id: Optional[int] = Field(default=None, gt=0)
    experience: str = Field(default="", max_length=2000)


class Milestone(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    done: bool = False


class ProjectUpdateRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=10000)
    milestones: Optional[list[Milestone]] = Field(default=None, max_length=30)
