from __future__ import annotations

import json
import time

import anthropic
from pydantic import BaseModel

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
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        resolved_model = model or DEFAULT_MODEL
        started = time.monotonic()
        # `temperature` is intentionally not forwarded: verified live against
        # the installed SDK (1.2.0) that `messages.create` no longer accepts
        # it at all — real API drift, not an oversight. Still accepted as a
        # method param so this provider's signature matches the Protocol.
        config_kwargs: dict = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            # Cache breakpoint on the system prompt: it's the fixed part,
            # reused verbatim on every call for a given feature (e.g. every
            # JD parse), while `user_prompt` is what actually varies. Repeat
            # calls within the TTL only pay the cheap cache-read rate for
            # this part instead of full input price — see pricing.py.
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if response_schema is not None:
            config_kwargs["tools"] = [
                {
                    "name": "record_result",
                    "description": "Record the structured extraction result.",
                    "input_schema": response_schema.model_json_schema(),
                }
            ]
            config_kwargs["tool_choice"] = {"type": "tool", "name": "record_result"}

        try:
            response = self._client.messages.create(**config_kwargs)
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError("Anthropic request timed out") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMProviderError(f"Anthropic connection error: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMProviderError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if response_schema is not None:
            # Forced tool-use: the answer is a tool_use block's already-parsed
            # `.input` dict, not text. Re-serialize to a string so `content`
            # stays a plain str regardless of which provider answered.
            tool_use_block = next(
                (block for block in response.content if block.type == "tool_use"),
                None,
            )
            content = json.dumps(tool_use_block.input) if tool_use_block else ""
        else:
            content = "".join(
                block.text for block in response.content if block.type == "text"
            )

        usage = response.usage
        base_input_tokens = usage.input_tokens
        cache_write_tokens = usage.cache_creation_input_tokens or 0
        cache_read_tokens = usage.cache_read_input_tokens or 0
        completion_tokens = usage.output_tokens
        # Reported prompt_tokens covers all input-side tokens actually
        # processed (fresh + cache write + cache read) — cost weighting
        # differs per bucket, so calculate_cost gets them separately below.
        prompt_tokens = base_input_tokens + cache_write_tokens + cache_read_tokens

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
                prompt_tokens=base_input_tokens,
                completion_tokens=completion_tokens,
                cache_write_tokens=cache_write_tokens,
                cache_read_tokens=cache_read_tokens,
            ),
            latency_ms=latency_ms,
        )
