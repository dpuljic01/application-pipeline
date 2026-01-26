from sqlalchemy.orm import Session

from app.db.models.activity import Activity
from app.domain.enums import ActivityType


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        application_id: str,
        activity_type: ActivityType,
        note: str | None = None,
    ) -> Activity:
        activity = Activity(
            application_id=application_id,
            activity_type=activity_type,
            note=note,
        )
        self.db.add(activity)
        return activity