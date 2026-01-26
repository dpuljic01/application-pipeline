from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_activity_service, get_current_user_id
from app.api.schemas.activity import ActivityCreate, ActivityRead
from app.domain.errors import NotFound
from app.services.activity_service import ActivityService

router = APIRouter(
    prefix="/applications/{application_id}/activities",
    tags=["activities"],
)


@router.post("", response_model=ActivityRead, status_code=201)
def create_activity(
    application_id: UUID,
    payload: ActivityCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: ActivityService = Depends(get_activity_service),
):
    try:
        return service.log_activity(
            user_id=user_id,
            application_id=application_id,
            activity_type=payload.activity_type,
            note=payload.note,
        )
    except NotFound:
        raise HTTPException(status_code=404, detail="Application not found")
