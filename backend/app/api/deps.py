from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.application_service import ApplicationService
from app.services.activity_service import ActivityService


def get_application_service(
    db: Session = Depends(get_db),
) -> ApplicationService:
    return ApplicationService(db)


def get_activity_service(
    db: Session = Depends(get_db),
) -> ActivityService:
    return ActivityService(db)


def get_current_user_id() -> UUID:
    # TODO: replace with Cognito JWT verification when implemented
    return UUID("d2b258bb-fa56-4b12-a16c-bf1fdd39a837")
