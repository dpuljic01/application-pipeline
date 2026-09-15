from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class RawJobResult(BaseModel):
    """One posting as returned by a source, before JD parsing/scoring.

    Deliberately close to raw: `description` is whatever text the source
    gave us (may be HTML, may be a search snippet) — Day 9's JD parser is
    what turns this into structured data, not this layer.
    """

    model_config = ConfigDict(frozen=True)

    source: str
    external_id: str
    title: str
    company_name: str
    location: str
    url: str
    description: str
    posted_at: datetime | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None


class JobSearchProvider(Protocol):
    async def search(
        self,
        *,
        query: str,
        location: str | None = None,
        results_limit: int = 50,
    ) -> list[RawJobResult]: ...


class JobSearchProviderError(Exception):
    pass


class JobSearchTimeoutError(JobSearchProviderError):
    pass
