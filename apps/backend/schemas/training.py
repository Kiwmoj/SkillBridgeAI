from typing import Literal, Optional

from pydantic import Field

from apps.backend.schemas.base import Form


class DatasetBuildRequest(Form):
    name: str = Field(min_length=3, max_length=255)


class ModelVersionRequest(Form):
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(default="skillbridge", min_length=1, max_length=64)
    status: Literal["development", "evaluated"] = "development"
    evaluation_summary: Optional[str] = Field(default=None, max_length=5000)
