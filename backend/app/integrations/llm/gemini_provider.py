from __future__ import annotations

import time
from pydantic import BaseModel

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.integrations.llm.base import LLMProviderError, LLMResponse
from app.integrations.llm.pricing import calculate_cost

DEFAULT_MODEL = "gemini-3.6-flash"
# Free tier is ~20 requests/day on 3.6 Flash vs. ~500 on 3.1 Flash-Lite (same
# API key, no separate provider needed) - used only when the primary model
# is rate-limited, never for an explicitly-requested model.
FALLBACK_MODEL = "gemini-3.1-flash-lite"
PROVIDER_NAME = "gemini"


class GeminiProvider:
    def __init__(
        self, *, api_key: str, timeout_seconds: float = 30.0, max_attempts: int = 3
    ):
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=max_attempts,
                    initial_delay=1.0,
                    max_delay=10.0,
                    exp_base=2.0,
                ),
            ),
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
        resolved_model = model or DEFAULT_MODEL
        started = time.monotonic()

        config_kwargs: dict = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = types.GenerateContentConfig(**config_kwargs)

        # Only fall back when the caller let us pick the model (resolved_model
        # is still DEFAULT_MODEL) - an explicitly-requested model is never
        # silently swapped for a different one.
        candidates = [resolved_model]
        if resolved_model == DEFAULT_MODEL:
            candidates.append(FALLBACK_MODEL)

        response = None
        for candidate_model in candidates:
            is_last_candidate = candidate_model == candidates[-1]
            try:
                response = self._client.models.generate_content(
                    model=candidate_model, contents=user_prompt, config=config
                )
                resolved_model = candidate_model
                break
            except genai_errors.APIError as exc:
                if exc.code == 429 and not is_last_candidate:
                    continue
                raise LLMProviderError(
                    f"Gemini API error ({exc.code}): {exc.message}"
                ) from exc
            except Exception as exc:
                raise LLMProviderError(f"Gemini request failed: {exc}") from exc
        assert response is not None

        latency_ms = int((time.monotonic() - started) * 1000)
        usage = response.usage_metadata
        prompt_tokens = (usage.prompt_token_count if usage else None) or 0
        completion_tokens = (usage.candidates_token_count if usage else None) or 0
        total_tokens = (usage.total_token_count if usage else None) or (
            prompt_tokens + completion_tokens
        )

        return LLMResponse(
            content=response.text or "",
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
