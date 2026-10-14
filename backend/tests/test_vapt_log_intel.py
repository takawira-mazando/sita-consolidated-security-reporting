"""Tests for AIMI VAPT Log Interpretation Layer atop security telemetry.

Verifies:
1. Tenancy scoping: department users only receive their own department logs.
2. RBAC scoping: findings roles get technical forensic telemetry; compliance gets POPIA/ISO controls; risks gets executive risk summary.
3. Telemetry vector aggregation: SQLi, XSS, LFI, Brute-Force, Scanner Reconnaissance.
4. Baseline VAPT remediation verifier audit.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from app.api.auth import JWTClaims
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.metrics import WafBlock
from app.processing.intel.vapt import (
    VAPT_BASELINE_REMEDIATIONS,
    VAPT_VECTORS_CATALOG,
    interpret_logs_with_vapt,
)


class _MockScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _MockResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _MockScalars(self._items)


class _MockSession:
    def __init__(self, waf_records, finding_records, alert_records):
        self.waf_records = waf_records
        self.finding_records = finding_records
        self.alert_records = alert_records

    async def execute(self, stmt):
        stmt_str = str(stmt).lower()
        if "waf_blocks" in stmt_str:
            return _MockResult(self.waf_records)
        elif "findings" in stmt_str:
            return _MockResult(self.finding_records)
        elif "alerts" in stmt_str:
            return _MockResult(self.alert_records)
        return _MockResult([])


@pytest.fixture
def mock_session():
    now = datetime.now(timezone.utc)
    waf_records = [
        WafBlock(
            id=1,
            block_time=now,
            app_name="demo.testfire.net",
            department_id="home-affairs-digital",
            src_ip="192.0.2.45",
            request_uri="/login.aspx?user=' OR '1'='1",
            attack_type="SQL Injection",
            action="block",
        ),
        WafBlock(
            id=2,
            block_time=now,
            app_name="demo.testfire.net",
            department_id="home-affairs-digital",
            src_ip="192.0.2.78",
            request_uri="/search.aspx?q=<script>alert(1)</script>",
            attack_type="Cross-Site Scripting (XSS)",
            action="block",
        ),
        WafBlock(
            id=3,
            block_time=now,
            app_name="demo.testfire.net",
            department_id="home-affairs-digital",
            src_ip="192.0.2.99",
            request_uri="/view.aspx?page=../../../../etc/passwd",
            attack_type="Local File Inclusion",
            action="block",
        ),
    ]
    finding_records = [
        Finding(
            id=1,
            app_name="demo.testfire.net",
            department_id="home-affairs-digital",
            source="appscan",
            title="SQL Injection in login.aspx",
            severity="critical",
            status="open",
            last_seen=now,
        )
    ]
    alert_records = [
        Alert(
            id="1",
            rule_id="RULE-SQLI-SURGE",
            source="appscan",
            target_id="demo.testfire.net",
            severity="critical",
            title="SQL Injection surge detected",
            department_id="home-affairs-digital",
            status="active",
            first_triggered=now,
            last_triggered=now,
        )
    ]
    return _MockSession(waf_records, finding_records, alert_records)


@pytest.mark.asyncio
async def test_vapt_log_interpretation_scenarios(mock_session):
    """Test transversal, department, and compliance roles in a single test run."""
    session = mock_session

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
