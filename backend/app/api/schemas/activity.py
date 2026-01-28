from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import ActivityType


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    note: str | None = Field(default=None, max_length=5000)


class ActivityRead(BaseModel):
    id: UUID
    application_id: UUID
    activity_type: ActivityType
    note: str | None
    created_at: datetime
