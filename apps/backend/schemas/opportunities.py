from typing import Literal, Optional

from pydantic import Field, HttpUrl

from apps.backend.schemas.base import Form


class OpportunitySaveRequest(Form):
    title: str = Field(min_length=1, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    url: Optional[HttpUrl] = None
    details: Optional[str] = Field(default=None, max_length=5000)


class OpportunityStatusRequest(Form):
    application_status: Literal["saved", "preparing", "applied", "closed"]
