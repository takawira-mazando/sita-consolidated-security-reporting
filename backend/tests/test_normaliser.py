"""Tests for the config-driven Normaliser against OEM-shaped fixtures."""
from __future__ import annotations

import pandas as pd
import pytest
from app.processing.normaliser import Normaliser
from tests.fixtures import load_all_fixtures, load_fixture


@pytest.fixture(scope="module")
def normaliser() -> Normaliser:
    return Normaliser()


@pytest.mark.parametrize("source", ["appscan", "imperva_dam", "imperva_waf", "apisec", "compliance"])
def test_normalise_produces_canonical_columns(normaliser, source):
    records = load_fixture(source)
    df = normaliser.normalise(pd.DataFrame(records), source)
    assert not df.empty
    for col in ["external_id", "app_name", "severity", "title", "first_seen", "last_seen"]:
        assert col in df.columns, f"{source}: missing column {col}"
    assert not df["external_id"].isna().any()


def test_normalise_all_fixtures(normaliser):
    fixtures = load_all_fixtures()
    for source, records in fixtures.items():
        df = normaliser.normalise(pd.DataFrame(records), source)
        assert len(df) == len(records), f"{source}: lost records during normalise"


def test_appscan_severity_mapping(normaliser):
    records = [
        {"id": "1", "application_name": "legacy-api", "vulnerability_name": "x",
         "owasp_category": "A03", "severity": "4 - Critical", "status": "Open",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
        {"id": "2", "application_name": "legacy-api", "vulnerability_name": "y",
         "owasp_category": "A03", "severity": "Informational", "status": "Open",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
    ]
    df = normaliser.normalise(pd.DataFrame(records), "appscan")
    sev = df["severity"].tolist()
    assert sev == ["critical", "info"]


def test_imperva_severity_mapping(normaliser):
    records = [
        {"event_id": "D1", "database_name": "DB-1", "rule_name": "r", "attack_type": "sqli",
         "violation_type": "sql_injection", "severity": "Emergency", "timestamp": "2026-01-01T00:00:00Z"},
        {"event_id": "D2", "database_name": "DB-1", "rule_name": "r", "attack_type": "sqli",
         "violation_type": "sql_injection", "severity": "Info", "timestamp": "2026-01-01T00:00:00Z"},
    ]
    df = normaliser.normalise(pd.DataFrame(records), "imperva_dam")
    assert df["severity"].tolist() == ["critical", "info"]


def test_apisec_exposure_based_severity(normaliser):
    records = [
        {"api_id": "A1", "application": "payment-gateway", "endpoint": "/api/v1/pay", "method": "POST",
         "exposure_score": 90, "is_shadow": True, "issue_type": "auth_missing",
         "exposure_notes": "n", "discovered_at": "2026-01-01", "last_active": "2026-01-01"},
        {"api_id": "A2", "application": "payment-gateway", "endpoint": "/api/v1/pay", "method": "GET",
         "exposure_score": 30, "is_shadow": False, "issue_type": "rate_limit",
         "exposure_notes": "n", "discovered_at": "2026-01-01", "last_active": "2026-01-01"},
    ]
    df = normaliser.normalise(pd.DataFrame(records), "apisec")
    assert df["severity"].tolist() == ["critical", "medium"]


def test_compliance_fields(normaliser):
    records = [
        {"framework": "popia", "control_id": "POPIA-1", "domain": "Consent",
         "description": "d", "owner": "DPO", "severity": "high",
         "due_date": "2026-06-01", "status": "open", "evidence_count": 2}
    ]
    df = normaliser.normalise(pd.DataFrame(records), "compliance")
    row = df.iloc[0]
    assert row["severity"] == "high"
    assert row["external_id"] == "POPIA-1"
    assert row["app_name"] == "popia"


def test_window_dedup_same_status_suppressed(normaliser):
    records = [
        {"id": "1", "application_name": "legacy-api", "vulnerability_name": "x",
         "owasp_category": "A03", "severity": "3 - High", "status": "Open",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
    ]
    existing = {"1": {"status": "Open", "last_seen": "2026-01-02"}}

    def lookup(records):
        return {r["external_id"]: existing.get(r["external_id"], {}) for r in records}

    df = normaliser.normalise(pd.DataFrame(records), "appscan", lookup=lookup)
    assert df.empty


def test_window_dedup_status_change_kept(normaliser):
    records = [
        {"id": "1", "application_name": "legacy-api", "vulnerability_name": "x",
         "owasp_category": "A03", "severity": "3 - High", "status": "Fixed",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
    ]
    existing = {"1": {"status": "Open"}}

    def lookup(records):
        return {r["external_id"]: existing.get(r["external_id"], {}) for r in records}

    df = normaliser.normalise(pd.DataFrame(records), "appscan", lookup=lookup)
    assert not df.empty
    assert df.iloc[0]["status"] == "Fixed"


def test_in_batch_dedup(normaliser):
    records = [
        {"id": "1", "application_name": "legacy-api", "vulnerability_name": "x",
         "owasp_category": "A03", "severity": "3 - High", "status": "Open",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
        {"id": "1", "application_name": "legacy-api", "vulnerability_name": "x",
         "owasp_category": "A03", "severity": "4 - Critical", "status": "Open",
         "first_found_date": "2026-01-01", "last_found_date": "2026-01-02"},
    ]
    df = normaliser.normalise(pd.DataFrame(records), "appscan")
    assert len(df) == 1
    assert df.iloc[0]["severity"] == "critical"
