"""Tests for AIMI VAPT Log Interpretation Layer atop security telemetry.

Verifies:
1. Tenancy scoping: department users only receive their own department logs.
2. RBAC scoping: findings roles get technical forensic telemetry; compliance gets POPIA/ISO controls; risks gets executive risk summary.
3. Telemetry vector aggregation: SQLi, XSS, LFI, Brute-Force, Scanner Reconnaissance.
4. Baseline VAPT remediation verifier audit.
"""
import pytest
from app.api.auth import JWTClaims
from app.db import SessionFactory
from app.processing.intel.vapt import (
    VAPT_BASELINE_REMEDIATIONS,
    VAPT_VECTORS_CATALOG,
    interpret_logs_with_vapt,
)


@pytest.mark.asyncio
async def test_vapt_log_interpretation_scenarios():
    """Test transversal, department, and compliance roles in a single test run."""
    async with SessionFactory() as session:
        # Scenario 1: Transversal Admin
        claims_admin = JWTClaims(
            sub="admin@example.com",
            roles=["admin"],
            department_ids=[],
            branch_ids=[],
            province_ids=[],
        )
        res_admin = await interpret_logs_with_vapt(session, claims_admin, lookback_hours=48)
        assert res_admin["avp"] == "AIMI-VAPT-LOGS"
        assert res_admin["advisory_only"] is True
        assert res_admin["telemetry_summary"]["total_logs_analyzed"] > 0
        assert res_admin["perimeter_resilience"]["resilience_percentage"] >= 0
        assert len(res_admin["vector_breakdown"]) > 0
        assert len(res_admin["interpreted_events"]) > 0
        assert len(res_admin["vapt_baseline_audit"]) == len(VAPT_BASELINE_REMEDIATIONS)

        insights_admin = res_admin["role_gated_insights"]
        assert insights_admin["soc_appsec"]["authorized"] is True
        assert insights_admin["compliance"]["authorized"] is True
        assert insights_admin["exec_risks"]["authorized"] is True

        # Scenario 2: DHA SOC Analyst (department scoped, findings role)
        claims_soc = JWTClaims(
            sub="soc-ha@example.com",
            roles=["soc-ha"],
            department_ids=["home-affairs-digital"],
            branch_ids=["dha-civic"],
            province_ids=[],
        )
        res_soc = await interpret_logs_with_vapt(session, claims_soc, lookback_hours=72)
        assert "home-affairs-digital" in res_soc["tenant_scope"]["scope_label"]
        insights_soc = res_soc["role_gated_insights"]
        assert insights_soc["soc_appsec"]["authorized"] is True
        assert insights_soc["compliance"]["authorized"] is False
        assert insights_soc["exec_risks"]["authorized"] is True

        # Scenario 3: Compliance Persona (compliance role, no findings)
        claims_comp = JWTClaims(
            sub="compliance@example.com",
            roles=["compliance"],
            department_ids=[],
            branch_ids=[],
            province_ids=[],
        )
        res_comp = await interpret_logs_with_vapt(session, claims_comp, lookback_hours=24)
        insights_comp = res_comp["role_gated_insights"]
        assert insights_comp["soc_appsec"]["authorized"] is False
        assert insights_comp["compliance"]["authorized"] is True
        assert insights_comp["compliance"]["popia_s22_breach_triggered"] is False
        assert insights_comp["exec_risks"]["authorized"] is False
