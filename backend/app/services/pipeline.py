"""Day 12: the automatic parse -> score run for a newly created application.

Orchestration, not choreography: one function owns the sequence and decides
what happens on each step's failure, instead of steps reacting to each
other's events. Each step commits on its own (via ApplicationService), so a
scoring failure never loses the parsed JD - the user can retry scoring from
the detail page.

Runs via FastAPI BackgroundTasks, i.e. in the same process after the
response is sent. That's enough at this scale, with one known gap: if the
process restarts mid-run, the application stays PENDING. A real queue
(SQS, arq) would fix that and is the documented next step.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.enums import PipelineStatus
from app.domain.errors import (
    JDNotParsed,
    JDParseError,
    LLMBudgetExceeded,
    MatchingError,
    NotFound,
)
from app.integrations.llm.base import LLMProvider, LLMProviderError
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.tracked import TrackedLLMProvider
from app.services.application_service import ApplicationService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)


def _tracked(llm: LLMProvider, *, db: Session, operation: str) -> LLMProvider:
    return TrackedLLMProvider(
        llm,
        db=db,
        operation=operation,
        daily_budget_usd=settings.LLM_DAILY_BUDGET_USD,
    )


def process_new_application(
    *,
    db: Session,
    llm: LLMProvider,
    user_id: UUID,
    application_id: UUID,
    jd_text: str,
) -> None:
    service = ApplicationService(db)

    def fail(error: str) -> None:
        service.set_pipeline_status(
            user_id=user_id,
            application_id=application_id,
            status=PipelineStatus.FAILED,
            error=error,
        )

    try:
        service.parse_jd(
            user_id=user_id,
            application_id=application_id,
            llm=_tracked(llm, db=db, operation="parse_jd"),
            jd_text=jd_text,
        )
    except NotFound:
        return  # deleted before the run started
    except (JDParseError, LLMBudgetExceeded) as exc:
        fail(f"Parsing failed: {exc}")
        return

    profile = ProfileService(db).get_or_create_profile_for_user(user_id=user_id)
    try:
        service.score_application(
            user_id=user_id,
            application_id=application_id,
            llm=_tracked(llm, db=db, operation="match_insights"),
            profile=profile,
        )
    except NotFound:
        return
    except (JDNotParsed, MatchingError, LLMBudgetExceeded) as exc:
        fail(f"Scoring failed: {exc}")
        return

    service.set_pipeline_status(
        user_id=user_id,
        application_id=application_id,
        status=PipelineStatus.COMPLETED,
    )


def run_pipeline_in_background(
    *, user_id: UUID, application_id: UUID, jd_text: str
) -> None:
    """BackgroundTasks entry point. The request's DB session is closed by the
    time this runs, so it opens its own - the one place in services/ that
    does, because nothing upstream of a background task can own a session.
    """
    db = SessionLocal()
    try:
        if not settings.LLM_ENABLED:
            ApplicationService(db).set_pipeline_status(
                user_id=user_id,
                application_id=application_id,
                status=PipelineStatus.FAILED,
                error="AI features are disabled on this server",
            )
            return
        try:
            llm = get_llm_provider()
        except LLMProviderError as exc:
            ApplicationService(db).set_pipeline_status(
                user_id=user_id,
                application_id=application_id,
                status=PipelineStatus.FAILED,
                error=f"LLM provider unavailable: {exc}",
            )
            return
        process_new_application(
            db=db,
            llm=llm,
            user_id=user_id,
            application_id=application_id,
            jd_text=jd_text,
        )
    except Exception:
        # Nothing above the background task would ever see this - log it and
        # make sure the application doesn't sit in PENDING forever.
        logger.exception("Pipeline crashed for application %s", application_id)
        db.rollback()
        ApplicationService(db).set_pipeline_status(
            user_id=user_id,
            application_id=application_id,
            status=PipelineStatus.FAILED,
            error="Unexpected error while processing",
        )
    finally:
        db.close()
