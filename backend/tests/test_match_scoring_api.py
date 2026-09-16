import json
import uuid
from decimal import Decimal

from app.api.deps import get_llm_provider
from app.integrations.llm.base import LLMProviderError, LLMResponse


class FakeLLMProvider:
    """Test double for LLMProvider - returns canned content keyed off which
    response_schema is requested, so the same fake can answer both
    parse-jd and score calls in one test."""

    def __init__(self, *, responses: dict[str, str], raise_error: bool = False):
        self.responses = responses
        self.raise_error = raise_error

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        model=None,
        temperature=0.0,
        max_tokens=1024,
        response_schema=None,
    ) -> LLMResponse:
        if self.raise_error:
            raise LLMProviderError("simulated provider failure")

        content = self.responses.get(
            response_schema.__name__ if response_schema else "", ""
        )
        return LLMResponse(
            content=content,
            provider="fake",
            model="fake-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost_usd=Decimal("0"),
            latency_ms=1,
        )


PARSED_JD_JSON = json.dumps(
    {
        "required_skills": ["Python", "FastAPI"],
        "nice_to_have_skills": ["Docker"],
        "seniority_claimed": "Senior",
        "seniority_assessed": "senior",
        "tech_stack": ["Python", "FastAPI"],
        "languages": ["English"],
        "years_experience_min": 5,
        "remote_policy": "hybrid",
        "salary_range": "CHF 95'000 - 125'000",
        "salary_confidence": "stated",
        "key_responsibilities": ["Build things"],
        "red_flags": [],
        "missing_info": [],
        "summary": "A role.",
    }
)

MATCH_INSIGHTS_JSON = json.dumps(
    {
        "fit_narrative": "Solid fit overall.",
        "key_strengths": ["Python", "FastAPI"],
        "gaps": [],
        "talking_points": ["Backend experience with FastAPI"],
    }
)


def _create_application(client, **overrides):
    payload = {
        "company": "Hamilton AG",
        "role_title": "Software Engineer",
        "job_url": "https://jobs.hamilton.ch/JR-5687",
    }
    payload.update(overrides)
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _override_llm(client, provider):
    client.app.dependency_overrides[get_llm_provider] = lambda: provider


def test_score_application_returns_404_for_unknown_application(client):
    response = client.post(f"/api/applications/{uuid.uuid4()}/score")
    assert response.status_code == 404


def test_score_application_without_parsed_jd_returns_409(client):
    application = _create_application(client)

    response = client.post(f"/api/applications/{application['id']}/score")
    assert response.status_code == 409


def test_score_application_happy_path_sets_match_score_and_details(client):
    application = _create_application(client)
    _override_llm(
        client,
        FakeLLMProvider(
            responses={
                "ParsedJobDescription": PARSED_JD_JSON,
                "MatchInsights": MATCH_INSIGHTS_JSON,
            }
        ),
    )

    parse_response = client.post(
        f"/api/applications/{application['id']}/parse-jd",
        json={"jd_text": "We need a Python engineer with FastAPI experience."},
    )
    assert parse_response.status_code == 200, parse_response.text

    score_response = client.post(f"/api/applications/{application['id']}/score")
    assert score_response.status_code == 200, score_response.text
    body = score_response.json()

    assert body["match_score"] is not None
    assert 0 <= body["match_score"] <= 100
    components = body["match_details"]["components"]
    assert set(components.keys()) == {
        "skills",
        "seniority",
        "language",
        "salary",
        "remote_policy",
    }
    assert body["match_details"]["insights"]["fit_narrative"] == "Solid fit overall."


def test_score_application_llm_failure_returns_502(client):
    application = _create_application(client)
    _override_llm(
        client,
        FakeLLMProvider(responses={"ParsedJobDescription": PARSED_JD_JSON}),
    )
    parse_response = client.post(
        f"/api/applications/{application['id']}/parse-jd",
        json={"jd_text": "We need a Python engineer with FastAPI experience."},
    )
    assert parse_response.status_code == 200, parse_response.text

    _override_llm(client, FakeLLMProvider(responses={}, raise_error=True))
    response = client.post(f"/api/applications/{application['id']}/score")
    assert response.status_code == 502
