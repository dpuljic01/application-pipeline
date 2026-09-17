from pydantic import BaseModel, Field


class ParseJDRequest(BaseModel):
    jd_text: str = Field(min_length=1)
