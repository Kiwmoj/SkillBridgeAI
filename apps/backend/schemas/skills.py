from typing import Optional

from pydantic import Field, model_validator

from apps.backend.schemas.base import Form, SkillName


class SkillGapRequest(Form):
    occupation_id: Optional[int] = Field(default=None, gt=0)
    occupation_title: Optional[str] = Field(default=None, max_length=255)
    current_skills: list[SkillName] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def require_occupation(self):
        if not self.occupation_id and not self.occupation_title:
            raise ValueError("Enter an occupation ID or title")
        return self


class SkillAssessmentRequest(Form):
    occupation_title: str = Field(min_length=1, max_length=255)
    skill_name: str = Field(min_length=1, max_length=255)
    rating: float = Field(ge=0, le=5)
