from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.activity_repo import ActivityRepository
from app.domain.enums import ActivityType
from app.domain.errors import NotFound


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.application_repository = ApplicationRepository(db)
        self.activity_repository = ActivityRepository(db)

    def log_activity(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        activity_type: ActivityType,
        note: str | None = None,
        occurred_at: datetime | None = None,
    ):
        app = self.application_repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")

        activity = self.activity_repository.create(
            application_id=app.id,
            activity_type=activity_type,
            note=note,
            occurred_at=occurred_at,
        )
        # ensure defaults (created_at) are assigned before using them
        self.db.flush()

        # business rule: activity updates app timeline
        app.last_activity_at = activity.created_at

        self.db.commit()
        self.db.refresh(activity)
        return activity
