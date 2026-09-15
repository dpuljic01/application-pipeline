import httpx
from fastapi import HTTPException
from app.core.config import settings

COGNITO_URL_TEMPLATE = "https://cognito-idp.{region}.amazonaws.com/"


async def _initiate_auth(auth_flow: str, auth_parameters: dict[str, str]) -> dict:
    """
    Server-side call to Cognito's InitiateAuth — same public REST action the
    frontend used to call directly, just moved behind the backend so the
    refresh token never reaches browser JS.
    """
    url = COGNITO_URL_TEMPLATE.format(region=settings.COGNITO_REGION)
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    }
    payload = {
        "ClientId": settings.COGNITO_APP_CLIENT_ID,
        "AuthFlow": auth_flow,
        "AuthParameters": auth_parameters,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

    data = resp.json()
    if resp.status_code != 200:
        raise HTTPException(
            status_code=401, detail=data.get("message", "Authentication failed")
        )

    result = data.get("AuthenticationResult")
    if not result:
        raise HTTPException(status_code=401, detail="Authentication failed")

    return result


async def sign_in(username: str, password: str) -> dict:
    return await _initiate_auth(
        "USER_PASSWORD_AUTH",
        {"USERNAME": username, "PASSWORD": password},
    )


async def refresh_session(refresh_token: str) -> dict:
    # REFRESH_TOKEN_AUTH doesn't return a new refresh token (no rotation on
    # this pool) — the caller keeps reusing the one it already has.
    return await _initiate_auth(
        "REFRESH_TOKEN_AUTH",
        {"REFRESH_TOKEN": refresh_token},
    )
