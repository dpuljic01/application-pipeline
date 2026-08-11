from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, AnyHttpUrl, Field, ConfigDict

from app.domain.enums import ApplicationStage


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role_title: str = Field(min_length=1, max_length=128)
    job_url: AnyHttpUrl | None = None
    location: str | None = None
    salary_range: str | None = None


class StageChangeRequest(BaseModel):
    stage: ApplicationStage


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role_title: str | None = Field(default=None, min_length=1, max_length=128)
    job_url: AnyHttpUrl | None = None
    location: str | None = None
    salary_range: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company: str
    role_title: str
    job_url: str | None
    location: str | None
    salary_range: str | None
    stage: ApplicationStage
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime | None
    stage_changed_at: datetime | None
