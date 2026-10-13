"""Tests for the access-audit control (gap G-10).

Before this control the only writer to ``audit.action_audit`` was the
Auditor-General export engine, so the platform could not answer "who accessed
what personal data, in which tenancy scope, and when".

These tests pin the three properties that make the control trustworthy:

1. A record is written, signed and bound to the scope in force.
2. A record is never dropped — a signing failure degrades it, it does not
   discard it.
3. A record can never contain a secret.
"""
from __future__ import annotations

import pytest
from app.monitoring import access_audit
from app.monitoring.access_audit import (
    ACCESS_POLICY_VERSION,
    REDACTION_MARKER,
    record_access,
    redact,
    scope_digest,
)


class _FakeSession:
    """Captures appended rows so assertions can inspect what was written."""

    def __init__(self, fail_on_add: bool = False, fail_on_commit: bool = False):
        self.rows = []
        self.fail_on_add = fail_on_add
        self.fail_on_commit = fail_on_commit

    def add(self, obj):
        if self.fail_on_add:
            raise RuntimeError("simulated add failure")
        self.rows.append(obj)

    async def commit(self):
        if self.fail_on_commit:
            raise RuntimeError("simulated commit failure")

    async def rollback(self):
        pass


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["password", "user_password", "Password", "api_key", "apikey", "secret",
     "token", "access_token", "Authorization", "routing_key", "private_key",
     "credential"],
)
def test_secret_looking_keys_are_redacted(key):
    assert redact({key: "super-secret-value"})[key] == REDACTION_MARKER


def test_redaction_recurses_into_nested_structures():
    detail = {
        "outer": {"inner": [{"password": "hunter2"}, {"safe": "keep"}]},
        "password": "top-level",
    }
    result = redact(detail)
    assert result["outer"]["inner"][0]["password"] == REDACTION_MARKER
    assert result["outer"]["inner"][1]["safe"] == "keep"
    assert result["password"] == REDACTION_MARKER


def test_redaction_leaves_ordinary_detail_intact():
    detail = {"row_count": 12, "src_ip": "198.51.100.7", "dataset": "findings"}
    assert redact(detail) == detail


# --------------------------------------------------------------------------
# recording
# --------------------------------------------------------------------------


async def test_record_access_writes_a_signed_row():
    session = _FakeSession()
    await record_access(
        session,
        action="data.read.persons",
        actor="admin@example.com",
        target="persons",
        tenant_scope={"department_ids": ["treasury"], "branch_ids": [], "province_ids": []},
        actor_role="admin",
        scope_hash=scope_digest(["treasury"], [], [], ["admin"]),
        detail={"rows_returned": 50},
    )

    assert len(session.rows) == 1
    row = session.rows[0]
    assert row.actor == "admin@example.com"
    assert row.action == "data.read.persons"
    assert row.policy_version == ACCESS_POLICY_VERSION
    assert row.verification_status == "unverified"
    # Signed: a signature and key id are present, so the record can be verified
    # offline rather than trusted on the strength of the database row.
    assert row.signature
    assert row.key_id
    assert row.signing_algorithm
    assert row.payload_hash and len(row.payload_hash) == 64


async def test_record_access_never_persists_a_secret():
    session = _FakeSession()
    await record_access(
        session,
        action="auth.login",
        actor="admin@example.com",
        detail={"password": "hunter2", "api_key": "AKIA-example"},
    )
    signed = session.rows[0].signed_payload
    assert "hunter2" not in signed
    assert "AKIA-example" not in signed
    assert REDACTION_MARKER in signed


async def test_record_access_is_idempotent_for_hash_stability():
    """Same inputs produce the same payload hash, so records are diffable."""
    session = _FakeSession()
    kwargs = dict(
        action="export.csv",
        actor="soc@example.com",
        target="findings",
        detail={"dataset": "findings", "row_count": 12},
    )
    await record_access(session, **kwargs)
    await record_access(session, **kwargs)
    assert session.rows[0].payload_hash == session.rows[1].payload_hash


async def test_signing_failure_degrades_instead_of_dropping(monkeypatch):
    """A record must survive a broken signing key.

    Losing the row is the exact failure mode this control exists to prevent,
    so the row is written unsigned and flagged for follow-up.
    """
    def _boom(_payload):
        raise RuntimeError("no signing key available")

    monkeypatch.setattr(access_audit, "sign_canonical_payload", _boom)
    session = _FakeSession()
    await record_access(session, action="auth.login", actor="a@example.com")

    assert len(session.rows) == 1, "record must not be dropped when signing fails"
    assert session.rows[0].verification_status == "unsigned"
    assert session.rows[0].signature is None
    assert session.rows[0].payload_hash


async def test_database_failure_never_raises_into_the_request():
    """An audit defect must not deny a legitimate security operation."""
    session = _FakeSession(fail_on_add=True)
    await record_access(session, action="auth.login", actor="a@example.com")

    session = _FakeSession(fail_on_commit=True)
    await record_access(session, action="auth.login", actor="a@example.com")


# --------------------------------------------------------------------------
# scope digest
# --------------------------------------------------------------------------


def test_scope_digest_is_order_independent():
    assert scope_digest(["b", "a"], [], [], ["soc"]) == scope_digest(
        ["a", "b"], [], [], ["soc"]
    )


def test_scope_digest_changes_when_authority_changes():
    baseline = scope_digest(["treasury"], [], [], ["soc"])
    assert baseline != scope_digest(["treasury"], [], [], ["admin"])
    assert baseline != scope_digest(["treasury", "dpsa-hr"], [], [], ["soc"])
    assert baseline != scope_digest(["treasury"], ["treasury-cash"], [], ["soc"])


# --------------------------------------------------------------------------
# endpoint wiring
# --------------------------------------------------------------------------


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


class _ExportSession(_FakeSession):
    def __init__(self, rows, **kw):
        super().__init__(**kw)
        self._rows = rows

    async def execute(self, stmt):
        return _FakeResult(list(self._rows))


class _Finding:
    id = "f1"
    source = "appscan"
    external_id = "ASC-1"
    app_name = "payment-gateway"
    severity = "critical"
    title = "A03 injection"
    category = "injection"
    status = "open"
    first_seen = "2026-01-01 00:00:00"
    last_seen = "2026-01-02 00:00:00"


class _Alert:
    id = "a1"
    rule_id = "critical_record"
    title = "WAF block spike"
    severity = "critical"
    source = "imperva"
    target_id = "payment-gateway"
    status = "new"
    first_triggered = "2026-01-01 00:00:00"
    last_triggered = "2026-01-02 00:00:00"


EXPORT_ROWS = [_Finding()]
ALERT_ROWS = [_Alert()]


def _claims():
    from app.api.auth import JWTClaims

    return JWTClaims(
        sub="u1",
        email="soc@example.com",
        roles=["soc"],
        department_ids=["home-affairs-digital"],
        branch_ids=[],
        province_ids=[],
    )


async def test_csv_export_records_an_audit_row():
    """A bulk egress must leave a signed, scoped record naming the dataset."""
    from app.api.routers import exports

    session = _ExportSession(EXPORT_ROWS)
    await exports.export_findings(_FakeRequest(), session, _claims())

    rows = [r for r in session.rows if r.action == "export.csv"]
    assert len(rows) == 1
    row = rows[0]
    assert row.actor == "soc@example.com"
    assert row.target == "findings"
    assert row.signature and row.key_id
    assert row.policy_version == ACCESS_POLICY_VERSION
    # The release size and the scope it was released under are both recorded,
    # so a routine extract is distinguishable from a full-estate dump.
    assert '"row_count":1' in row.signed_payload
    assert row.tenant_scope["department_ids"] == ["home-affairs-digital"]


async def test_csv_export_audit_records_the_source_address():
    from app.api.routers import exports

    session = _ExportSession(ALERT_ROWS)
    request = _FakeRequest(src_ip="203.0.113.9")
    await exports.export_alerts(request, session, _claims())

    rows = [r for r in session.rows if r.action == "export.csv"]
    assert len(rows) == 1
    assert '"src_ip":"203.0.113.9"' in rows[0].signed_payload


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    """Minimal stand-in for starlette's Request, covering request_context()."""

    def __init__(self, src_ip: str = "198.51.100.7"):
        self.client = _FakeClient(src_ip)
        self.headers = _FakeHeaders({"user-agent": "pytest"})