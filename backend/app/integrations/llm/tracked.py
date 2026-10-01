from __future__ import annotations

import time
from datetime import datetime, time as dt_time, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.mixins import utcnow
from app.db.repositories.llm_usage_repo import LLMUsageRepository
from app.domain.enums import LLMProviderName
from app.domain.errors import LLMBudgetExceeded
from app.integrations.llm.base import LLMProvider, LLMProviderError, LLMResponse
from app.integrations.llm.cost_tracker import CostTracker


def _start_of_utc_day() -> datetime:
    return datetime.combine(utcnow().date(), dt_time.min, tzinfo=timezone.utc)


class TrackedLLMProvider:
    """Decorates any LLMProvider with a daily budget check and usage logging.

    Callers (services, parsers) keep calling `complete()` on a plain
    LLMProvider and never know this layer exists - same interface in, same
    interface out. One wrapper instance per operation, since `llm_usage`
    records which feature spent the money.

    Two budgets: the global daily one (all users together - protects the
    bill) and an optional per-user one, used for the shared demo account so
    anonymous visitors can't spend the global budget and lock real users out
    of AI features for the rest of the day.
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        db: Session,
        operation: str,
        daily_budget_usd: float | None,
        user_id: UUID | None = None,
        user_daily_budget_usd: float | None = None,
    ):
        self._inner = inner
        self._db = db
        self._operation = operation
        self._daily_budget_usd = daily_budget_usd
        self._user_id = user_id
        self._user_daily_budget_usd = user_daily_budget_usd
        self._tracker = CostTracker(db)
        self.name = inner.name

    def _check_budget(self) -> None:
        if self.name == "disabled":
            return
        usage = LLMUsageRepository(self._db)
        today = _start_of_utc_day()
        if self._daily_budget_usd is not None and usage.total_cost_since(
            since=today
        ) >= Decimal(str(self._daily_budget_usd)):
            raise LLMBudgetExceeded(
                "Daily AI budget reached - AI features resume tomorrow (UTC)"
            )
        if (
            self._user_daily_budget_usd is not None
            and self._user_id is not None
            and usage.total_cost_since(since=today, user_id=self._user_id)
            >= Decimal(str(self._user_daily_budget_usd))
        ):
            raise LLMBudgetExceeded(
                "The demo's AI budget for today is used up - sign up for your "
                "own free account to keep using the AI features"
            )

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        self._check_budget()

        started = time.monotonic()
        try:
            response = self._inner.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_schema=response_schema,
            )
        except LLMProviderError as exc:
            if self.name != "disabled":
                self._tracker.record_failure(
                    provider=LLMProviderName(self.name),
                    model=model or "default",
                    operation=self._operation,
                    user_id=self._user_id,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_message=str(exc)[:1000],
                )
            raise

        self._tracker.record_success(
            response=response, operation=self._operation, user_id=self._user_id
        )
        return response
