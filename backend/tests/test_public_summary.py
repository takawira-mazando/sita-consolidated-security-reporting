"""Tests for the public, aggregate-only /public/summary endpoint."""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.api.routers import public_summary
from app.tenant import BRANCHES, DEPARTMENTS, PROVINCES, PROVINCIAL_DEPARTMENTS
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows if rows is not None else ([] if value is None else [value])

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return _FakeScalars(self._rows)

    def all(self):
        return self._rows


class _Row:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _empty(stmt):
    sql = str(stmt)
    if "database_inventory" in sql:
        return _FakeResult(rows=[])
    if "risk_scores" in sql and "JOIN" in sql:
        return _FakeResult(rows=[])
    if "GROUP BY" in sql:
        return _FakeResult(rows=[])
    if "max(" in sql:
        return _FakeResult(value=None)
    return _FakeResult(value=0)


def _populated(stmt):
    sql = str(stmt)
    if "findings" in sql:
        if "status" in sql and "count" in sql:
            return _FakeResult(value=13)
        if "severity" in sql and "GROUP BY" in sql:
            return _FakeResult(rows=[("high", 7), ("medium", 4), ("low", 2)])
        if "max(" in sql:
            return _FakeResult(value=datetime(2026, 8, 1, 3, 15, tzinfo=timezone.utc))
        return _FakeResult(value=42)
    if "risk_scores" in sql:
        if "JOIN" in sql:
            return _FakeResult(
                rows=[
                    _Row(app_name="app-a", fused_score="92.0", bucket="critical"),
                    _Row(app_name="app-b", fused_score="88.4", bucket="monitored"),
                ]
            )
        if "distinct" in sql:
            return _FakeResult(value=5)
        if "max(" in sql:
            return _FakeResult(value=date(2026, 8, 1))
        if "bucket" in sql and "GROUP BY" in sql:
            return _FakeResult(rows=[("critical", 2), ("monitored", 3)])
        if "avg(" in sql:
            return _FakeResult(
                rows=[(date(2026, 7, 20), 72.5), (date(2026, 7, 21), 68.3)]
            )
        return _FakeResult(value=0)
    if "database_inventory" in sql:
        return _FakeResult(
            rows=[_Row(monitored=True), _Row(monitored=False)]
        )
    if "api_endpoints" in sql:
        return _FakeResult(value=7)
    if "agents" in sql:
        return _FakeResult(value=3)
    if "waf_blocks" in sql:
        return _FakeResult(value=9)
    if "connector_health" in sql:
        if "max(" in sql:
            return _FakeResult(value=None)
        return _FakeResult(rows=[("healthy", 4), ("down", 1)])
    return _FakeResult(value=0)


class _FakeSession:
    def __init__(self, dispatcher):
        self._dispatcher = dispatcher

    async def execute(self, stmt):
        return self._dispatcher(stmt)


def _make_client(dispatcher):
    app = FastAPI()
    app.include_router(public_summary.router, prefix="/api/v1")
    from app import db

    session = _FakeSession(dispatcher)
    app.dependency_overrides[db.get_session] = lambda: session
    return TestClient(app)


def test_public_summary_populated():
    client = _make_client(_populated)
    resp = client.get("/api/v1/public/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["findings"] == {
        "total": 42,
        "open": 13,
        "by_severity": {"high": 7, "medium": 4, "low": 2},
    }
    assert body["assets"] == {
        "apps": 5,
        "databases": 2,
        "monitored_databases": 1,
        "api_endpoints": 7,
        "agents": 3,
        "waf_blocks": 9,
    }
    assert body["risk"]["distribution"] == {"critical": 2, "monitored": 3}
    assert body["risk"]["latest_score_date"] == "2026-08-01"
    assert body["risk"]["trend"] == [
        {"date": "2026-07-20", "avg_score": 72.5},
        {"date": "2026-07-21", "avg_score": 68.3},
    ]
    assert body["top_risky_apps"] == [
        {"app_name": "app-a", "score": 92.0, "bucket": "critical"},
        {"app_name": "app-b", "score": 88.4, "bucket": "monitored"},
    ]
    assert body["connectors"] == {"total": 5, "healthy": 4, "degraded": 0, "down": 1}
    assert body["latest_ingest"] == "2026-08-01T03:15:00+00:00"
    assert body["tenancy"] == {
        "departments": len(DEPARTMENTS),
        "branches": len(BRANCHES),
        "provinces": len(PROVINCES),
        "provincial_departments": len(PROVINCIAL_DEPARTMENTS),
    }


def test_public_summary_empty_graceful():
    client = _make_client(_empty)
    resp = client.get("/api/v1/public/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["findings"] == {"total": 0, "open": 0, "by_severity": {}}
    assert body["assets"]["apps"] == 0
    assert body["assets"]["databases"] == 0
    assert body["assets"]["monitored_databases"] == 0
    assert body["latest_ingest"] is None
    assert body["risk"]["distribution"] == {}
    assert body["risk"]["latest_score_date"] is None
    assert body["risk"]["trend"] == []
    assert body["top_risky_apps"] == []
    assert body["connectors"] == {"total": 0, "healthy": 0, "degraded": 0, "down": 0}
