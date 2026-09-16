from __future__ import annotations

from decimal import Decimal

# USD per 1M tokens (input, output). Verified against provider pricing pages
# 2026-09-01 (gemini/anthropic) and 2026-09-11 (cerebras). Update when a new
# default model is picked in config.py.
PRICING: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    # TODO: promotional rate expires 2027-01-01, then $1.50 / $7.50.
    ("gemini", "gemini-3.6-flash"): (Decimal("0.75"), Decimal("3.75")),
    ("anthropic", "claude-haiku-4-5-20251001"): (Decimal("1.00"), Decimal("5.00")),
    # Free while under the account's free-tier daily/rate quota — cost_tracker
    # still records this rate so a call that spills over into paid usage
    # (quota exceeded, or a non-free Cerebras account) is logged accurately.
    ("cerebras", "gpt-oss-120b"): (Decimal("0.35"), Decimal("0.75")),
}

# Anthropic prompt-caching multipliers on the base input price, 5-minute TTL
# (the default we use — see anthropic_provider.py). Writing to the cache
# costs *more* than a normal input token; reading from it costs far less.
# Not verifiable by calling the SDK like the request/response shapes were —
# check console.anthropic.com/docs if these ever look off.
CACHE_WRITE_MULTIPLIER = Decimal("1.25")
CACHE_READ_MULTIPLIER = Decimal("0.10")


def calculate_cost(
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> Decimal:
    input_price, output_price = PRICING.get(
        (provider, model), (Decimal("0"), Decimal("0"))
    )
    cost = (
        Decimal(prompt_tokens) * input_price
        + Decimal(completion_tokens) * output_price
        + Decimal(cache_write_tokens) * input_price * CACHE_WRITE_MULTIPLIER
        + Decimal(cache_read_tokens) * input_price * CACHE_READ_MULTIPLIER
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"))
