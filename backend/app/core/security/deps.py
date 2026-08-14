from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security.cognito_jwt import TokenPayload, verify_jwt
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db

bearer = HTTPBearer()


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    cognito_sub: UUID
    email: str | None


# STEP 1: verify JWT and return TokenPayload (pure auth, no DB)
async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Security(bearer),
) -> TokenPayload:
    token = credentials.credentials
    return await verify_jwt(token)


# STEP 2: token-use guards (require that the token is an ID token) -> still return TokenPayload
async def require_id_token_payload(
    payload: TokenPayload = Depends(get_token_payload),
) -> TokenPayload:
    if payload.token_use != "id":
        raise HTTPException(status_code=401, detail="ID token required")
    return payload


async def require_access_token_payload(
    payload: TokenPayload = Depends(get_token_payload),
) -> TokenPayload:
    if payload.token_use != "access":
        raise HTTPException(status_code=401, detail="Access token required")
    return payload


# Step 3: map Cognito sub -> internal user_id (DB lookup/upsert)
async def get_current_user(
    db: Session = Depends(get_db),
    payload: TokenPayload = Depends(require_id_token_payload),
) -> CurrentUser:
    """
    AWS Cognito: 'sub' is immutable subject identifier.
    We map it to internal users.id so all DB ownership uses user_id
    """
    try:
        cognito_sub = UUID(payload.sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid sub claim in token")

    repo = UserRepository(db)
    user = repo.get_or_create(cognito_sub=cognito_sub, email=payload.email)

    # If UUID PK is DB-generated, flush is required to access user.id
    db.flush()
    return CurrentUser(user_id=user.id, cognito_sub=cognito_sub, email=user.email)
