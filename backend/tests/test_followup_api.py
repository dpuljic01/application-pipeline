import json
import uuid
from decimal import Decimal

from app.api.deps import get_llm_provider
from app.integrations.llm.base import LLMProviderError, LLMResponse


class FakeLLMProvider:
    def __init__(self, *, content: str = "", raise_error: bool = False):
        self.content = content
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

        return LLMResponse(
            content=self.content,
            provider="fake",
            model="fake-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost_usd=Decimal("0"),
            latency_ms=1,
        )


FOLLOWUP_EMAIL_JSON = json.dumps(
    {
        "subject": "Following up: Software Engineer application",
        "body": "Hi, I wanted to check on the status of my application for the Software Engineer role. Happy to answer any questions. Thanks.",
    }
)


def _create_application(client, **overrides):
    payload = {
        "company": "Northgate AG",
        "role_title": "Software Engineer",
        "job_url": "https://jobs.example.com/JR-5687",
    }
    payload.update(overrides)
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _override_llm(client, provider):
    client.app.dependency_overrides[get_llm_provider] = lambda: provider


def test_generate_followup_returns_404_for_unknown_application(client):
    response = client.post(
        f"/api/applications/{uuid.uuid4()}/generate-followup", json={}
    )
    assert response.status_code == 404


def test_generate_followup_happy_path_persists_on_application(client):
    application = _create_application(client)
    _override_llm(client, FakeLLMProvider(content=FOLLOWUP_EMAIL_JSON))

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup",
        json={"context": "Mention I'm still very interested."},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["generated_followup"]["subject"] == (
        "Following up: Software Engineer application"
    )
    assert "Software Engineer" in body["generated_followup"]["body"]

    # Persisted - a plain GET reflects it too.
    fetched = client.get(f"/api/applications/{application['id']}").json()
    assert (
        fetched["generated_followup"]["subject"]
        == body["generated_followup"]["subject"]
    )


def test_generate_followup_llm_failure_returns_502(client):
    application = _create_application(client)
    _override_llm(client, FakeLLMProvider(raise_error=True))

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )
    assert response.status_code == 502
