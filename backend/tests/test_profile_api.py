import uuid

from app.core.security.deps import CurrentUser, get_current_user
from app.db.models.user import User


def test_get_profile_auto_creates_with_empty_fields(client):
    response = client.get("/api/profile")
    assert response.status_code == 200
    body = response.json()

    assert body["years_experience"] is None
    assert body["skills"] == []
    assert body["languages"] == []
    assert body["target_seniorities"] == []
    assert body["min_salary_chf"] is None
    assert body["ideal_salary_chf"] is None
    assert body["home_location"] is None


def test_get_profile_is_idempotent(client):
    first = client.get("/api/profile").json()
    second = client.get("/api/profile").json()
    assert first["id"] == second["id"]


def test_update_profile_updates_only_provided_fields(client):
    client.get("/api/profile")  # auto-create

    response = client.put(
        "/api/profile",
        json={
            "years_experience": 7,
            "skills": ["Python", "FastAPI"],
            "min_salary_chf": 90000,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["years_experience"] == 7
    assert body["skills"] == ["Python", "FastAPI"]
    assert body["min_salary_chf"] == 90000
    assert body["ideal_salary_chf"] is None  # untouched
    assert body["languages"] == []  # untouched


def test_update_profile_persists_languages_and_seniorities(client):
    response = client.put(
        "/api/profile",
        json={
            "languages": [
                {"language": "English", "level": "fluent"},
                {"language": "German", "level": "B1"},
            ],
            "target_seniorities": ["mid", "senior"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["languages"] == [
        {"language": "English", "level": "fluent"},
        {"language": "German", "level": "B1"},
    ]
    assert body["target_seniorities"] == ["mid", "senior"]


def test_update_profile_rejects_invalid_seniority_value(client):
    response = client.put("/api/profile", json={"target_seniorities": ["expert"]})
    assert response.status_code == 422


def test_update_profile_rejects_wrong_type_for_skills(client):
    response = client.put("/api/profile", json={"skills": "Python"})
    assert response.status_code == 422


def test_user_cannot_see_another_users_profile(client, db_session):
    first = client.put("/api/profile", json={"years_experience": 10}).json()

    # Profile auto-creates on GET (unlike Company), and its user_id is a
    # real FK to users.id - the second user needs a real row, not just a
    # random UUID, or the auto-create insert itself would fail.
    other_user = User(cognito_sub=uuid.uuid4(), email="other@example.com")
    db_session.add(other_user)
    db_session.flush()

    client.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=other_user.id,
        cognito_sub=other_user.cognito_sub,
        email=other_user.email,
    )

    second = client.get("/api/profile").json()
    assert second["id"] != first["id"]
    assert second["years_experience"] is None
