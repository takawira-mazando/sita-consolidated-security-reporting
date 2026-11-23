"""Tenant-scope authorization and input-validation regression tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.db import get_session
from app.main import app


def create_token(
    email: str,
    roles: list[str],
    departments: list[str],
    branches: list[str] | None = None,
    scope_units: list[str] | None = None,
) -> str:
    return jwt.encode(
        {
            "sub": "user-" + email.split("@")[0],
            "email": email,
            "roles": roles,
            "department_ids": departments,
            "branch_ids": branches or [],
            "province_ids": [],
            "tenant_scope_unit_ids": scope_units or [],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def treasury_soc_token():
    return create_token(
        "soc@example.com",
        ["soc"],
        ["treasury"],
        ["treasury-ict"],
        ["treasury", "treasury-ict"],
    )


@pytest.fixture
def treasury_appsec_token():
    return create_token(
        "appsec@example.com",
        ["appsec"],
        ["treasury"],
        ["treasury-ict"],
        ["treasury", "treasury-ict"],
    )


@pytest.mark.asyncio
async def test_cross_tenant_query_tampering_is_rejected(
    treasury_soc_token: str,
    treasury_appsec_token: str,
):
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            soc_headers = {"Authorization": f"Bearer {treasury_soc_token}"}
            appsec_headers = {"Authorization": f"Bearer {treasury_appsec_token}"}

            checks = [
                ("/api/v1/findings?department_id=justice-document", soc_headers),
                ("/api/v1/findings?branch_id=doj-ict", soc_headers),
                ("/api/v1/alerts?department_id=justice-document", soc_headers),
            ]
            for path, headers in checks:
                response = await client.get(path, headers=headers)
                assert response.status_code == 403
                assert "outside your assigned tenant access" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_queries_within_assigned_tenant_scope_are_allowed(
    treasury_soc_token: str,
    treasury_appsec_token: str,
):
    mock_session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            soc_headers = {"Authorization": f"Bearer {treasury_soc_token}"}
            appsec_headers = {"Authorization": f"Bearer {treasury_appsec_token}"}
            checks = [
                ("/api/v1/findings?department_id=treasury", soc_headers),
                ("/api/v1/findings?branch_id=treasury-ict", soc_headers),
                ("/api/v1/risks", appsec_headers),
                ("/api/v1/alerts?department_id=treasury", soc_headers),
            ]
            for path, headers in checks:
                response = await client.get(path, headers=headers)
                assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_workspace_header_cannot_select_an_unassigned_tenant():
    token = jwt.encode(
        {
            "sub": "scoped-admin",
            "email": "dept-admin@example.com",
            "roles": ["dept-admin"],
            "tenant_workspace_ids": ["workspace-a"],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-Workspace-ID": "workspace-b",
            },
        )
    assert response.status_code == 403
    assert "outside your assigned access" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_scope_parameters_reject_injection_payloads():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "pass",
                "department_id": "<script>alert('XSS')</script>",
            },
        )
        assert login_response.status_code == 422
        assert "<script>" not in login_response.text

        demo_response = await client.post(
            "/api/v1/auth/demo-login",
            json={
                "role": "soc",
                "department_id": "treasury' OR '1'='1",
            },
        )
        assert demo_response.status_code == 422
        assert "'1'='1" not in demo_response.text
