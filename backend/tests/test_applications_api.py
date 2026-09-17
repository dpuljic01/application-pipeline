import uuid
from datetime import datetime

from app.core.security.deps import CurrentUser, get_current_user
from app.domain.enums import ApplicationStage


def _create_application(client, **overrides):
    payload = {
        "company": "Hamilton AG",
        "role_title": "Software Engineer",
        "job_url": "https://jobs.hamilton.ch/JR-5687",
        "location": "Bonaduz, CH",
        "salary_range": "100k-120k CHF",
    }
    payload.update(overrides)
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_create_application_happy_path(client):
    body = _create_application(client)

    assert body["company"] == "Hamilton AG"
    assert body["stage"] == ApplicationStage.SAVED.value
    assert body["stage_changed_at"] is None


def test_create_application_missing_required_field_returns_422(client):
    response = client.post("/api/applications", json={"role_title": "SWE"})
    assert response.status_code == 422


def test_get_application_returns_404_for_unknown_id(client):
    response = client.get(f"/api/applications/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_and_list_application(client):
    created = _create_application(client)

    got = client.get(f"/api/applications/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]

    listed = client.get("/api/applications")
    assert listed.status_code == 200
    assert any(a["id"] == created["id"] for a in listed.json())


def test_list_applications_ordered_newest_saved_first(client):
    first = _create_application(client, role_title="First")
    second = _create_application(client, role_title="Second")
    third = _create_application(client, role_title="Third")

    listed = client.get("/api/applications").json()
    ids = [a["id"] for a in listed]

    assert ids.index(third["id"]) < ids.index(second["id"]) < ids.index(first["id"])


def test_last_activity_at_updates_for_any_activity_type(client):
    # Not just FOLLOW_UP: any logged activity (e.g. a NOTE about the
    # employer's own update) counts as "something happened" for the
    # frontend's stale-application nudge to reset from.
    created = _create_application(client)
    assert created["last_activity_at"] is None

    response = client.post(
        f"/api/applications/{created['id']}/activities",
        json={"activity_type": "NOTE", "note": "They said they'll reply Monday."},
    )
    assert response.status_code == 201, response.text

    fetched = client.get(f"/api/applications/{created['id']}").json()
    assert fetched["last_activity_at"] is not None
    assert datetime.fromisoformat(
        fetched["last_activity_at"]
    ) == datetime.fromisoformat(response.json()["created_at"])


def test_put_application_updates_only_provided_fields(client):
    created = _create_application(client)

    response = client.put(
        f"/api/applications/{created['id']}",
        json={"location": "Remote"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Remote"
    assert body["company"] == created["company"]  # untouched


def test_put_application_returns_404_for_unknown_id(client):
    response = client.put(
        f"/api/applications/{uuid.uuid4()}",
        json={"location": "Remote"},
    )
    assert response.status_code == 404


def test_valid_stage_transition_succeeds_and_records_history(client):
    created = _create_application(client)

    response = client.patch(
        f"/api/applications/{created['id']}/stage",
        json={"stage": ApplicationStage.APPLIED.value},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == ApplicationStage.APPLIED.value
    assert body["stage_changed_at"] is not None
    assert body["last_activity_at"] is not None


def test_invalid_stage_transition_returns_409(client):
    created = _create_application(client)

    # SAVED -> INTERVIEW skips APPLIED, which isn't allowed.
    response = client.patch(
        f"/api/applications/{created['id']}/stage",
        json={"stage": ApplicationStage.INTERVIEW.value},
    )
    assert response.status_code == 409


def test_stage_change_on_unknown_application_returns_404(client):
    response = client.patch(
        f"/api/applications/{uuid.uuid4()}/stage",
        json={"stage": ApplicationStage.APPLIED.value},
    )
    assert response.status_code == 404


def test_delete_application_succeeds(client):
    created = _create_application(client)

    response = client.delete(f"/api/applications/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/applications/{created['id']}").status_code == 404


def test_delete_application_returns_404_for_unknown_id(client):
    response = client.delete(f"/api/applications/{uuid.uuid4()}")
    assert response.status_code == 404


def test_user_cannot_see_another_users_application(client):
    created = _create_application(client)

    # client fixture tears down dependency_overrides after the test, so it's
    # safe to swap the current-user override for the rest of this test only.
    client.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        cognito_sub=uuid.uuid4(),
        email=None,
    )

    response = client.get(f"/api/applications/{created['id']}")
    assert response.status_code == 404
