import httpx
import pytest
from fastapi import HTTPException

from app.core.security.cognito_jwt import JWKSCache


@pytest.mark.asyncio
async def test_fetch_jwks_unreachable_raises_503_not_500(monkeypatch):
    cache = JWKSCache()

    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FailingClient())

    with pytest.raises(HTTPException) as exc_info:
        await cache.fetch_jwks()

    assert exc_info.value.status_code == 503
    # The raw exception text (URLs, timeouts) isn't leaked to the client.
    assert "connection refused" not in exc_info.value.detail
