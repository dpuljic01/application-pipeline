"""Day 12 pipeline: creating an application with jd_text parses + scores it
in a background task. TestClient runs background tasks before post()
returns, so the follow-up GET sees the final state."""

import uuid

from app.api.deps import get_pipeline_runner
from app.core.config import settings
from app.services.pipeline import process_new_application
from tests.test_match_scoring_api import (
    MATCH_INSIGHTS_JSON,
    PARSED_JD_JSON,
    FakeLLMProvider,
)


def _use_pipeline(client, db_session, llm) -> list[dict]:
    """Route the pipeline through the test session + a fake LLM; returns a
    list that records every run's kwargs."""
    runs: list[dict] = []

    def runner(**kwargs):
        runs.append(kwargs)
        process_new_application(db=db_session, llm=llm, **kwargs)

    client.app.dependency_overrides[get_pipeline_runner] = lambda: runner
    return runs


def _create(client, **extra) -> dict:
    response = client.post(
        "/api/applications",
        json={"company": "Northgate AG", "role_title": "Backend Engineer", **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _get(client, application_id: str) -> dict:
    response = client.get(f"/api/applications/{application_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _jd() -> str:
    # Unique per test so llm_cache never serves one test's parse to another.
    return f"Northgate AG seeks a Python/FastAPI engineer. Ref {uuid.uuid4()}"


def test_without_jd_text_no_pipeline_runs(client, db_session):
    runs = _use_pipeline(client, db_session, FakeLLMProvider(responses={}))

    created = _create(client)

    assert runs == []
    assert created["pipeline_status"] is None


def test_blank_jd_text_is_treated_as_absent(client, db_session):
    runs = _use_pipeline(client, db_session, FakeLLMProvider(responses={}))

    created = _create(client, jd_text="   \n ")

    assert runs == []
    assert created["pipeline_status"] is None


def test_jd_text_parses_and_scores_in_background(client, db_session):
    llm = FakeLLMProvider(
        responses={
            "ParsedJobDescription": PARSED_JD_JSON,
            "MatchInsights": MATCH_INSIGHTS_JSON,
        }
    )
    runs = _use_pipeline(client, db_session, llm)

    created = _create(client, jd_text=_jd())

    # The response is serialized before the background task runs.
    assert created["pipeline_status"] == "PENDING"
    assert len(runs) == 1
    final = _get(client, created["id"])
    assert final["pipeline_status"] == "COMPLETED"
    assert final["pipeline_error"] is None
    assert final["parsed_jd"]["required_skills"] == ["Python", "FastAPI"]
    assert final["match_score"] is not None
    assert final["match_details"]["insights"]["fit_narrative"] == "Solid fit overall."


def test_scoring_failure_keeps_the_parsed_jd(client, db_session):
    # No MatchInsights response -> the fake returns "" -> invalid output.
    llm = FakeLLMProvider(responses={"ParsedJobDescription": PARSED_JD_JSON})
    _use_pipeline(client, db_session, llm)

    created = _create(client, jd_text=_jd())

    final = _get(client, created["id"])
    assert final["pipeline_status"] == "FAILED"
    assert final["pipeline_error"].startswith("Scoring failed")
    assert final["parsed_jd"] is not None
    assert final["match_score"] is None


def test_parse_failure_stops_before_scoring(client, db_session):
    _use_pipeline(client, db_session, FakeLLMProvider(responses={}, raise_error=True))

    created = _create(client, jd_text=_jd())

    final = _get(client, created["id"])
    assert final["pipeline_status"] == "FAILED"
    assert final["pipeline_error"].startswith("Parsing failed")
    assert final["parsed_jd"] is None


def test_budget_exhausted_fails_the_pipeline_cleanly(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "LLM_DAILY_BUDGET_USD", 0.0)
    llm = FakeLLMProvider(
        responses={
            "ParsedJobDescription": PARSED_JD_JSON,
            "MatchInsights": MATCH_INSIGHTS_JSON,
        }
    )
    _use_pipeline(client, db_session, llm)

    created = _create(client, jd_text=_jd())

    final = _get(client, created["id"])
    assert final["pipeline_status"] == "FAILED"
    assert "budget" in final["pipeline_error"].lower()
