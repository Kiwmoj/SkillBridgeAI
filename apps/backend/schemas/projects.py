from typing import Optional

from pydantic import BaseModel, Field

from apps.backend.schemas.base import Form


class ProjectRequest(Form):
    title: Optional[str] = Field(default=None, max_length=255)
    occupation: str = Field(min_length=1, max_length=255)
    experience: str = Field(default="", max_length=2000)


class ProjectUpdateRequest(BaseModel):
    status: str
