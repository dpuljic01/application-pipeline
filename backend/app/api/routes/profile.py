from fastapi import APIRouter, Depends

from app.api.deps import get_profile_service
from app.api.schemas.profile import ProfileRead, ProfileUpdate
from app.core.security.deps import CurrentUser, get_current_user
from app.db.models.profile import Profile
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    return service.get_or_create_profile_for_user(user_id=current_user.user_id)


@router.put("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    data = payload.model_dump(exclude_unset=True)
    return service.update_profile(user_id=current_user.user_id, data=data)
