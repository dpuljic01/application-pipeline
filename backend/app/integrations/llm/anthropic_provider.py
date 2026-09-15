from __future__ import annotations

import time

import anthropic

from app.integrations.llm.base import LLMProviderError, LLMResponse, LLMTimeoutError
from app.integrations.llm.pricing import calculate_cost

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
PROVIDER_NAME = "anthropic"


class AnthropicProvider:
    def __init__(
        self, *, api_key: str, timeout_seconds: float = 30.0, max_retries: int = 2
    ):
        self._client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        resolved_model = model or DEFAULT_MODEL
        started = time.monotonic()

        try:
            response = self._client.messages.create(
                model=resolved_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError("Anthropic request timed out") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMProviderError(f"Anthropic connection error: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        content = "".join(
            block.text for block in response.content if block.type == "text"
        )
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens

        return LLMResponse(
            content=content,
            provider=PROVIDER_NAME,
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=calculate_cost(
                provider=PROVIDER_NAME,
                model=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
        )
