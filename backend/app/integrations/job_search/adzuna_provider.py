from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.integrations.job_search.base import (
    JobSearchProviderError,
    JobSearchTimeoutError,
    RawJobResult,
)

BASE_URL = "https://api.adzuna.com/v1/api/jobs"
PROVIDER_NAME = "adzuna"
# Adzuna caps results_per_page server-side regardless of what's requested.
MAX_RESULTS_PER_PAGE = 50


class AdzunaProvider:
    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        country: str = "ch",
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._app_id = app_id
        self._app_key = app_key
        self._country = country
        self._timeout = timeout_seconds
        # Injectable only for tests (httpx.MockTransport) — real calls leave
        # this None and get httpx's normal transport.
        self._transport = transport

    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        results_limit: int = 50,
    ) -> list[RawJobResult]:
        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": min(results_limit, MAX_RESULTS_PER_PAGE),
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        url = f"{BASE_URL}/{self._country}/search/1"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise JobSearchTimeoutError("Adzuna request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise JobSearchProviderError(
                f"Adzuna API error ({exc.response.status_code}): "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise JobSearchProviderError(f"Adzuna request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise JobSearchProviderError(
                f"Adzuna returned non-JSON response: {exc}"
            ) from exc

        return [_to_raw_result(item) for item in payload.get("results", [])]


def _to_raw_result(item: dict) -> RawJobResult:
    location_obj = item.get("location") or {}
    company_obj = item.get("company") or {}

    return RawJobResult(
        source=PROVIDER_NAME,
        external_id=str(item.get("id") or item.get("redirect_url") or ""),
        title=(item.get("title") or "").strip(),
        company_name=company_obj.get("display_name") or "Unknown",
        location=location_obj.get("display_name") or "Unknown",
        url=item.get("redirect_url") or "",
        description=item.get("description") or "",
        posted_at=_parse_created(item.get("created")),
        salary_min=_to_decimal(item.get("salary_min")),
        salary_max=_to_decimal(item.get("salary_max")),
    )


def _parse_created(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_decimal(value: float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None
