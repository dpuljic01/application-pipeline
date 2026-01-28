from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.core.security.deps import require_id_token_payload
from app.core.security.cognito_jwt import TokenPayload

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: str
    email: str | None


@router.get("/me", response_model=MeResponse)
async def me(payload: TokenPayload = Depends(require_id_token_payload)) -> MeResponse:
    """
    Get information about the currently authenticated user.
    Requires a valid ID token.
    Returns the token payload containing user information.
    """
    return MeResponse(sub=payload.sub, email=payload.email)
