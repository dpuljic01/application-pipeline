import uuid

from app.core.security.deps import CurrentUser, get_current_user


def _create_company(client, **overrides):
    payload = {
        "name": "Northgate AG",
        "website": "https://northgate.example",
        "industry": "Medical devices",
        "size": "MID",
        "location": "Zurich, CH",
        "notes": "Found via a referral",
    }
    payload.update(overrides)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


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


def test_create_company_happy_path(client):
    body = _create_company(client)

    assert body["name"] == "Northgate AG"
    assert body["size"] == "MID"
    assert body["website"] == "https://northgate.example/"


def test_create_company_missing_required_field_returns_422(client):
    response = client.post("/api/companies", json={"website": "https://x.ch"})
    assert response.status_code == 422


def test_get_company_returns_404_for_unknown_id(client):
    response = client.get(f"/api/companies/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_companies_and_search_is_case_insensitive(client):
    _create_company(client, name="Northgate AG")
    _create_company(client, name="Acme Zurich")

    listed = client.get("/api/companies")
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    searched = client.get("/api/companies", params={"search": "northgate"})
    assert searched.status_code == 200
    assert len(searched.json()) == 1
    assert searched.json()[0]["name"] == "Northgate AG"


def test_update_company_updates_only_provided_fields(client):
    created = _create_company(client)

    response = client.put(
        f"/api/companies/{created['id']}", json={"industry": "Biotech"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "Biotech"
    assert body["name"] == created["name"]  # untouched


def test_delete_company_without_applications_succeeds(client):
    created = _create_company(client)

    response = client.delete(f"/api/companies/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/companies/{created['id']}").status_code == 404


def test_delete_company_with_applications_returns_409(client):
    company = _create_company(client, name="Northgate AG")
    _create_application(client, company="Northgate AG")

    response = client.delete(f"/api/companies/{company['id']}")
    assert response.status_code == 409


def test_two_applications_same_company_name_link_to_one_company(client):
    first = _create_application(client, company="Northgate AG")
    second = _create_application(
        client, company="northgate ag", role_title="Backend Engineer"
    )

    assert first["company_id"] is not None
    assert first["company_id"] == second["company_id"]

    companies = client.get("/api/companies").json()
    assert len(companies) == 1


def test_application_with_explicit_company_id_links_to_it(client):
    company = _create_company(client, name="Northgate AG")

    application = _create_application(
        client, company="Northgate AG", company_id=company["id"]
    )

    assert application["company_id"] == company["id"]


def test_application_with_unknown_company_id_returns_404(client):
    response = client.post(
        "/api/applications",
        json={
            "company": "Northgate AG",
            "role_title": "Software Engineer",
            "company_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404


def test_list_applications_for_company(client):
    company = _create_company(client, name="Northgate AG")
    _create_application(client, company="Northgate AG", company_id=company["id"])
    _create_application(
        client,
        company="Northgate AG",
        company_id=company["id"],
        role_title="Backend Engineer",
    )

    response = client.get(f"/api/companies/{company['id']}/applications")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_applications_for_unknown_company_returns_404(client):
    response = client.get(f"/api/companies/{uuid.uuid4()}/applications")
    assert response.status_code == 404


def test_user_cannot_see_another_users_company(client):
    created = _create_company(client)

    client.app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid.uuid4(),
        cognito_sub=uuid.uuid4(),
        email=None,
    )

    response = client.get(f"/api/companies/{created['id']}")
    assert response.status_code == 404
