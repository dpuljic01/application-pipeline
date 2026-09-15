from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.activity import Activity
from app.domain.enums import ActivityType


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_application(self, *, application_id: UUID) -> list[Activity]:
        stmt = (
            select(Activity)
            .where(Activity.application_id == application_id)
            .order_by(Activity.occurred_at.desc())
        )
        return self.db.scalars(stmt).all()

    def create(
        self,
        *,
        application_id: UUID,
        activity_type: ActivityType,
        note: str | None = None,
        occurred_at: datetime | None = None,
    ) -> Activity:
        activity = Activity(
            application_id=application_id,
            activity_type=activity_type,
            note=note,
            occurred_at=occurred_at,
        )
        self.db.add(activity)
        return activity
