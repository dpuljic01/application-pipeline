import uuid

from app.core.security.deps import CurrentUser, get_current_user


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


def _create_activity(client, application_id, **overrides):
    payload = {"activity_type": "NOTE", "note": "Good first call."}
    payload.update(overrides)
    response = client.post(
        f"/api/applications/{application_id}/activities", json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_activities_returns_newest_first(client):
    application = _create_application(client)

    _create_activity(
        client, application["id"], note="Applied.", occurred_at="2026-09-01T09:00:00Z"
    )
    _create_activity(
        client,
        application["id"],
        activity_type="INTERVIEW",
        note="First interview, went well.",
        occurred_at="2026-09-10T09:00:00Z",
    )

    response = client.get(f"/api/applications/{application['id']}/activities")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["note"] == "First interview, went well."
    assert body[1]["note"] == "Applied."


def test_list_activities_includes_auto_logged_stage_change(client):
    application = _create_application(client)

    client.patch(
        f"/api/applications/{application['id']}/stage", json={"stage": "APPLIED"}
    )

    response = client.get(f"/api/applications/{application['id']}/activities")
    assert response.status_code == 200
    body = response.json()
    assert any(a["activity_type"] == "STAGE_CHANGE" for a in body)


def test_list_activities_for_unknown_application_returns_404(client):
    response = client.get(f"/api/applications/{uuid.uuid4()}/activities")
    assert response.status_code == 404


def test_user_cannot_list_another_users_activities(client):
    application = _create_application(client)
    _create_activity(client, application["id"])

    client.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        cognito_sub=uuid.uuid4(),
        email=None,
    )

    response = client.get(f"/api/applications/{application['id']}/activities")
    assert response.status_code == 404
