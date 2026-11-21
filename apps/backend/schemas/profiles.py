from typing import Optional

from pydantic import Field

from apps.backend.schemas.base import Form


class ProfileRequest(Form):
    education: Optional[str] = Field(default=None, max_length=255)
    interests: Optional[str] = Field(default=None, max_length=2000)
    goals: Optional[str] = Field(default=None, max_length=4000)
    location: Optional[str] = Field(default=None, max_length=255)
