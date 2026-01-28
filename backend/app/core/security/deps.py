from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security.cognito_jwt import TokenPayload, verify_jwt

bearer = HTTPBearer()


# Concept: Dependency Injection: reuse auth logic across endpoints
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer),
) -> TokenPayload:
    """
    Dependency to get the current user from the JWT token in the Authorization header.
    Raises 401 if token is missing or invalid.
    """
    token = credentials.credentials
    return await verify_jwt(token)


# Concept: /me uses ID token (identity claims like email)
async def require_id_token(
    user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Dependency to require that the token is an ID token.
    Raises 401 if the token is not an ID token.
    """
    if user.token_use != "id":
        raise HTTPException(status_code=401, detail="ID token required")
    return user


# Concept: protect API endpoints with access token
async def require_access_token(
    user: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    if user.token_use != "access":
        raise HTTPException(status_code=401, detail="Access token required")
    return user
