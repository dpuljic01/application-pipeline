from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.repositories.llm_usage_repo import LLMUsageRepository
from app.domain.enums import LLMProviderName
from app.integrations.llm.base import LLMResponse


class CostTracker:
    """Logs every LLM call to `llm_usage`, success or failure.

    Commits on its own rather than leaving that to the caller's service
    transaction: a usage record is an independent audit fact about a call
    that already happened, not part of the caller's business transaction,
    so it must survive even if the caller rolls back afterwards.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = LLMUsageRepository(db)

    def record_success(self, *, response: LLMResponse, operation: str) -> None:
        if response.provider == "disabled":
            return

        self.repository.create(
            provider=LLMProviderName(response.provider),
            model=response.model,
            operation=operation,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            success=True,
        )
        self.db.commit()

    def record_failure(
        self,
        *,
        provider: LLMProviderName,
        model: str,
        operation: str,
        latency_ms: int,
        error_message: str,
    ) -> None:
        self.repository.create(
            provider=provider,
            model=model,
            operation=operation,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=Decimal("0"),
            latency_ms=latency_ms,
            success=False,
            error_message=error_message,
        )
        self.db.commit()
