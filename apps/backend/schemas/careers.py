from typing import Optional

from pydantic import BaseModel, Field

from apps.backend.schemas.base import Form


class CustomOccupationRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)


class CareerCompareRequest(BaseModel):
    occupation_ids: list[int] = Field(min_length=2, max_length=5)
