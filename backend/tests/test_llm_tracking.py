"""TrackedLLMProvider: usage logging and the daily budget, exercised through
a real LLM route (generate-followup) so the dependency wiring is covered."""

import json
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.api.deps import get_llm_provider
from app.core.config import settings
from app.db.models import User
from app.db.models.llm_usage import LLMUsage
from app.db.repositories.llm_usage_repo import LLMUsageRepository
from app.domain.enums import LLMProviderName
from app.integrations.llm.base import LLMProviderError, LLMResponse
from app.integrations.llm.tracked import _start_of_utc_day

FOLLOWUP_EMAIL_JSON = json.dumps(
    {"subject": "Following up", "body": "Hello, just checking in."}
)


class RecordingProvider:
    name = "gemini"

    def __init__(self, *, raise_error: bool = False):
        self.raise_error = raise_error
        self.calls = 0

    def complete(self, **kwargs) -> LLMResponse:
        self.calls += 1
        if self.raise_error:
            raise LLMProviderError("simulated provider failure")
        return LLMResponse(
            content=FOLLOWUP_EMAIL_JSON,
            provider="gemini",
            model="gemini-test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=Decimal("0.000123"),
            latency_ms=5,
        )


def _create_application(client) -> dict:
    response = client.post(
        "/api/applications",
        json={"company": "Northgate AG", "role_title": "Backend Engineer"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _usage_rows(db_session, operation: str) -> list[LLMUsage]:
    return list(
        db_session.scalars(
            select(LLMUsage).where(
                LLMUsage.operation == operation,
                LLMUsage.model == "gemini-test",
            )
        )
    )


def test_successful_call_is_logged_with_operation_and_cost(client, db_session):
    application = _create_application(client)
    client.app.dependency_overrides[get_llm_provider] = lambda: RecordingProvider()

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 200, response.text
    rows = _usage_rows(db_session, "generate_followup")
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].cost_usd == Decimal("0.000123")
    assert rows[0].total_tokens == 150


def test_failed_call_is_logged_and_still_maps_to_502(client, db_session):
    application = _create_application(client)
    client.app.dependency_overrides[get_llm_provider] = lambda: RecordingProvider(
        raise_error=True
    )

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 502
    failures = list(
        db_session.scalars(
            select(LLMUsage).where(
                LLMUsage.operation == "generate_followup",
                LLMUsage.success.is_(False),
                LLMUsage.error_message == "simulated provider failure",
            )
        )
    )
    assert len(failures) == 1
    assert failures[0].cost_usd == 0


def test_over_budget_returns_503_without_calling_the_provider(
    client, db_session, monkeypatch
):
    application = _create_application(client)
    # Relative to whatever is already logged today - the dev DB is shared.
    spent = LLMUsageRepository(db_session).total_cost_since(since=_start_of_utc_day())
    monkeypatch.setattr(settings, "LLM_DAILY_BUDGET_USD", float(spent) + 0.5)
    LLMUsageRepository(db_session).create(
        provider=LLMProviderName.GEMINI,
        model="gemini-test",
        operation="parse_jd",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=Decimal("0.5"),
        latency_ms=0,
        success=True,
    )
    db_session.flush()
    provider = RecordingProvider()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 503
    assert "budget" in response.json()["detail"].lower()
    assert provider.calls == 0


def test_under_budget_calls_go_through(client, db_session, monkeypatch):
    application = _create_application(client)
    spent = LLMUsageRepository(db_session).total_cost_since(since=_start_of_utc_day())
    monkeypatch.setattr(settings, "LLM_DAILY_BUDGET_USD", float(spent) + 1.0)
    provider = RecordingProvider()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 200, response.text
    assert provider.calls == 1


# --- per-user demo budget --------------------------------------------------


def _log_spend(db_session, *, user_id, cost: str) -> None:
    LLMUsageRepository(db_session).create(
        provider=LLMProviderName.GEMINI,
        model="gemini-test",
        operation="parse_jd",
        user_id=user_id,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=Decimal(cost),
        latency_ms=0,
        success=True,
    )
    db_session.flush()


def test_usage_rows_record_the_calling_user(client, db_session, test_user):
    application = _create_application(client)
    client.app.dependency_overrides[get_llm_provider] = lambda: RecordingProvider()

    client.post(f"/api/applications/{application['id']}/generate-followup", json={})

    rows = _usage_rows(db_session, "generate_followup")
    assert [r.user_id for r in rows] == [test_user.id]


def test_demo_account_has_its_own_cap(client, db_session, test_user, monkeypatch):
    # The test client's user *is* the demo account here.
    monkeypatch.setattr(settings, "DEMO_EMAIL", test_user.email.upper())
    monkeypatch.setattr(settings, "LLM_DEMO_DAILY_BUDGET_USD", 0.25)
    _log_spend(db_session, user_id=test_user.id, cost="0.25")
    application = _create_application(client)
    provider = RecordingProvider()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 503
    assert "sign up" in response.json()["detail"]
    assert provider.calls == 0


def test_demo_spend_does_not_count_against_other_users_cap(
    client, db_session, test_user, monkeypatch
):
    # Someone else is the demo account and has blown through its cap; the
    # global budget still has room, so this (non-demo) user is unaffected.
    demo = User(cognito_sub=uuid.uuid4(), email="demo@example.com")
    db_session.add(demo)
    db_session.flush()
    monkeypatch.setattr(settings, "DEMO_EMAIL", "demo@example.com")
    monkeypatch.setattr(settings, "LLM_DEMO_DAILY_BUDGET_USD", 0.25)
    spent = LLMUsageRepository(db_session).total_cost_since(since=_start_of_utc_day())
    monkeypatch.setattr(settings, "LLM_DAILY_BUDGET_USD", float(spent) + 1.0)
    _log_spend(db_session, user_id=demo.id, cost="0.50")
    application = _create_application(client)
    provider = RecordingProvider()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post(
        f"/api/applications/{application['id']}/generate-followup", json={}
    )

    assert response.status_code == 200, response.text
    assert provider.calls == 1
