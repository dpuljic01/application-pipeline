"""Tests for the job search provider abstraction.

Adzuna's parsing logic is exercised against a mocked transport (real JSON
shape, no real network call) — unlike the LLM providers' tests, this one is
worth covering at the response-mapping level: a field-shape drift here
(Adzuna renames/nests something) fails silently as "0 leads found" rather
than a crash, which is much easier to miss.
"""

from decimal import Decimal

import httpx
import pytest

from app.integrations.job_search.adzuna_provider import AdzunaProvider
from app.integrations.job_search.base import (
    JobSearchProviderError,
    JobSearchTimeoutError,
)
from app.integrations.job_search.factory import get_enabled_job_search_providers

SAMPLE_RESPONSE = {
    "results": [
        {
            "id": "123456",
            "title": "Senior Backend Python Engineer",
            "company": {"display_name": "Example AG"},
            "location": {"display_name": "Zürich, Switzerland"},
            "redirect_url": "https://www.adzuna.ch/land/ad/123456",
            "description": "We are looking for a Python/FastAPI engineer...",
            "created": "2026-09-10T08:00:00Z",
            "salary_min": 95000,
            "salary_max": 120000,
        },
        {
            # Missing company/location/salary — must not crash, must fall
            # back gracefully.
            "id": "789",
            "title": "DevOps Engineer",
            "redirect_url": "https://www.adzuna.ch/land/ad/789",
            "description": "AWS, Docker, CI/CD.",
            "created": None,
        },
    ]
}


def _provider_with_transport(handler) -> AdzunaProvider:
    transport = httpx.MockTransport(handler)
    return AdzunaProvider(app_id="test-id", app_key="test-key", transport=transport)


@pytest.mark.asyncio
async def test_search_parses_full_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["app_id"] == "test-id"
        assert request.url.params["what"] == "python backend"
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    provider = _provider_with_transport(handler)
    results = await provider.search(query="python backend")

    assert len(results) == 2
    first = results[0]
    assert first.source == "adzuna"
    assert first.external_id == "123456"
    assert first.title == "Senior Backend Python Engineer"
    assert first.company_name == "Example AG"
    assert first.location == "Zürich, Switzerland"
    assert first.url == "https://www.adzuna.ch/land/ad/123456"
    assert first.salary_min == Decimal("95000")
    assert first.posted_at is not None


@pytest.mark.asyncio
async def test_search_handles_missing_optional_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    provider = _provider_with_transport(handler)
    results = await provider.search(query="devops")

    second = results[1]
    assert second.company_name == "Unknown"
    assert second.location == "Unknown"
    assert second.salary_min is None
    assert second.posted_at is None


@pytest.mark.asyncio
async def test_search_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid app_id/app_key")

    provider = _provider_with_transport(handler)

    with pytest.raises(JobSearchProviderError):
        await provider.search(query="python")


@pytest.mark.asyncio
async def test_search_raises_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    provider = _provider_with_transport(handler)

    with pytest.raises(JobSearchTimeoutError):
        await provider.search(query="python")


def test_factory_returns_empty_when_unconfigured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ADZUNA_APP_ID", None)
    monkeypatch.setattr(settings, "ADZUNA_APP_KEY", None)

    assert get_enabled_job_search_providers() == []


def test_factory_returns_adzuna_when_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "id")
    monkeypatch.setattr(settings, "ADZUNA_APP_KEY", "key")

    providers = get_enabled_job_search_providers()

    assert len(providers) == 1
    assert isinstance(providers[0], AdzunaProvider)
