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
