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

    def get_latest_stage_change(self, *, application_id: UUID) -> Activity | None:
        # Newest by insert time, not occurred_at: the last transition made is
        # the one that set the current stage, even if it was backdated to
        # before an earlier one.
        stmt = (
            select(Activity)
            .where(
                Activity.application_id == application_id,
                Activity.activity_type == ActivityType.STAGE_CHANGE,
            )
            .order_by(Activity.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def update_occurred_at(self, *, activity: Activity, occurred_at: datetime) -> None:
        activity.occurred_at = occurred_at

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
