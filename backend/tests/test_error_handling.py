"""Tests for the global exception handlers in app/main.py.

These are defense-in-depth fallbacks (every route already catches and maps
its own domain errors - see CLAUDE.md's "Domain Errors -> HTTP Status
Codes" table), so they're only ever reached if a route forgets to. Tested
by calling the handler functions directly with a fabricated Request,
rather than through TestClient - Starlette's test client re-raises
unhandled exceptions by default for debuggability, which would fight
against testing "what does the client actually receive" here.
"""

import json

import pytest
from starlette.requests import Request

from app.domain.errors import InvalidTransition, JDParseError, NotFound
from app.main import domain_error_handler, unhandled_exception_handler


def _fake_request(path: str = "/api/test") -> Request:
    return Request(scope={"type": "http", "method": "GET", "path": path, "headers": []})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc,expected_status",
    [
        (NotFound("missing"), 404),
        (InvalidTransition("bad transition"), 409),
        (JDParseError("llm failed"), 502),
    ],
)
async def test_domain_error_handler_maps_known_types(exc, expected_status):
    response = await domain_error_handler(_fake_request(), exc)
    assert response.status_code == expected_status
    assert json.loads(response.body) == {"detail": str(exc)}


@pytest.mark.asyncio
async def test_domain_error_handler_defaults_unknown_domain_error_to_500():
    from app.domain.errors import DomainError

    class SomeFutureDomainError(DomainError):
        pass

    response = await domain_error_handler(
        _fake_request(), SomeFutureDomainError("oops")
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_unhandled_exception_handler_returns_generic_500_without_leaking_details():
    response = await unhandled_exception_handler(
        _fake_request(), ValueError("some internal detail that shouldn't leak")
    )
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body == {"detail": "Internal server error"}
    assert "internal detail" not in response.body.decode()
