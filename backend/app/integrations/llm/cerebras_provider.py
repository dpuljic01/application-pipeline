from __future__ import annotations

import time

import cerebras.cloud.sdk as cerebras

from app.integrations.llm.base import LLMProviderError, LLMResponse, LLMTimeoutError
from app.integrations.llm.pricing import calculate_cost

DEFAULT_MODEL = "gpt-oss-120b"
PROVIDER_NAME = "cerebras"


class CerebrasProvider:
    def __init__(
        self, *, api_key: str, timeout_seconds: float = 30.0, max_retries: int = 2
    ):
        self._client = cerebras.Cerebras(
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
            response = self._client.chat.completions.create(
                model=resolved_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except cerebras.APITimeoutError as exc:
            raise LLMTimeoutError("Cerebras request timed out") from exc
        except cerebras.APIConnectionError as exc:
            raise LLMProviderError(f"Cerebras connection error: {exc}") from exc
        except cerebras.APIStatusError as exc:
            raise LLMProviderError(
                f"Cerebras API error ({exc.status_code}): {exc.message}"
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        content = response.choices[0].message.content or ""
        usage = response.usage
        prompt_tokens = (usage.prompt_tokens if usage else None) or 0
        completion_tokens = (usage.completion_tokens if usage else None) or 0
        total_tokens = (usage.total_tokens if usage else None) or (
            prompt_tokens + completion_tokens
        )

        return LLMResponse(
            content=content,
            provider=PROVIDER_NAME,
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=calculate_cost(
                provider=PROVIDER_NAME,
                model=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
        )
