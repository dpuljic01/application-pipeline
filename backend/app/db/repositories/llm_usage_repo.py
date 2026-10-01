from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.llm_usage import LLMUsage
from app.domain.enums import LLMProviderName


class LLMUsageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        provider: LLMProviderName,
        model: str,
        operation: str,
        user_id: UUID | None = None,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd: Decimal,
        latency_ms: int,
        success: bool,
        error_message: str | None = None,
    ) -> LLMUsage:
        usage = LLMUsage(
            provider=provider,
            model=model,
            operation=operation,
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
        self.db.add(usage)
        return usage

    def total_cost_since(
        self, *, since: datetime, user_id: UUID | None = None
    ) -> Decimal:
        """All spend since `since`, or only one user's when user_id is given."""
        stmt = select(func.coalesce(func.sum(LLMUsage.cost_usd), 0)).where(
            LLMUsage.created_at >= since
        )
        if user_id is not None:
            stmt = stmt.where(LLMUsage.user_id == user_id)
        return Decimal(self.db.scalar(stmt))
