from __future__ import annotations

from app.core.config import settings
from app.integrations.job_search.adzuna_provider import AdzunaProvider
from app.integrations.job_search.base import JobSearchProvider


def get_enabled_job_search_providers() -> list[JobSearchProvider]:
    """Returns every provider that has credentials configured.

    Unlike `get_llm_provider()`, this deliberately does not pick one — the
    discovery step runs all enabled providers concurrently (asyncio.gather)
    and merges their results. Add a source by adding it here, not by
    switching a config value.
    """
    providers: list[JobSearchProvider] = []

    if settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY:
        providers.append(
            AdzunaProvider(
                app_id=settings.ADZUNA_APP_ID,
                app_key=settings.ADZUNA_APP_KEY,
                country=settings.ADZUNA_COUNTRY,
            )
        )

    # Next: RssFeedProvider (swissdevjobs.ch), ClaudeWebSearchProvider
    # (jobs.ch/jobup.ch fallback) — same append-only pattern.

    return providers
