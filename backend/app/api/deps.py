from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider as _get_llm_provider
from app.integrations.llm.tracked import TrackedLLMProvider
from app.services.application_service import ApplicationService
from app.services.activity_service import ActivityService
from app.services.company_service import CompanyService
from app.services.pipeline import run_pipeline_in_background
from app.services.profile_service import ProfileService


def get_llm_provider() -> LLMProvider:
    return _get_llm_provider()


def tracked_llm(operation: str) -> Callable[..., LLMProvider]:
    """Dependency factory: the configured provider, wrapped with usage
    logging + the daily budget check, labelled with the route's operation.

    Tests override `get_llm_provider` (the inner provider), so the tracking
    layer still runs around their fakes.
    """

    def dependency(
        db: Session = Depends(get_db),
        llm: LLMProvider = Depends(get_llm_provider),
    ) -> LLMProvider:
        return TrackedLLMProvider(
            llm,
            db=db,
            operation=operation,
            daily_budget_usd=settings.LLM_DAILY_BUDGET_USD,
        )

    return dependency


def get_pipeline_runner() -> Callable[..., None]:
    # A dependency (not a direct import in the route) so tests can swap in a
    # runner that uses the test's transactional session and a fake LLM.
    return run_pipeline_in_background


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
