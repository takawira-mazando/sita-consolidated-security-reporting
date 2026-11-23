from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import JWTClaims, verify_token
from app.api.routers import admin


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _Scalars(self.rows)


class _Session:
    def __init__(self):
        self.clients = []

    async def execute(self, _statement):
        return _Result(self.clients)

    async def get(self, _model, client_id):
        return next((client for client in self.clients if client.id == client_id), None)

    def add(self, client):
        self.clients.append(client)

    async def commit(self):
        return None

    async def refresh(self, client):
        now = datetime.now(timezone.utc)
        client.created_at = now
        client.updated_at = now

    async def rollback(self):
        return None


def _client(session: _Session, roles: list[str]) -> TestClient:
    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1/admin")
    app.dependency_overrides[admin.get_session] = lambda: session

    async def claims():
        return JWTClaims(sub="root-user", email="root@example.test", roles=roles)

    app.dependency_overrides[verify_token] = claims
    return TestClient(app)


def _profile_payload():
    return {
        "identifier": "example-client",
        "name": "Example Client",
        "description": "A client profile",
        "client_type": "enterprise",
        "deployment_model": "saas",
        "primary_contact_name": "Primary Contact",
        "primary_contact_email": "contact@example.test",
        "superadmin_name": "Client Admin",
        "superadmin_email": "admin@example.test",
    }


def test_provider_can_create_client_profile_without_activating_global_schema():
    session = _Session()
    client = _client(session, ["operator"])

    response = client.post("/api/v1/admin/client-organizations", json=_profile_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["deployment_model"] == "saas"
    assert body["access_setup_status"] == "pending_superadmin_setup"
    assert body["superadmin_email"] == "admin@example.test"
    assert session.clients[0].status == "draft"


def test_provider_can_add_a_client_specific_status():
    session = _Session()
    client = _client(session, ["operator"])
    created = client.post("/api/v1/admin/client-organizations", json=_profile_payload()).json()

    response = client.patch(
        f"/api/v1/admin/client-organizations/{created['id']}",
        json={"status": "implementation review"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "implementation review"
    assert "implementation review" in response.json()["status_options"]


def test_platform_admin_without_provider_role_cannot_manage_client_catalog():
    client = _client(_Session(), ["admin"])

    response = client.get("/api/v1/admin/client-organizations")

    assert response.status_code == 403


def test_client_profile_creation_rejects_role_configuration():
    client = _client(_Session(), ["operator"])
    payload = _profile_payload()
    payload["roles"] = ["admin"]

    response = client.post("/api/v1/admin/client-organizations", json=payload)

    assert response.status_code == 422
