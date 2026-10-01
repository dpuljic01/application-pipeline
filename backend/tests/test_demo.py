"""Demo account: seeding from demo_seed.json, reset cooldown, and the
one-click POST /auth/demo login (Cognito calls mocked)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.core.security.cognito_jwt import TokenPayload
from app.db.mixins import utcnow
from app.db.models import Activity, Application, Company, Profile, User
from app.domain.enums import ALLOWED_TRANSITIONS, ApplicationStage
from app.services import demo_service
from app.services.demo_service import DemoService, load_seed


@pytest.fixture(autouse=True)
def _fresh_cooldown(monkeypatch):
    monkeypatch.setattr(demo_service, "_last_reset", None)


@pytest.fixture()
def demo_user(db_session):
    user = User(cognito_sub=uuid.uuid4(), email="demo@example.com")
    db_session.add(user)
    db_session.flush()
    return user


def _apps(db_session, user_id):
    return db_session.scalars(
        select(Application).where(Application.user_id == user_id)
    ).all()


def test_seed_file_only_uses_valid_stage_paths():
    for spec in load_seed()["applications"]:
        stage = ApplicationStage.SAVED
        for to_stage, _days in spec["history"]:
            assert ApplicationStage(to_stage) in ALLOWED_TRANSITIONS[stage], spec
            stage = ApplicationStage(to_stage)


def test_reset_seeds_profile_applications_and_timeline(db_session, demo_user):
    DemoService(db_session).reset(user_id=demo_user.id)

    seed = load_seed()
    apps = _apps(db_session, demo_user.id)
    assert len(apps) == len(seed["applications"])
    assert {a.stage for a in apps} >= {
        ApplicationStage.SAVED,
        ApplicationStage.APPLIED,
        ApplicationStage.INTERVIEW,
        ApplicationStage.OFFER,
    }
    profile = db_session.scalar(select(Profile).where(Profile.user_id == demo_user.id))
    assert profile.skills == seed["profile"]["skills"]

    northgate = next(a for a in apps if a.company == "Northgate AG")
    assert northgate.stage == ApplicationStage.INTERVIEW
    assert northgate.match_score is not None
    assert northgate.linked_company.name == "Northgate AG"
    # Dates are relative to seed time, so the demo never looks stale.
    assert utcnow() - northgate.stage_changed_at < timedelta(days=7)
    activities = db_session.scalars(
        select(Activity).where(Activity.application_id == northgate.id)
    ).all()
    assert len(activities) >= 2


def test_reset_replaces_visitor_changes_instead_of_duplicating(db_session, demo_user):
    service = DemoService(db_session)
    service.reset(user_id=demo_user.id)
    db_session.add(
        Application(user_id=demo_user.id, company="Visitor Co", role_title="Test")
    )
    db_session.flush()

    service.reset(user_id=demo_user.id)

    apps = _apps(db_session, demo_user.id)
    assert len(apps) == len(load_seed()["applications"])
    assert "Visitor Co" not in {a.company for a in apps}
    companies = db_session.scalar(
        select(func.count()).select_from(Company).where(Company.user_id == demo_user.id)
    )
    assert companies == len({s["company"] for s in load_seed()["applications"]})


def test_reset_leaves_other_users_alone(db_session, demo_user, test_user):
    db_session.add(Application(user_id=test_user.id, company="Mine AG", role_title="X"))
    db_session.flush()

    DemoService(db_session).reset(user_id=demo_user.id)

    assert [a.company for a in _apps(db_session, test_user.id)] == ["Mine AG"]


def test_cooldown_skips_a_second_reset(db_session, demo_user):
    service = DemoService(db_session)
    assert service.reset_if_stale(user_id=demo_user.id) is True
    assert service.reset_if_stale(user_id=demo_user.id) is False


# --- POST /auth/demo -------------------------------------------------------


@pytest.fixture()
def demo_enabled(monkeypatch, db_session):
    monkeypatch.setattr(settings, "DEMO_EMAIL", "demo@example.com")
    monkeypatch.setattr(settings, "DEMO_PASSWORD", "not-a-real-password")
    sub = uuid.uuid4()

    async def fake_sign_in(username, password):
        assert (username, password) == ("demo@example.com", "not-a-real-password")
        return {
            "IdToken": "id.token.here",
            "RefreshToken": "refresh-token",
            "AccessToken": "secret",
        }

    async def fake_verify(token):
        return TokenPayload(
            sub=str(sub),
            email="demo@example.com",
            token_use="id",
            exp=0,
            iat=0,
        )

    monkeypatch.setattr(auth_routes, "sign_in", fake_sign_in)
    monkeypatch.setattr(auth_routes, "verify_jwt", fake_verify)
    return sub


def test_demo_login_returns_only_the_id_token_and_seeds(
    client, db_session, demo_enabled
):
    response = client.post("/api/auth/demo")

    assert response.status_code == 200, response.text
    assert response.json() == {"id_token": "id.token.here"}
    assert "refresh_token" in response.cookies
    assert "secret" not in response.text
    user = db_session.scalar(select(User).where(User.cognito_sub == demo_enabled))
    assert len(_apps(db_session, user.id)) == len(load_seed()["applications"])


def test_demo_login_is_404_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_EMAIL", None)
    assert client.post("/api/auth/demo").status_code == 404
