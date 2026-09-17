"""Pure tests for the LLM provider abstraction: no network calls, no DB."""

from decimal import Decimal

import pytest

from google.genai import errors as genai_errors

from app.integrations.llm.anthropic_provider import AnthropicProvider
from app.integrations.llm.base import DisabledLLMProvider, LLMProviderError
from app.integrations.llm.cerebras_provider import CerebrasProvider
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.gemini_provider import (
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    GeminiProvider,
)
from app.integrations.llm.pricing import calculate_cost


class _FakeUsage:
    def __init__(self):
        self.prompt_token_count = 10
        self.candidates_token_count = 5
        self.total_token_count = 15


class _FakeResponse:
    def __init__(self, text: str = "ok"):
        self.text = text
        self.usage_metadata = _FakeUsage()


def _rate_limit_error() -> genai_errors.APIError:
    return genai_errors.APIError(
        429, {"error": {"message": "quota exceeded", "status": "RESOURCE_EXHAUSTED"}}
    )


def test_disabled_provider_returns_placeholder_with_zero_cost():
    provider = DisabledLLMProvider()

    response = provider.complete(system_prompt="sys", user_prompt="hi")

    assert response.content == ""
    assert response.provider == "disabled"
    assert response.cost_usd == Decimal("0")
    assert response.total_tokens == 0


def test_calculate_cost_known_model():
    cost = calculate_cost(
        provider="gemini",
        model="gemini-3.6-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == Decimal("0.75") + Decimal("3.75")


def test_calculate_cost_unknown_model_is_zero():
    cost = calculate_cost(
        provider="gemini",
        model="some-future-model",
        prompt_tokens=1000,
        completion_tokens=1000,
    )

    assert cost == Decimal("0")


def test_factory_returns_disabled_provider_when_llm_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", False)

    assert isinstance(get_llm_provider(), DisabledLLMProvider)


def test_factory_returns_gemini_provider_when_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    assert isinstance(get_llm_provider(), GeminiProvider)


def test_factory_returns_anthropic_provider_when_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")

    assert isinstance(get_llm_provider(), AnthropicProvider)


def test_factory_returns_cerebras_provider_when_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "cerebras")
    monkeypatch.setattr(settings, "CEREBRAS_API_KEY", "test-key")

    assert isinstance(get_llm_provider(), CerebrasProvider)


def test_calculate_cost_cerebras_known_model():
    cost = calculate_cost(
        provider="cerebras",
        model="gpt-oss-120b",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == Decimal("0.35") + Decimal("0.75")


def test_factory_raises_when_api_key_missing(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)

    with pytest.raises(LLMProviderError):
        get_llm_provider()


def test_factory_raises_on_unknown_provider(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "not-a-real-provider")

    with pytest.raises(LLMProviderError):
        get_llm_provider()


def test_gemini_falls_back_to_flash_lite_on_rate_limit(monkeypatch):
    provider = GeminiProvider(api_key="test-key")
    calls: list[str] = []

    def fake_generate_content(*, model, contents, config):
        calls.append(model)
        if model == DEFAULT_MODEL:
            raise _rate_limit_error()
        return _FakeResponse()

    monkeypatch.setattr(
        provider._client.models, "generate_content", fake_generate_content
    )

    response = provider.complete(system_prompt="sys", user_prompt="hi")

    assert calls == [DEFAULT_MODEL, FALLBACK_MODEL]
    assert response.model == FALLBACK_MODEL
    assert response.content == "ok"


def test_gemini_does_not_fall_back_for_non_rate_limit_error(monkeypatch):
    provider = GeminiProvider(api_key="test-key")

    def fake_generate_content(*, model, contents, config):
        raise genai_errors.APIError(
            500, {"error": {"message": "server error", "status": "INTERNAL"}}
        )

    monkeypatch.setattr(
        provider._client.models, "generate_content", fake_generate_content
    )

    with pytest.raises(LLMProviderError):
        provider.complete(system_prompt="sys", user_prompt="hi")


def test_gemini_does_not_fall_back_for_explicit_model(monkeypatch):
    provider = GeminiProvider(api_key="test-key")
    calls: list[str] = []

    def fake_generate_content(*, model, contents, config):
        calls.append(model)
        raise _rate_limit_error()

    monkeypatch.setattr(
        provider._client.models, "generate_content", fake_generate_content
    )

    explicit_model = DEFAULT_MODEL + "-explicit"
    with pytest.raises(LLMProviderError):
        provider.complete(system_prompt="sys", user_prompt="hi", model=explicit_model)

    assert calls == [explicit_model]


def test_calculate_cost_gemini_flash_lite_known_model():
    cost = calculate_cost(
        provider="gemini",
        model=FALLBACK_MODEL,
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    assert cost == Decimal("0.25") + Decimal("1.50")
