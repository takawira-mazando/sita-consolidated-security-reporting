"""Tests for the AlertRuleEngine and AlertEnricher (rules + enrichment)."""
from __future__ import annotations

import asyncio

import pytest
from app.processing.alert_engine import AlertRuleEngine
from app.processing.alert_enricher import AlertEnricher


@pytest.fixture(scope="module")
def engine() -> AlertRuleEngine:
    return AlertRuleEngine()


def _run(coro):
    return asyncio.run(coro)


def test_rules_loaded(engine):
    assert len(engine.rules) >= 6
    ids = {rule["id"] for rule in engine.rules}
    assert {"critical_record", "high_imperva_dam", "appscan_high", "risk_critical", "shadow_api", "compliance_drop"} <= ids


def test_record_rule_fires_critical(engine):
    context = {
        "source": "appscan",
        "severity": "critical",
        "app_name": "payment-gateway",
        "external_id": "ASC-1",
        "title": "A03 injection",
    }
    alerts = _run(engine.evaluate(context))
    assert alerts
    assert any(a["rule_id"] == "critical_record" for a in alerts)
    assert all(a["severity"] == "critical" for a in alerts)


def test_record_rule_throttle_window(engine):
    context = {"source": "appscan", "severity": "critical", "app_name": "legacy-api"}
    fired = 0
    for _ in range(7):
        alerts = _run(engine.evaluate(context))
        fired += 1 if any(a["rule_id"] == "critical_record" for a in alerts) else 0
    # critical_record allows max 5 alerts per 60min window, then suppresses
    assert fired == 5


def test_record_rule_appscan_high(engine):
    context = {"source": "appscan", "severity": "high", "app_name": "customer-portal"}
    alerts = _run(engine.evaluate(context))
    assert any(a["rule_id"] == "appscan_high" for a in alerts)


def test_high_imperva_requires_dam_source(engine):
    alerts = _run(engine.evaluate({"source": "appscan", "severity": "high"}))
    assert not any(a["rule_id"] == "high_imperva_dam" for a in alerts)
    alerts = _run(engine.evaluate({"source": "imperva_dam", "severity": "high"}))
    assert any(a["rule_id"] == "high_imperva_dam" for a in alerts)


def test_alert_fields_complete(engine):
    alert = _run(engine.evaluate(
        {"source": "imperva_dam", "severity": "critical", "app_name": "DB-CUST-01", "title": "unauth"}
    ))[0]
    for field in ["id", "rule_id", "title", "severity", "source", "target_id", "status", "dedup_key",
                  "first_triggered", "last_triggered"]:
        assert alert.get(field) is not None, f"missing {field}"


def test_record_alert_preserves_tenant_tier_scope(engine):
    alert = engine._build_alert(
        {"id": "test", "severity": "high"},
        {
            "tenant_workspace_id": "workspace-a",
            "tenant_scope_level_key": "branch",
        },
    )

    assert alert["tenant_workspace_id"] == "workspace-a"
    assert alert["tenant_scope_level_key"] == "branch"


def test_alert_throttling_is_isolated_by_tenant_and_tier():
    deduplicator = AlertRuleEngine().deduplicator
    workspace_a = deduplicator._make_key(
        "critical_record", "appscan", "portal", "critical", "workspace-a", "branch"
    )
    workspace_b = deduplicator._make_key(
        "critical_record", "appscan", "portal", "critical", "workspace-b", "branch"
    )
    department = deduplicator._make_key(
        "critical_record", "appscan", "portal", "critical", "workspace-a", "department"
    )

    assert workspace_a != workspace_b
    assert workspace_a != department


def test_aggregate_rules_exclude_tenant_scoped_records(engine):
    scoped_tables = {
        "warehouse.risk_scores",
        "warehouse.findings",
        "warehouse.api_endpoints",
        "warehouse.compliance_snapshots",
    }
    for rule in engine.rules:
        condition = rule.get("condition", {})
        query = condition.get("query") or condition.get("base_query") or ""
        if any(table in query for table in scoped_tables):
            assert "tenant_workspace_id IS NULL" in query


def test_enricher_app_owner_lookup():
    enricher = AlertEnricher()
    alert = enricher.enrich({
        "id": "a1", "rule_id": "critical_record", "title": "t", "severity": "critical",
        "source": "appscan", "target_id": "payment-gateway",
    })
    assert alert["owner"] == "Payment Ops"
    assert alert["team"] == "Payments"
    assert alert["priority"] == 1
    assert alert["dashboard_link"] == "/alerts/a1"


def test_enricher_fallback():
    enricher = AlertEnricher()
    alert = enricher.enrich({"id": "a2", "severity": "info", "target_id": "unknown-app"})
    assert alert["owner"] == "Unassigned"
    assert alert["priority"] == 5
