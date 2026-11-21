from pydantic import Field

from apps.backend.schemas.base import Form


class AIGenerateRequest(Form):
    purpose: str = Field(default="Career guidance", max_length=100)
    question: str = Field(min_length=1, max_length=5000)
