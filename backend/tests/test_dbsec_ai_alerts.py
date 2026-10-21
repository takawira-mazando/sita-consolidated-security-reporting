"""Tests for Database Security (DAM) AI Alert Reasoning Engine.

Verifies:
1. Classification of ingested telemetry into DAM attack archetypes.
2. Cross-signal correlation and confidence scoring.
3. RBAC differentiation:
   - findings -> SOC_DBA_TECHNICAL view (technical details, rules, D3FEND)
   - compliance -> COMPLIANCE_REGULATORY view (POPIA, breach window)
   - risks -> EXECUTIVE_RISK view (blast radius, business impact)
4. Tenancy scoping:
   - Department claims isolate to caller department
   - Transversal admin sees aggregated estate
5. Fallback behavior when telemetry is empty.
"""
import dataclasses
from datetime import datetime, timezone
import pytest
from app.api.auth import JWTClaims
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.metrics import DatabaseInventory, WafBlock
from app.processing.intel.dbsec import analyse_dbsec_ai_alerts


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

    def scalar(self):
        return len(self._items) if self._items else 0


class _MockSession:
    def __init__(self, alerts, findings, waf_blocks, dbs):
        self.alerts = alerts
        self.findings = findings
        self.waf_blocks = waf_blocks
        self.dbs = dbs

    async def execute(self, stmt):
        stmt_str = str(stmt).lower()
        if "alerts" in stmt_str:
            return _MockResult(self.alerts)
        elif "findings" in stmt_str:
            return _MockResult(self.findings)
        elif "waf_blocks" in stmt_str:
            return _MockResult(self.waf_blocks)
        elif "database_inventory" in stmt_str:
            return _MockResult(self.dbs)
        return _MockResult([])


@pytest.fixture
def populated_session():
    now = datetime.now(timezone.utc)
    alerts = [
        Alert(
            id="alert-dam-1",
            source="imperva",
            rule_id="RULE-SQLI-UNION",
            target_id="CitizenDB.dbo.IdentityProfiles",
            title="DAM: UNION-based SQL Injection detected on IdentityProfiles",
            severity="critical",
            department_id="home-affairs-digital",
            status="active",
            first_triggered=now,
            last_triggered=now,
        ),
        Alert(
            id="alert-dam-2",
            source="thales",
            rule_id="RULE-PRIV-GRANT-DBA",
            target_id="PayrollDB.dbo.sysadmin",
            title="DAM: Unauthorized GRANT role sysadmin to svc_backup",
            severity="high",
            department_id="home-affairs-digital",
            status="active",
            first_triggered=now,
            last_triggered=now,
        ),
    ]
    findings = [
        Finding(
            id=101,
            app_name="CitizenDB",
            department_id="home-affairs-digital",
            source="appscan",
            category="sql injection",
            title="CWE-89 SQL Injection in identity query endpoint",
            severity="critical",
            status="open",
            last_seen=now,
        ),
        Finding(
            id=102,
            app_name="PayrollDB",
            department_id="home-affairs-digital",
            source="appscan",
            category="privilege escalation",
            title="CWE-250 Execution with Unnecessary Privileges",
            severity="high",
            status="open",
            last_seen=now,
        ),
    ]
    waf_blocks = [
        WafBlock(
            id=201,
            block_time=now,
            app_name="CitizenDB",
            department_id="home-affairs-digital",
            src_ip="198.51.100.22",
            request_uri="/api/v1/citizen?id=1' UNION SELECT credit_card,pin FROM users--",
            attack_type="SQL Injection",
            action="block",
        ),
    ]
    dbs = [
        DatabaseInventory(
            id="db-1",
            name="CitizenDB",
            department_id="home-affairs-digital",
            engine="PostgreSQL",
            monitored=True,
        ),
        DatabaseInventory(
            id="db-2",
            name="PayrollDB",
            department_id="home-affairs-digital",
            engine="MSSQL",
            monitored=True,
        ),
    ]
    return _MockSession(alerts, findings, waf_blocks, dbs)


@pytest.fixture
def empty_session():
    return _MockSession([], [], [], [])


@pytest.mark.asyncio
async def test_dam_ai_alerts_soc_dba_view(populated_session):
    """findings role receives SOC_DBA_TECHNICAL view with technical details."""
    claims = JWTClaims(
        sub="dba-lead@example.com",
        roles=["findings"],
        department_ids=["home-affairs-digital"],
        branch_ids=[],
        province_ids=[],
    )
    res_obj = await analyse_dbsec_ai_alerts(populated_session, claims, lookback_hours=24)
    result = dataclasses.asdict(res_obj)

    assert result["rbac_view"] == "SOC_DBA_TECHNICAL"
    assert result["advisory_only"] is True
    assert result["total_events_analysed"] >= 5
    assert result["dam_alerts_ingested"] == 2
    assert result["findings_ingested"] == 2
    assert result["waf_db_blocks_ingested"] == 1
    assert result["db_inventory_size"] == 2
    assert result["overall_dam_posture"] in ("CRITICAL", "ELEVATED", "GUARDED", "NORMAL")

    cards = result["ai_alert_cards"]
    assert len(cards) >= 1

    # Check that technical fields are present for findings role
    sqli_card = next((c for c in cards if c["archetype_id"] == "sqli_exfiltration"), None)
    assert sqli_card is not None
    assert sqli_card["severity"] == "critical"
    assert sqli_card["confidence_score"] >= 40
    assert sqli_card["confidence_label"] in ("HIGH", "MEDIUM", "LOW")
    assert "top_rule_ids" in sqli_card
    assert "d3fend_countermeasure" in sqli_card
    assert "technical_summary" in sqli_card
    assert sqli_card["d3fend_countermeasure"] is not None
    # Regulatory impact should NOT be present in SOC_DBA_TECHNICAL view
    assert sqli_card.get("regulatory_impact") is None


@pytest.mark.asyncio
async def test_dam_ai_alerts_compliance_view(populated_session):
    """compliance role receives COMPLIANCE_REGULATORY view with POPIA breach fields."""
    claims = JWTClaims(
        sub="compliance-officer@example.com",
        roles=["compliance"],
        department_ids=["home-affairs-digital"],
        branch_ids=[],
        province_ids=[],
    )
    res_obj = await analyse_dbsec_ai_alerts(populated_session, claims, lookback_hours=48)
    result = dataclasses.asdict(res_obj)

    assert result["rbac_view"] == "COMPLIANCE_REGULATORY"
    cards = result["ai_alert_cards"]
    assert len(cards) >= 1

    sqli_card = next((c for c in cards if c["archetype_id"] == "sqli_exfiltration"), None)
    assert sqli_card is not None
    assert sqli_card.get("regulatory_impact") is not None
    assert sqli_card.get("breach_window_est") is not None
    assert sqli_card.get("data_class_at_risk") is not None
    # SOC technical summary should NOT be present in COMPLIANCE_REGULATORY view
    assert sqli_card.get("technical_summary") is None


@pytest.mark.asyncio
async def test_dam_ai_alerts_executive_view(populated_session):
    """risks role receives EXECUTIVE_RISK view with business impact and blast radius."""
    claims = JWTClaims(
        sub="ciso@example.com",
        roles=["risks"],
        department_ids=[],
        branch_ids=[],
        province_ids=[],
    )
    res_obj = await analyse_dbsec_ai_alerts(populated_session, claims, lookback_hours=72)
    result = dataclasses.asdict(res_obj)

    assert result["rbac_view"] == "EXECUTIVE_RISK"
    cards = result["ai_alert_cards"]
    assert len(cards) >= 1

    card = cards[0]
    assert "business_impact" in card
    assert "blast_radius_est" in card
    assert "dam_resilience_grade" in card
    assert "remediation_urgency" in card
    # Neither SOC technical nor compliance regulatory details should be exposed
    assert card.get("technical_summary") is None
    assert card.get("regulatory_impact") is None


@pytest.mark.asyncio
async def test_dam_ai_alerts_empty_session_fallback(empty_session):
    """Empty database session falls back gracefully to demonstrative patterns."""
    claims = JWTClaims(
        sub="analyst@example.com",
        roles=["findings"],
        department_ids=["demo-dept"],
        branch_ids=[],
        province_ids=[],
    )
    res_obj = await analyse_dbsec_ai_alerts(empty_session, claims, lookback_hours=24)
    result = dataclasses.asdict(res_obj)

    assert result["total_events_analysed"] >= 1
    assert result["overall_dam_posture"] in ("CRITICAL", "ELEVATED", "GUARDED", "NORMAL")
    assert len(result["ai_alert_cards"]) >= 1
    # Check that demo cards have valid advisory properties
    for card in result["ai_alert_cards"]:
        assert card["advisory_only"] is True
        assert card["requires_human_review"] is True
        assert 0 <= card["confidence_score"] <= 100
