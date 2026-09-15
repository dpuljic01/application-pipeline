from __future__ import annotations

from app.core.config import settings
from app.integrations.llm.anthropic_provider import AnthropicProvider
from app.integrations.llm.base import DisabledLLMProvider, LLMProvider, LLMProviderError
from app.integrations.llm.cerebras_provider import CerebrasProvider
from app.integrations.llm.gemini_provider import GeminiProvider


def get_llm_provider() -> LLMProvider:
    if not settings.LLM_ENABLED:
        return DisabledLLMProvider()

    if settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            raise LLMProviderError("GEMINI_API_KEY is not configured")
        return GeminiProvider(api_key=settings.GEMINI_API_KEY)

    if settings.LLM_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise LLMProviderError("ANTHROPIC_API_KEY is not configured")
        return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)

    if settings.LLM_PROVIDER == "cerebras":
        if not settings.CEREBRAS_API_KEY:
            raise LLMProviderError("CEREBRAS_API_KEY is not configured")
        return CerebrasProvider(api_key=settings.CEREBRAS_API_KEY)

    raise LLMProviderError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")
