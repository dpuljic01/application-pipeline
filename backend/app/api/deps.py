from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider as _get_llm_provider
from app.services.application_service import ApplicationService
from app.services.activity_service import ActivityService
from app.services.company_service import CompanyService
from app.services.profile_service import ProfileService


def get_llm_provider() -> LLMProvider:
    return _get_llm_provider()


def get_application_service(
    db: Session = Depends(get_db),
) -> ApplicationService:
    return ApplicationService(db)


def get_activity_service(
    db: Session = Depends(get_db),
) -> ActivityService:
    return ActivityService(db)


def get_company_service(
    db: Session = Depends(get_db),
) -> CompanyService:
    return CompanyService(db)


def get_profile_service(
    db: Session = Depends(get_db),
) -> ProfileService:
    return ProfileService(db)
