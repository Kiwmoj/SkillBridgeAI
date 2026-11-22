from typing import Literal, Optional

from pydantic import BaseModel, Field

from apps.backend.schemas.base import Form


class PortfolioReviewRequest(Form):
    send_to_provider: Literal[True]


class PortfolioUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    tags: Optional[list[str]] = Field(default=None, max_length=10)
    project_id: Optional[int] = Field(default=None, gt=0)
    featured: Optional[bool] = None
