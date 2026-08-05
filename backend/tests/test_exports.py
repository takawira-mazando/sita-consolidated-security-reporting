"""Tests for the CSV export endpoints (findings, risk scores, alerts)."""
from __future__ import annotations

import pytest
from app.api.auth import JWTClaims, verify_token
from app.api.routers import exports
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._scalars = _FakeScalars(rows)

    def scalars(self):
        return self._scalars


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, stmt):
        return _FakeResult(self._rows)


class _Row:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _make_finding(i):
    return _Row(
        id=f"f{i}", source="appscan", external_id=f"ASC-{i}", app_name="payment-gateway",
        severity="critical", title="A03 injection", category="injection", status="open",
        first_seen="2026-01-01 00:00:00", last_seen="2026-01-02 00:00:00",
    )


def _make_risk(i):
    return _Row(
        id=f"r{i}", app_name="payment-gateway", score_date="2026-01-02", fused_score="85.0",
        signal_appscan="80.0", signal_imperva="90.0", signal_api_exposure="70.0",
        signal_compliance_penalty="60.0", bucket="critical",
    )


def _make_alert(i):
    return _Row(
        id=f"a{i}", rule_id="critical_record", title="t", severity="critical",
        source="appscan", target_id="payment-gateway", status="new",
        first_triggered="2026-01-01 00:00:00", last_triggered="2026-01-02 00:00:00",
    )


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(exports.router, prefix="/api/v1")
    return application


def _client_with(app, session):
    app.dependency_overrides[exports.get_session] = lambda: session
    return TestClient(app)


def test_export_findings_csv():
    app = FastAPI()
    app.include_router(exports.router, prefix="/api/v1")
    client = _client_with(app, _FakeSession([_make_finding(1)]))
    resp = client.get("/api/v1/exports/findings.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.splitlines()
    assert lines[0].startswith("id,source,external_id")
    assert "ASC-1" in lines[1]


def test_export_risk_scores_csv():
    app = FastAPI()
    app.include_router(exports.router, prefix="/api/v1")

    async def _admin_claims():
        return JWTClaims(sub="admin", email="admin@localhost", roles=["admin"])

    app.dependency_overrides[verify_token] = _admin_claims
    client = _client_with(app, _FakeSession([_make_risk(1)]))
    resp = client.get("/api/v1/exports/risk-scores.csv")
    assert resp.status_code == 200
    assert resp.text.splitlines()[0].startswith("id,app_name,score_date")
    assert "payment-gateway" in resp.text


def test_export_alerts_csv():
    app = FastAPI()
    app.include_router(exports.router, prefix="/api/v1")
    client = _client_with(app, _FakeSession([_make_alert(1)]))
    resp = client.get("/api/v1/exports/alerts.csv")
    assert resp.status_code == 200
    assert resp.text.splitlines()[0].startswith("id,rule_id,title")
    assert "critical_record" in resp.text
