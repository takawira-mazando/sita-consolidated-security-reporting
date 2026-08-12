"""Endpoint wiring tests for the peer-benchmark and AG export routers."""
from __future__ import annotations

from app.api.auth import JWTClaims, verify_token
from app.api.routers import benchmark, exports_ag
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeResult:
    def __init__(self, rows):
        self._scalars = _FakeScalars(rows)
        self._rows = rows

    def scalars(self):
        return self._scalars

    def all(self):
        return self._rows


class _Row:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeSession:
    def __init__(self, mapping):
        self._mapping = mapping
        self.added = []

    async def execute(self, stmt):
        key = getattr(stmt, "_ag_key", None) or self._infer_key(stmt)
        return self._mapping.get(key, _FakeResult([]))

    def _infer_key(self, stmt):
        entity = next((e.entity for e in getattr(stmt, "_entities", []) if e.entity), None)
        if entity is None:
            return None
        return entity.__tablename__ if hasattr(entity, "__tablename__") else None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


def _risk_row(department_id="gp-health", app="gp-health-core", score="85.0"):
    return _Row(
        department_id=department_id,
        app_name=app,
        fused_score=score,
        signal_appscan="80.0",
        signal_imperva="90.0",
        signal_api_exposure="70.0",
        signal_compliance_penalty="60.0",
    )


def _snapshot_row():
    from datetime import date
    return _Row(
        framework="popia",
        snapshot_date=date(2026, 7, 31),
        overall_score="84.0",
        passed_controls=18,
        total_controls=20,
        details={"consent": 76},
    )


def _gap_row():
    return _Row(
        framework="popia",
        status="open",
        severity="high",
        domain="consent",
    )


def _fake_rows_for(stmt):
    """Return fake DB rows appropriate for the statement's target table."""
    from app.models.audit import ActionAudit
    from app.models.compliance import ComplianceGap, ComplianceSnapshot
    from app.models.risk_score import RiskScore
    target = None
    for f in getattr(stmt, "froms", []):
        tablename = getattr(f, "name", None)
        if tablename == RiskScore.__tablename__:
            target = RiskScore
        elif tablename == ComplianceSnapshot.__tablename__:
            target = ComplianceSnapshot
        elif tablename == ComplianceGap.__tablename__:
            target = ComplianceGap
        elif tablename == ActionAudit.__tablename__:
            target = ActionAudit
    if target is RiskScore:
        return [_risk_row(), _risk_row("wc-health", "wc-health-core", "60.0")]
    if target is ComplianceSnapshot:
        return [_snapshot_row()]
    if target is ComplianceGap:
        return [_gap_row(), _gap_row()]
    return []


class _MappingSession:
    def __init__(self):
        self.added = []

    async def execute(self, stmt):
        return _FakeResult(_fake_rows_for(stmt))

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        return None


def _make_client(router, session, claims):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    from app import db
    app.dependency_overrides[db.get_session] = lambda: session

    async def _claims():
        return claims

    app.dependency_overrides[verify_token] = _claims
    return TestClient(app)


def test_province_benchmark_endpoint_scoped():
    claims = JWTClaims(sub="u1", email="soc@gp.example.com", roles=["province-soc-lead"], province_ids=["gp"])
    client = _make_client(benchmark.router, _MappingSession(), claims)
    resp = client.get("/api/v1/benchmark/province")
    assert resp.status_code == 200
    body = resp.json()
    assert body["viewer"] == "province"
    assert body["scope"]["provinces"] == ["gp"]
    assert body["own"]["province_id"] == "gp"
    peers = [e for e in body["leaderboard"] if not e["is_you"]]
    assert all(e["label"].startswith("Peer Province") for e in peers)
    assert all(e["province_id"] is None for e in peers)


def test_province_benchmark_national_unblinded():
    claims = JWTClaims(sub="u1", email="exec@example.com", roles=["exec"])
    client = _make_client(benchmark.router, _MappingSession(), claims)
    resp = client.get("/api/v1/benchmark/province")
    assert resp.status_code == 200
    body = resp.json()
    assert body["viewer"] == "national"
    assert all(e["province_id"] for e in body["leaderboard"])


def test_benchmark_requires_auth():
    app = FastAPI()
    app.include_router(benchmark.router, prefix="/api/v1")
    client = TestClient(app)
    resp = client.get("/api/v1/benchmark/province")
    assert resp.status_code == 401


def test_ag_export_writes_audit_row_with_hash():
    session = _MappingSession()
    claims = JWTClaims(sub="u1", email="compliance@example.com", roles=["compliance"])
    client = _make_client(exports_ag.router, session, claims)
    resp = client.post("/api/v1/exports/ag-compliance")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["integrity_hash"]) == 64
    assert body["verify_url"].endswith(body["integrity_hash"])
    assert body["attestation"]["scope"]["type"] == "estate"
    assert body["attestation"]["snapshot"]["overall_score"] == 84.0
    assert len(session.added) == 1
    audit = session.added[0]
    assert audit.action == "ag_compliance_export"
    assert audit.actor == "compliance@example.com"
    assert audit.payload_hash == body["integrity_hash"]


def test_ag_export_province_scope():
    session = _MappingSession()
    claims = JWTClaims(sub="u1", email="admin@gp.example.com", roles=["province-dept-admin"], province_ids=["gp"])
    client = _make_client(exports_ag.router, session, claims)
    resp = client.post("/api/v1/exports/ag-compliance")
    assert resp.status_code == 200
    body = resp.json()
    assert body["attestation"]["scope"]["type"] == "province"
    assert body["attestation"]["scope"]["provinces"] == ["Gauteng"]


def test_ag_export_verify_missing_hash():
    claims = JWTClaims(sub="u1", email="compliance@example.com", roles=["compliance"])
    client = _make_client(exports_ag.router, _MappingSession(), claims)
    resp = client.get("/api/v1/exports/ag-compliance/verify/abc")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
