import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.db import get_session
from app.main import app


def make_raw_jwt(header: dict, payload: dict, signature: str = "") -> str:
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{h}.{p}.{signature}"


@pytest.mark.asyncio
async def test_weak_jwt_alg_none_rejected():
    """Verify that tokens with alg: none or forged signatures are rejected with 401."""
    # Crafted unsigned token (alg: none) exactly as HCL AppScan generates
    unsigned_token = make_raw_jwt(
        header={"typ": "JWT", "alg": "none"},
        payload={"sub": "attacker", "roles": ["admin"]},
    )
    # Crafted token with invalid/forged HMAC signature
    forged_token = make_raw_jwt(
        header={"typ": "JWT", "alg": "HS256"},
        payload={"sub": "attacker", "roles": ["admin"]},
        signature="invalid_forged_signature_12345",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Public summary with unsigned/alg:none token -> rejected with 401
        res1 = await ac.get(
            "/api/v1/public/summary",
            headers={"Authorization": f"Bearer {unsigned_token}"},
        )
        assert res1.status_code == 401
        assert "forbidden" in res1.json()["detail"].lower() or "invalid" in res1.json()["detail"].lower()

        # Tenancy hierarchy with forged signature -> rejected with 401
        res2 = await ac.get(
            "/api/v1/auth/tenancy",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert res2.status_code == 401
        assert res2.json()["detail"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_mass_assignment_rejected():
    """Verify that unexpected payload fields trigger 422 Unprocessable Entity."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Extra fields on demo-login (injected role, is_admin)
        res1 = await ac.post(
            "/api/v1/auth/demo-login",
            json={"role": "exec", "is_admin": True, "role_injected": "superadmin"},
        )
        assert res1.status_code == 422

        # Extra fields on login
        res2 = await ac.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "pass", "is_admin": True},
        )
        assert res2.status_code == 422


@pytest.mark.asyncio
async def test_pagination_bounds_enforced():
    """Verify that size=25000 is rejected with HTTP 422 instead of unbounded queries."""
    admin_token = jwt.encode(
        {"sub": "adm1", "email": "admin@test.gov.za", "roles": ["admin"]},
        settings.jwt_secret,
        algorithm="HS256",
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        res1 = await ac.get(
            "/admin/users?size=25000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res1.status_code == 422

        res2 = await ac.get(
            "/admin/persons?size=25000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res2.status_code == 422


@pytest.mark.asyncio
async def test_bfla_sre_metrics_role_gating():
    """Verify that /metrics/sre/system strictly requires sre or admin_read roles."""
    soc_token = jwt.encode(
        {"sub": "soc1", "email": "soc@test.gov.za", "roles": ["soc"]},
        settings.jwt_secret,
        algorithm="HS256",
    )
    sre_token = jwt.encode(
        {"sub": "sre1", "email": "sre@test.gov.za", "roles": ["sre"]},
        settings.jwt_secret,
        algorithm="HS256",
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            # Access with non-SRE role (SOC) MUST be 403 Forbidden
            res_forbidden = await ac.get(
                "/api/v1/metrics/sre/system",
                headers={"Authorization": f"Bearer {soc_token}"},
            )
            assert res_forbidden.status_code == 403

            # Access with SRE role should be 200 OK
            res_allowed = await ac.get(
                "/api/v1/metrics/sre/system",
                headers={"Authorization": f"Bearer {sre_token}"},
            )
            assert res_allowed.status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_cross_origin_and_security_headers():
    """Verify that COEP, COOP, CORP and security headers are injected into responses."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("cross-origin-embedder-policy") == "credentialless"
        assert headers.get("cross-origin-opener-policy") == "same-origin"
        assert headers.get("cross-origin-resource-policy") == "same-origin"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-content-type-options") == "nosniff"
        assert "server" not in headers


@pytest.mark.asyncio
async def test_null_byte_injection_rejected():
    """Verify that null byte injection in parameters returns 400 instead of 500 DB error."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Null byte in query parameter (like AppScan tested on /admin/persons?employment_status=%00)
        res = await ac.get("/admin/persons?employment_status=%00")
        assert res.status_code == 400
        assert "null byte" in res.json()["detail"].lower()
