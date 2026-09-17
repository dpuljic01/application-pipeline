import httpx
from fastapi import HTTPException
import logging
import time
from typing import Any, Dict, Optional
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class JWKSCache:
    """
    A simple in-memory cache for Cognito JWKs.
    Concepts:
    - JWKS: set of public keys Cognito publishes for verifying JWT signatures.
    - Caching: avoids fetching keys on every request.
    - Key rotation: if token `kid` isn't found, refresh JWKS once.
    """

    def __init__(self, ttl_seconds: int = 1800) -> None:
        self.ttl_seconds = ttl_seconds
        self.jwks: Optional[Dict[str, Any]] = None
        self.last_fetched_at: float = 0.0

    def is_expired(self) -> bool:
        """Return True if cache is empty or TTL has passed."""
        if self.jwks is None:
            return True

        now = time.time()
        age = now - self.last_fetched_at
        return age > self.ttl_seconds

    async def get_jwks(self) -> Dict[str, Any]:
        """Return cached JWKs if not expired, else fetch new JWKs."""
        if self.is_expired():
            await self.fetch_jwks()

        return self.jwks or {}

    async def fetch_jwks(self) -> None:
        """Fetch JWKS from Cognito and update cache."""

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(settings.cognito_jwks_url)
                resp.raise_for_status()
                self.jwks = resp.json()
                self.last_fetched_at = time.time()
        except httpx.HTTPError as e:
            # 503, not 500: our code isn't broken, Cognito's JWKS endpoint is
            # unreachable - a retry-later situation for the client, not a bug
            # here. The underlying error is logged server-side, not leaked to
            # the client (it can include internal URLs/timeouts).
            logger.warning("Failed to fetch Cognito JWKS: %s", e)
            raise HTTPException(
                status_code=503,
                detail="Authentication service temporarily unavailable",
            )

    def clear(self) -> None:
        """Clear the JWKS cache."""
        self.jwks = None
        self.last_fetched_at = 0.0


jwks_cache = JWKSCache(ttl_seconds=1800)


class TokenPayload(BaseModel):
    """
    Represents the payload of a Cognito JWT token
    """

    # Concept: `sub` tells who the user is, `token_use` tells "id" vs "access"
    sub: str
    token_use: str
    exp: int
    iat: int

    # Identity claims usually live in ID token (if scopes include email/profile)
    email: Optional[str] = None  # user identity
    username: Optional[str] = None

    class Config:
        extra = "allow"


async def get_verification_jwk(token: str) -> Dict[str, Any]:
    """
    Return the JWK dict matching token header `kid`.

    Concept:
    - JWT header has `kid` = which key was used to sign.
    - We pick that key from JWKS to verify signature.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {e}")

    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token header missing 'kid'")

    # 1) Use cached JWKS (fetch only if expired)
    jwks = await jwks_cache.get_jwks()
    keys = jwks.get("keys", [])

    for key in keys:
        if key.get("kid") == kid:
            return key

    # 2) Key rotation path: refresh once if kid not found
    jwks_cache.clear()
    jwks = await jwks_cache.get_jwks()
    keys = jwks.get("keys", [])

    for key in keys:
        if key.get("kid") == kid:
            return key

    raise HTTPException(status_code=401, detail="Signing key not found (unknown kid)")


async def verify_jwt(token: str) -> TokenPayload:
    """
    Verify JWT signature + standard claims.

    Concepts:
    - Signature verification uses JWK (public key).
    - Claim checks:
      - iss (issuer) must match Cognito user pool issuer
      - aud (audience) must match your app client id (works for ID tokens)
      - exp must not be expired
    """
    verification_jwk = await get_verification_jwk(token)

    try:
        payload = jwt.decode(
            token,
            verification_jwk,
            algorithms=["RS256"],
            audience=settings.COGNITO_APP_CLIENT_ID,
            issuer=settings.cognito_issuer,
            options={
                "verify_at_hash": False,
            },
        )
        return TokenPayload(**payload)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
