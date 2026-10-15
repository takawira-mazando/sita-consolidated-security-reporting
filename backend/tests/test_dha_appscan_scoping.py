"""Verification of Department of Home Affairs (DHA) Scoping & AppScan Security Controls.

Validates that:
1. DHA demo personas are strictly isolated to 'home-affairs-digital' and its 8 DDG branches.
2. Cross-tenant tampering probes (IDOR/BOLA) passing non-DHA department_id are rejected with 403 Forbidden.
3. Malformed or injected scoping parameters (XSS/SQLi) fail Pydantic validation (422) with zero reflection.
4. Tenant switching and anti-elevation ceilings strictly block DHA admins from elevating privileges (403).
5. The DHA demo accounts endpoint serves strictly the 5 certified DHA PoC personas.
6. Real AppScan telemetry identifiers (b816b09c-... and demo.testfire.net) are bound to DHA.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.db import get_session
from app.main import app
from app.tenant import (
    APP_DEPARTMENTS,
    APP_BRANCHES,
    BRANCHES,
    DEPARTMENTS,
)


def create_token(email: str, roles: list[str], depts: list[str], branches: list[str] | None = None) -> str:
    return jwt.encode(
        {
            "sub": "user-" + email.split("@")[0],
            "email": email,
            "roles": roles,
            "department_ids": depts,
            "branch_ids": branches or [],
            "province_ids": [],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def dha_soc_token():
    return create_token(
        email="soc-ha@example.com",
        roles=["soc"],
        depts=["home-affairs-digital"],
        branches=["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"],
    )


@pytest.fixture
def dha_deptadmin_token():
    return create_token(
        email="deptadmin-ha@example.com",
        roles=["dept-admin"],
        depts=["home-affairs-digital"],
        branches=["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"],
    )


@pytest.fixture
def dha_appsec_token():
    return create_token(
        email="appsec-ha@example.com",
        roles=["appsec"],
        depts=["home-affairs-digital"],
        branches=["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"],
    )


@pytest.mark.asyncio
async def test_dha_testbed_topology_aligned():
    """Verify DHA tenant slug and all 8 real DDG operational branches exist."""
    assert "home-affairs-digital" in DEPARTMENTS
    assert DEPARTMENTS["home-affairs-digital"] == "Department of Home Affairs"

    expected_branches = {
        "dha-civic": "Civic Services",
        "dha-digital": "Information Services (CIO)",
        "dha-immigration": "Immigration Services",
        "dha-operations": "Operations",
        "dha-hrmd": "Human Resource Management and Development",
        "dha-ccss": "Counter Corruption and Security Services",
        "dha-finance": "Finance and Supply Chain Management",
        "dha-planning": "Institutional Planning and Support",
    }
    for branch_id, branch_name in expected_branches.items():
        assert branch_id in BRANCHES
        assert BRANCHES[branch_id][0] == branch_name
        assert BRANCHES[branch_id][1] == "home-affairs-digital"

    # AppScan Cloud UUID and testfire app mapped to DHA
    assert APP_DEPARTMENTS["demo.testfire.net"] == "home-affairs-digital"
    assert APP_DEPARTMENTS["b816b09c-4240-4ea7-a4b5-f8ae89f62f57"] == "home-affairs-digital"
    assert APP_BRANCHES["demo.testfire.net"] == "dha-digital"
    assert APP_BRANCHES["b816b09c-4240-4ea7-a4b5-f8ae89f62f57"] == "dha-digital"


@pytest.mark.asyncio
async def test_dha_demo_accounts_filtering():
    """Verify GET /api/v1/auth/demo-accounts?department_id=home-affairs-digital returns strictly DHA PoC personas."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Mock database User objects matching the demo accounts
    dha_users = [
        MagicMock(email="soc-ha@example.com", display_name="SOC Analyst (Home Affairs)", roles=["soc"], department_ids=["home-affairs-digital"], province_ids=[], is_active=True),
        MagicMock(email="appsec-ha@example.com", display_name="AppSec (Home Affairs)", roles=["appsec"], department_ids=["home-affairs-digital"], province_ids=[], is_active=True),
        MagicMock(email="dbsec-ha@example.com", display_name="DB Security (Home Affairs)", roles=["dbsec"], department_ids=["home-affairs-digital"], province_ids=[], is_active=True),
        MagicMock(email="deptadmin-ha@example.com", display_name="Dept Admin (Home Affairs)", roles=["dept-admin"], department_ids=["home-affairs-digital"], province_ids=[], is_active=True),
        MagicMock(email="branchadmin-ha@example.com", display_name="Branch Admin (Home Affairs)", roles=["branch-admin"], department_ids=["home-affairs-digital"], province_ids=[], is_active=True),
    ]
    mock_result.scalars.return_value.all.return_value = dha_users
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/v1/auth/demo-accounts?department_id=home-affairs-digital")
            assert res.status_code == 200
            accounts = res.json()
            assert len(accounts) == 5
            roles = [a["role"] for a in accounts]
            assert roles == ["soc-ha", "appsec-ha", "dbsec-ha", "deptadmin-ha", "branchadmin-ha"]
            for a in accounts:
                assert a["department_ids"] == ["home-affairs-digital"]
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_idor_cross_tenant_query_tampering_rejected(dha_soc_token, dha_appsec_token):
    """Verify that a DHA user tampering query parameters with foreign department_id gets 403 Forbidden."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            headers_soc = {"Authorization": f"Bearer {dha_soc_token}"}
            headers_appsec = {"Authorization": f"Bearer {dha_appsec_token}"}

            # 1. Attacker tries to query Treasury findings using DHA credentials
            res_findings = await ac.get("/api/v1/findings?department_id=treasury", headers=headers_soc)
            assert res_findings.status_code == 403
            assert "outside your assigned scope" in res_findings.json()["detail"]

            # 2. Attacker tries to query Treasury branch findings using DHA credentials
            res_branch = await ac.get("/api/v1/findings?branch_id=treasury-ict", headers=headers_soc)
            assert res_branch.status_code == 403
            assert "outside your assigned scope" in res_branch.json()["detail"]

            # 3. Attacker tries to query Treasury risks using DHA AppSec credentials
            res_risks = await ac.get("/api/v1/risks?department_id=treasury", headers=headers_appsec)
            assert res_risks.status_code == 403
            assert "outside your assigned scope" in res_risks.json()["detail"]

            # 4. Attacker tries to query Treasury alerts using DHA credentials
            res_alerts = await ac.get("/api/v1/alerts?department_id=treasury", headers=headers_soc)
            assert res_alerts.status_code == 403
            assert "outside your assigned scope" in res_alerts.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_valid_dha_scoped_queries_allowed(dha_soc_token, dha_appsec_token):
    """Verify that a DHA user can query with their own department or branch scope without error."""
    mock_session = AsyncMock()
    mock_scalar = MagicMock()
    mock_scalar.scalar_one.return_value = 0
    mock_scalar.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_scalar
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            headers_soc = {"Authorization": f"Bearer {dha_soc_token}"}
            headers_appsec = {"Authorization": f"Bearer {dha_appsec_token}"}

            # 1. Query findings explicitly scoped to DHA
            res_findings = await ac.get("/api/v1/findings?department_id=home-affairs-digital", headers=headers_soc)
            assert res_findings.status_code == 200

            # 2. Query findings scoped to valid DHA branch
            res_branch = await ac.get("/api/v1/findings?branch_id=dha-digital", headers=headers_soc)
            assert res_branch.status_code == 200

            # 3. Query risks scoped to DHA (using appsec)
            res_risks = await ac.get("/api/v1/risks?department_id=home-affairs-digital", headers=headers_appsec)
            assert res_risks.status_code == 200

            # 4. Query alerts scoped to DHA
            res_alerts = await ac.get("/api/v1/alerts?department_id=home-affairs-digital", headers=headers_soc)
            assert res_alerts.status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_dha_admin_switch_tenant_blocked(dha_deptadmin_token):
    """Verify DHA Department Admin cannot hop/switch tenants (anti-lateral movement)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {dha_deptadmin_token}"}
        res = await ac.post(
            "/api/v1/auth/switch-tenant",
            json={"department_id": "treasury"},
            headers=headers,
        )
        assert res.status_code == 403
        assert "restricted to admin and transversal-admin" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_appscan_xss_sqli_payload_in_scope_rejected():
    """Verify that AppScan injection payloads in scope fields return 422 with zero reflection."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # XSS injection attempt in department_id
        res_xss = await ac.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "pass",
                "department_id": "<script>alert('XSS')</script>",
            },
        )
        assert res_xss.status_code == 422
        # Verify the raw script tag is not reflected back in detail as HTML
        assert "<script>" not in res_xss.text

        # SQLi injection attempt in department_id on demo-login
        res_sqli = await ac.post(
            "/api/v1/auth/demo-login",
            json={
                "role": "soc-ha",
                "department_id": "home-affairs' OR '1'='1",
            },
        )
        assert res_sqli.status_code == 422
        assert "'1'='1" not in res_sqli.text
