from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ActivityType


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    note: str | None = Field(default=None, max_length=5000)
    occurred_at: datetime | None = None


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    activity_type: ActivityType
    note: str | None
    created_at: datetime
    occurred_at: datetime
