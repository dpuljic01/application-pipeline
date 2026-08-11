from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_application_service, get_current_user_id
from app.api.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    StageChangeRequest,
)
from app.db.models.application import Application
from app.domain.errors import InvalidTransition, NotFound
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead)
def create_application(
    payload: ApplicationCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> Application:
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
) -> Application:
    try:
        return service.get_application_for_user(
            user_id=user_id,
            application_id=application_id,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> list[Application]:
    applications = service.list_applications_for_user(user_id=user_id)
    return applications


@router.put("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> Application:
    try:
        return service.update_application(
            user_id=user_id,
            application_id=application_id,
            payload=payload,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Application not found")


@router.patch("/{application_id}/stage", response_model=ApplicationRead)
def change_stage(
    application_id: UUID,
    payload: StageChangeRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ApplicationService = Depends(get_application_service),
) -> Application:
    try:
        application = service.change_stage(
            user_id=user_id,
            application_id=application_id,
            stage=payload.stage,
        )
        return application
    except NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
