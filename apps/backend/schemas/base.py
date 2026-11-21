from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class Form(BaseModel):
    """Request body that strips whitespace and rejects unknown fields."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
