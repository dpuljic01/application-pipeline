"""JD parser retry + llm_cache behaviour. Service-level with a real DB
session (the cache is a real table), but no HTTP layer."""

import json
from decimal import Decimal

import pytest

from app.db.repositories.llm_cache_repo import LLMCacheRepository
from app.domain.errors import JDParseError
from app.integrations.llm.base import LLMResponse
from app.services.jd_parser import (
    jd_cache_key,
    parse_job_description,
    parse_job_description_cached,
)

VALID = {
    "required_skills": ["Python"],
    "nice_to_have_skills": [],
    "seniority_claimed": None,
    "seniority_assessed": "mid",
    "tech_stack": ["FastAPI"],
    "languages": ["English"],
    "years_experience_min": 3,
    "remote_policy": None,
    "salary_range": None,
    "salary_confidence": "unknown",
    "key_responsibilities": [],
    "red_flags": [],
    "missing_info": [],
    "summary": "Backend role at Northgate AG.",
}
NO_SKILLS = {**VALID, "required_skills": [], "tech_stack": []}
JD = "Northgate AG is hiring a backend engineer (Python, FastAPI)."


class ScriptedProvider:
    """Returns the scripted contents in order, recording each user prompt."""

    def __init__(self, *contents: str, name: str = "gemini"):
        self.contents = list(contents)
        self.name = name
        self.prompts: list[str] = []

    def complete(self, *, user_prompt, **kwargs) -> LLMResponse:
        self.prompts.append(user_prompt)
        return LLMResponse(
            content=self.contents.pop(0),
            provider=self.name,
            model="test",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost_usd=Decimal("0"),
            latency_ms=1,
        )


def test_valid_output_needs_one_call():
    llm = ScriptedProvider(json.dumps(VALID))
    assert parse_job_description(llm, jd_text=JD).required_skills == ["Python"]
    assert len(llm.prompts) == 1


@pytest.mark.parametrize("first", ["not json", json.dumps(NO_SKILLS)])
def test_invalid_output_is_retried_once_with_the_reason(first):
    llm = ScriptedProvider(first, json.dumps(VALID))

    parsed = parse_job_description(llm, jd_text=JD)

    assert parsed.tech_stack == ["FastAPI"]
    assert len(llm.prompts) == 2
    assert "previous answer was rejected" in llm.prompts[1]
    assert llm.prompts[1].startswith(JD)


def test_two_invalid_outputs_raise():
    llm = ScriptedProvider("not json", json.dumps(NO_SKILLS))
    with pytest.raises(JDParseError, match="twice"):
        parse_job_description(llm, jd_text=JD)


def test_second_parse_of_same_posting_is_served_from_cache(db_session):
    cache = LLMCacheRepository(db_session)
    first = ScriptedProvider(json.dumps(VALID))
    parse_job_description_cached(first, cache=cache, jd_text=JD)

    second = ScriptedProvider()  # would IndexError if called
    # Different wrapping/whitespace, same posting.
    rewrapped = "  " + JD.replace(" ", "\n", 2) + "\n\n"
    parsed = parse_job_description_cached(second, cache=cache, jd_text=rewrapped)

    assert parsed.required_skills == ["Python"]
    assert second.prompts == []


def test_cache_is_per_provider(db_session):
    cache = LLMCacheRepository(db_session)
    parse_job_description_cached(
        ScriptedProvider(json.dumps(VALID)), cache=cache, jd_text=JD
    )

    anthropic = ScriptedProvider(json.dumps(VALID), name="anthropic")
    parse_job_description_cached(anthropic, cache=cache, jd_text=JD)

    assert len(anthropic.prompts) == 1


def test_failed_parse_is_not_cached(db_session):
    cache = LLMCacheRepository(db_session)
    with pytest.raises(JDParseError):
        parse_job_description_cached(
            ScriptedProvider("bad", "bad"), cache=cache, jd_text=JD
        )

    assert cache.get(cache_key=jd_cache_key(provider="gemini", jd_text=JD)) is None
