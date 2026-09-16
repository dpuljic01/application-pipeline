from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal
    latency_ms: int


class LLMProvider(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse: ...


class LLMProviderError(Exception):
    pass


class LLMTimeoutError(LLMProviderError):
    pass


class DisabledLLMProvider:
    """Returned by the factory when LLM_ENABLED=false. Never calls out to a
    real provider, so callers can run the same code path in environments
    with no API key configured."""

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
        return LLMResponse(
            content="",
            provider="disabled",
            model=model or "none",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=Decimal("0"),
            latency_ms=0,
        )
