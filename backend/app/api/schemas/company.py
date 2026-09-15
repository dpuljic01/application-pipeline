from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.domain.enums import CompanySize


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: AnyHttpUrl | None = None
    industry: str | None = Field(default=None, max_length=120)
    size: CompanySize | None = None
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    website: AnyHttpUrl | None = None
    industry: str | None = Field(default=None, max_length=120)
    size: CompanySize | None = None
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website: str | None
    industry: str | None
    size: CompanySize | None
    location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
