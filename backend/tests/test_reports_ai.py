"""Unit & Integration Test Suite for AI Report Generation Engine (Stage 4 / G2).

Tests:
1. Gate 1 Capability RBAC (default-deny, role-restricted report types).
2. Gate 2 Tenancy Scoping (ReportScope, scope_hash stability & isolation).
3. Numeral Fidelity Verifier (catches hallucinations, verifies factual grounding).
4. Deterministic Fallback Generation (complete envelope, zero LLM dependency).
5. REST API Endpoints (/reports-ai/available, /reports-ai/generate, /reports-ai/catalog).
"""
from unittest.mock import AsyncMock
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.ai.generator import _render_deterministic_report, generate_report
from app.ai.permissions import can_access_report, get_available_reports
from app.ai.scope import compute_scope_hash, resolve_report_scope
from app.ai.verify import verify_numeral_fidelity
from app.api.auth import JWTClaims
from app.api.routers.reports_ai import _active_workspace_report_scope
from app.config import settings
from app.db import get_session
from app.main import app
from app.models.finding import Finding


def create_token(email: str, roles: list[str], depts: list[str] | None = None) -> str:
    return jwt.encode(
        {
            "sub": "user-" + email.split("@")[0],
            "email": email,
            "roles": roles,
            "department_ids": depts or [],
            "branch_ids": [],
            "province_ids": [],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def exec_token():
    return create_token("exec@example.com", ["exec"])


@pytest.fixture
def soc_token():
    return create_token("soc@example.com", ["soc"], ["treasury"])


@pytest.fixture
def appsec_token():
    return create_token("appsec@example.com", ["appsec"], ["treasury"])


@pytest.fixture
def compliance_token():
    return create_token("compliance@example.com", ["compliance"])


@pytest.fixture
def admin_token():
    return create_token("admin@example.com", ["admin"])


# -----------------------------------------------------------------------------
# 1. GATE 1: RBAC CAPABILITY TESTS
# -----------------------------------------------------------------------------

def test_gate_1_rbac_permissions():
    """Verify Gate 1 role restrictions across report types."""
    # Executive can access executive_summary, not technical vulnerability posture
    assert can_access_report(["exec"], "executive_summary") is True
    assert can_access_report(["exec"], "vulnerability_posture") is False

    # AppSec can access vulnerability_posture, not executive_summary
    assert can_access_report(["appsec"], "vulnerability_posture") is True
    assert can_access_report(["appsec"], "executive_summary") is False

    # SOC can access threat_intel_brief & incident_summary
    assert can_access_report(["soc"], "threat_intel_brief") is True
    assert can_access_report(["soc"], "incident_summary") is True
    assert can_access_report(["soc"], "popia_impact_assessment") is False

    # Compliance can access popia_impact_assessment & ag_audit_readiness
    assert can_access_report(["compliance"], "popia_impact_assessment") is True
    assert can_access_report(["compliance"], "ag_audit_readiness") is True

    # Admin can access everything
    assert can_access_report(["admin"], "executive_summary") is True
    assert can_access_report(["admin"], "threat_intel_brief") is True
    assert can_access_report(["admin"], "vulnerability_posture") is True
    assert can_access_report(["admin"], "compliance_status") is True

    # Unknown role rejected
    assert can_access_report(["guest_user"], "executive_summary") is False


def test_get_available_reports_filtering():
    """Verify available report list is tailored to the caller's role."""
    exec_reports = get_available_reports(["exec"])
    exec_types = [r["report_type"] for r in exec_reports]
    assert "executive_summary" in exec_types
    assert "vulnerability_posture" not in exec_types

    appsec_reports = get_available_reports(["appsec"])
    appsec_types = [r["report_type"] for r in appsec_reports]
    assert "vulnerability_posture" in appsec_types
    assert "executive_summary" not in appsec_types


# -----------------------------------------------------------------------------
# 2. GATE 2: TENANCY SCOPE & HASH ISOLATION
# -----------------------------------------------------------------------------

def test_gate_2_scope_hash_isolation():
    """Verify scope_hash determinism and cross-tenant separation."""
    hash_tenant = compute_scope_hash(["workspace-a"], ["unit-a"], ["division"], False)
    hash_other_tenant = compute_scope_hash(["workspace-b"], ["unit-a"], ["division"], False)
    hash_platform = compute_scope_hash([], [], [], True)

    assert len(hash_tenant) == 64
    assert hash_tenant != hash_other_tenant
    assert hash_tenant != hash_platform

    # Determinism: identical scopes yield identical hashes
    assert hash_tenant == compute_scope_hash(["workspace-a"], ["unit-a"], ["division"], False)
    claims = JWTClaims(
        roles=["soc"],
        tenant_workspace_ids=["workspace-a"],
        tenant_scope_unit_ids=["unit-a"],
        active_tenant_workspace_id="workspace-a",
        active_tenant_scope_level_keys=["division"],
    )
    scope = resolve_report_scope(claims)
    assert scope.scope_hash == hash_tenant
    assert "unit-a" in scope.tenant_scope_unit_ids
    assert scope.is_platform_scope is False


def test_tenant_report_scope_isolated_by_workspace_and_tier():
    claims = JWTClaims(
        roles=[],
        tenant_workspace_ids=["workspace-a"],
        tenant_workspace_access=[
            {
                "workspace_id": "workspace-a",
                "workspace_name": "Tenant A",
            },
        ],
        active_tenant_workspace_id="workspace-a",
        active_tenant_scope_level_keys=["division", "team"],
    )

    scope = resolve_report_scope(claims)
    filter_sql = str(
        scope.get_filter(Finding).compile(compile_kwargs={"literal_binds": True})
    )
    other_scope_hash = compute_scope_hash(
        ["workspace-b"], [], ["division", "team"], False
    )

    assert scope.describe() == "Tenant A - division, team"
    assert "workspace-a" in filter_sql
    assert "tenant_scope_level_key" in filter_sql
    assert scope.scope_hash != other_scope_hash


def test_tenant_report_authorization_uses_active_workspace_role_scope():
    claims = JWTClaims(
        roles=[],
        tenant_workspace_ids=["workspace-a"],
        tenant_workspace_access=[
            {
                "workspace_id": "workspace-a",
                "workspace_name": "Tenant A",
                "cockpit_scopes": {"soc": ["team"]},
            },
        ],
        active_tenant_workspace_id="workspace-a",
    )

    cockpit_roles, scope_levels = _active_workspace_report_scope(
        claims, "threat_intel_brief"
    )
    scoped_claims = claims.model_copy(
        update={"active_tenant_scope_level_keys": sorted(scope_levels)}
    )
    scope = resolve_report_scope(scoped_claims)

    assert cockpit_roles == {"soc"}
    assert scope.tenant_workspace_id == "workspace-a"
    assert scope.tenant_scope_level_keys == ("team",)
    assert "workspace-a" in str(
        scope.get_filter(Finding).compile(compile_kwargs={"literal_binds": True})
    )


# -----------------------------------------------------------------------------
# 3. NUMERAL FIDELITY VERIFICATION TESTS
# -----------------------------------------------------------------------------

def test_numeral_fidelity_verifier():
    """Verify numeral fidelity checker flags invented numbers and passes factual ones."""
    facts = {
        "total_findings": 69,
        "critical_findings": 0,
        "high_findings": 0,
        "medium_findings": 12,
        "avg_risk_score": 34.2,
        "open_alerts": 2,
        "compliance_posture_index": 100,
    }

    # Accurate text
    accurate_text = (
        "Evaluation records 69 total findings, with 12 medium vulnerabilities and 0 critical issues. "
        "The average risk score is 34.2, and 2 open alerts remain."
    )
    is_valid, score, discrepancies = verify_numeral_fidelity(accurate_text, facts)
    assert is_valid is True
    assert score >= 0.90
    assert len(discrepancies) == 0

    # Hallucinated text with non-existent numbers
    hallucinated_text = (
        "There are 9999 critical breaches and 888 compromised databases with a score of 777.7."
    )
    is_valid_h, score_h, discrepancies_h = verify_numeral_fidelity(hallucinated_text, facts)
    assert is_valid_h is False
    assert score_h < 0.50
    assert "9999.0" in discrepancies_h or "888.0" in discrepancies_h


# -----------------------------------------------------------------------------
# 4. DETERMINISTIC FALLBACK & ENVELOPE GENERATION
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deterministic_report_generation():
    """Verify fallback template produces complete, verified report envelope without LLM."""
    mock_session = AsyncMock()
    claims = JWTClaims(
        roles=["soc"],
        tenant_workspace_ids=["workspace-a"],
        tenant_scope_unit_ids=["unit-a"],
        active_tenant_workspace_id="workspace-a",
        active_tenant_scope_level_keys=["division"],
    )
    scope = resolve_report_scope(claims)

    report = await generate_report(mock_session, scope, "threat_intel_brief")

    assert report["report_type"] == "threat_intel_brief"
    assert report["title"] == "SOC Threat Intelligence & Alert Triage Brief"
    assert report["fallback_used"] is True
    assert report["verification"]["passed"] is True
    assert report["verification"]["zero_hallucination_guaranteed"] is True
    assert report["scope_hash"] == scope.scope_hash
    assert len(report["summary"]) > 20
    assert len(report["key_findings"]) >= 2
    assert len(report["recommendations"]) >= 2
    assert "facts" in report


# -----------------------------------------------------------------------------
# 5. REST API ROUTER INTEGRATION TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_available_reports(exec_token, appsec_token):
    """Verify GET /api/v1/reports-ai/available enforces Gate 1."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Exec user
        res_exec = await ac.get(
            "/api/v1/reports-ai/available",
            headers={"Authorization": f"Bearer {exec_token}"},
        )
        assert res_exec.status_code == 200
        types_exec = [r["report_type"] for r in res_exec.json()]
        assert "executive_summary" in types_exec
        assert "vulnerability_posture" not in types_exec

        # AppSec user
        res_appsec = await ac.get(
            "/api/v1/reports-ai/available",
            headers={"Authorization": f"Bearer {appsec_token}"},
        )
        assert res_appsec.status_code == 200
        types_appsec = [r["report_type"] for r in res_appsec.json()]
        assert "vulnerability_posture" in types_appsec
        assert "executive_summary" not in types_appsec


@pytest.mark.asyncio
async def test_api_generate_unauthorized_role_rejected(soc_token):
    """Verify POST /api/v1/reports-ai/generate rejects unauthorized report type with 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # SOC analyst tries to generate executive_summary (unauthorized)
        res = await ac.post(
            "/api/v1/reports-ai/generate",
            json={"report_type": "executive_summary"},
            headers={"Authorization": f"Bearer {soc_token}"},
        )
        assert res.status_code == 403
        assert "not authorized" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_generate_authorized_report_success(exec_token):
    """Verify POST /api/v1/reports-ai/generate succeeds for authorized persona."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/reports-ai/generate",
                json={"report_type": "executive_summary"},
                headers={"Authorization": f"Bearer {exec_token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["report_type"] == "executive_summary"
            assert data["verification"]["passed"] is True
            assert "summary" in data
            assert len(data["recommendations"]) > 0
    finally:
        app.dependency_overrides.pop(get_session, None)
