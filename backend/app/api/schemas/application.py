from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, AnyHttpUrl, Field, ConfigDict

from app.domain.enums import ApplicationStage
from app.services.followup_generator import FollowUpEmail
from app.services.jd_parser import ParsedJobDescription
from app.services.matcher import MatchDetails


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role_title: str = Field(min_length=1, max_length=128)
    job_url: AnyHttpUrl | None = None
    location: str | None = None
    salary_range: str | None = None
    # Optional: link to an existing Company explicitly. Omit it and the
    # service auto-creates/links one by matching `company` (case-insensitive)
    # against the user's existing companies.
    company_id: UUID | None = None


class StageChangeRequest(BaseModel):
    stage: ApplicationStage


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role_title: str | None = Field(default=None, min_length=1, max_length=128)
    job_url: AnyHttpUrl | None = None
    location: str | None = None
    salary_range: str | None = None
    stage_changed_at: datetime | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company: str
    company_id: UUID | None
    role_title: str
    job_url: str | None
    location: str | None
    salary_range: str | None
    stage: ApplicationStage
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime | None
    stage_changed_at: datetime | None
    parsed_jd: ParsedJobDescription | None
    match_score: int | None
    match_details: MatchDetails | None
    generated_followup: FollowUpEmail | None
