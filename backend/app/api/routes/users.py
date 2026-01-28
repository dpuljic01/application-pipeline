from fastapi import APIRouter, Depends

from app.core.security.deps import CurrentUser, get_current_user
from app.api.schemas.user import UserMeResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: CurrentUser = Depends(get_current_user)) -> UserMeResponse:
    """
    Return the current application user.
    Requires access token.
    Ensures user exists in DB (get_or_create).
    """
    return UserMeResponse(
        sub=str(current_user.cognito_sub),
        email=current_user.email,
    )
