from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_application_service, get_current_user_id
from app.api.schemas.application import ApplicationCreate, ApplicationRead
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead)
def create_application(
    payload: ApplicationCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    application = service.create_application(
        user_id=user_id,
        company=payload.company,
        role_title=payload.role_title,
        job_url=str(payload.job_url) if payload.job_url else None,
        location=payload.location,
        salary_range=payload.salary_range,
    )
    return application


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationRead:
    application = service.get_application_for_user(
        user_id=user_id,
        application_id=application_id,
    )
    if not application:
        raise HTTPException(status_code=404, detail="Not found")
    return application


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> list[ApplicationRead]:
    applications = service.list_applications_for_user(user_id=user_id)
    return applications
