from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security.deps import require_id_token_payload
from app.core.security.cognito_jwt import TokenPayload, verify_jwt
from app.core.security.cognito_auth import sign_in, refresh_session
from app.db.session import get_db
from app.services.demo_service import DemoService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # Cognito's default refresh-token validity


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: str
    email: str | None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    id_token: str


def _refresh_cookie_kwargs() -> dict:
    is_prod = settings.APP_ENV == "production"
    return {
        "httponly": True,
        "secure": is_prod,
        # Cross-site (Vercel <-> Render) needs SameSite=None + Secure; same-site
        # localhost dev works fine with Lax and no Secure requirement.
        "samesite": "none" if is_prod else "lax",
        "path": REFRESH_COOKIE_PATH,
    }


@router.get("/me", response_model=MeResponse)
async def me(payload: TokenPayload = Depends(require_id_token_payload)) -> MeResponse:
    """
    Get information about the currently authenticated user.
    Requires a valid ID token.
    Returns the token payload containing user information.
    """
    return MeResponse(sub=payload.sub, email=payload.email)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response) -> TokenResponse:
    result = await sign_in(body.username, body.password)
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        result["RefreshToken"],
        max_age=REFRESH_COOKIE_MAX_AGE,
        **_refresh_cookie_kwargs(),
    )
    return TokenResponse(id_token=result["IdToken"])


@router.post("/demo", response_model=TokenResponse)
async def demo_login(
    response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    """One-click login to the shared demo account. Re-seeds its data unless
    another visitor did so within the last 15 minutes.

    Only an ID token (plus the HttpOnly refresh cookie) reaches the browser,
    never the access token - so a visitor can't call Cognito's
    ChangePassword/DeleteUser on the shared account.
    """
    if not settings.DEMO_EMAIL or not settings.DEMO_PASSWORD:
        raise HTTPException(status_code=404, detail="Demo is not enabled")

    result = await sign_in(settings.DEMO_EMAIL, settings.DEMO_PASSWORD)
    payload = await verify_jwt(result["IdToken"])
    user = UserService(db).get_or_create_current_user(
        cognito_sub=UUID(payload.sub), email=payload.email
    )
    # ~50 inserts: small, but blocking - keep it off the event loop.
    await run_in_threadpool(DemoService(db).reset_if_stale, user_id=user.id)

    response.set_cookie(
        REFRESH_COOKIE_NAME,
        result["RefreshToken"],
        max_age=REFRESH_COOKIE_MAX_AGE,
        **_refresh_cookie_kwargs(),
    )
    return TokenResponse(id_token=result["IdToken"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request) -> TokenResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No session")

    result = await refresh_session(refresh_token)
    return TokenResponse(id_token=result["IdToken"])


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
