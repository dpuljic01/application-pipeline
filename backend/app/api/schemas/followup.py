from pydantic import BaseModel, Field


class GenerateFollowUpRequest(BaseModel):
    context: str | None = Field(default=None, max_length=1000)
