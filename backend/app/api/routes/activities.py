from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_activity_service
from app.api.schemas.activity import ActivityCreate, ActivityRead
from app.core.security.deps import CurrentUser, get_current_user
from app.db.models.activity import Activity
from app.domain.errors import NotFound
from app.services.activity_service import ActivityService

router = APIRouter(
    prefix="/applications/{application_id}/activities",
    tags=["activities"],
)


@router.get("", response_model=list[ActivityRead])
async def list_activities(
    application_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ActivityService = Depends(get_activity_service),
) -> list[Activity]:
    try:
        return service.list_activities(
            user_id=current_user.user_id,
            application_id=application_id,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Application not found")


@router.post("", response_model=ActivityRead, status_code=201)
async def create_activity(
    application_id: UUID,
    payload: ActivityCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ActivityService = Depends(get_activity_service),
) -> Activity:
    try:
        return service.log_activity(
            user_id=current_user.user_id,
            application_id=application_id,
            activity_type=payload.activity_type,
            note=payload.note,
            occurred_at=payload.occurred_at,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Application not found")
