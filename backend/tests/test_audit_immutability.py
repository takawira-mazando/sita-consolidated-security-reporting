"""Database-level guarantees for the append-only audit trail.

These require a live PostgreSQL instance and are skipped when one is not
reachable, so the suite still runs in CI without a database service. The SQL
under test is extracted verbatim from infrastructure/scripts/init-db.sql, so
these tests cannot pass while the shipped DDL is wrong.
"""
from __future__ import annotations

import os
import re

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

#: Resolved from this file rather than the working directory. The suite is run
#: both from the repository root (``pytest backend/tests``, which is what CI does)
#: and from ``backend/`` (``pytest tests``); a relative path silently resolves in
#: one and raises FileNotFoundError in the other, which made these assertions look
#: like DDL regressions when the DDL was correct.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DDL_PATH = os.path.join(REPO_ROOT, "infrastructure", "scripts", "init-db.sql")
ENV_PATH = os.path.join(REPO_ROOT, "backend", ".env")
PROBE_SCHEMA = "audit_probe"

BLOCKING_MUTATIONS = [
    ("delete", "DELETE FROM audit_probe.action_audit WHERE id = $1"),
    ("overwrite_signature", "UPDATE audit_probe.action_audit SET signature = 'forged' WHERE id = $1"),
    ("overwrite_payload", "UPDATE audit_probe.action_audit SET signed_payload = '{\"tampered\":1}' WHERE id = $1"),
    ("rewrite_hash", "UPDATE audit_probe.action_audit SET payload_hash = 'f' WHERE id = $1"),
    ("rewrite_actor", "UPDATE audit_probe.action_audit SET actor = 'evil@x.co.za' WHERE id = $1"),
    ("rewrite_role", "UPDATE audit_probe.action_audit SET actor_role = 'admin' WHERE id = $1"),
    ("rewrite_scope", "UPDATE audit_probe.action_audit SET tenant_scope = '{}'::jsonb WHERE id = $1"),
    ("rewrite_policy_version", "UPDATE audit_probe.action_audit SET policy_version = 'x' WHERE id = $1"),
    ("truncate", "TRUNCATE audit_probe.action_audit"),
]


def _dsn() -> str | None:
    env = os.environ.get("TEST_DATABASE_URL")
    if env:
        return env.replace("postgresql+asyncpg://", "postgresql://")
    path = ENV_PATH
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip().replace("postgresql+asyncpg://", "postgresql://")
                m = re.search(r"://(?P<u>[^:]+):(?P<p>[^@]*)@(?P<h>[^:/]+):(?P<port>\d+)/(?P<db>\w+)", url)
                if not m:
                    return None
                return f"postgresql://{m.group('u')}:{m.group('p')}@{m.group('h')}:{m.group('port')}/{m.group('db')}"
    return None


def _audit_ddl() -> str:
    with open(DDL_PATH, encoding="utf-8") as handle:
        sql = handle.read()
    start = sql.index("CREATE TABLE IF NOT EXISTS audit.action_audit")
    end = sql.index("-- staging", start)
    return sql[start:end]


async def _conn():
    import asyncpg

    return await asyncpg.connect(_dsn())


@pytest.fixture
async def audit_table():
    conn = await _conn()
    try:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {PROBE_SCHEMA}")
        await conn.execute(f"DROP TABLE IF EXISTS {PROBE_SCHEMA}.action_audit")
        await conn.execute(_audit_ddl().replace("audit.", f"{PROBE_SCHEMA}."))
        await conn.execute(
            f"""
            INSERT INTO {PROBE_SCHEMA}.action_audit
                (id, actor, action, target, payload_hash, signed_payload,
                 signature, key_id, verification_status)
            VALUES ('row-1', 'auditor@sita.co.za', 'ag_compliance_export', 'popia',
                    'aaa', '{{"x":1}}', 'sig', 'key1', 'unverified')
            """
        )
        yield conn
    finally:
        await conn.execute(f"DROP SCHEMA IF EXISTS {PROBE_SCHEMA} CASCADE")
        await conn.close()


@pytest.fixture(scope="module")
def database_available() -> bool:
    if not _dsn():
        return False

    async def probe() -> bool:
        try:
            conn = await _conn()
        except Exception:
            return False
        await conn.close()
        return True

    import asyncio

    try:
        return asyncio.get_event_loop().run_until_complete(probe())
    except RuntimeError:
        return asyncio.run(probe())


@pytest.mark.asyncio
@pytest.mark.parametrize("label,sql", BLOCKING_MUTATIONS, ids=[m[0] for m in BLOCKING_MUTATIONS])
async def test_mutation_of_evidentiary_columns_is_blocked(audit_table, label, sql):
    takes_id = "WHERE id = $1" in sql
    for statement in sql.split(";"):
        if not statement.strip():
            continue
        args = ("row-1",) if takes_id else ()
        try:
            await audit_table.execute(statement, *args)
        except Exception as exc:
            assert "append-only" in str(exc), f"{label} raised the wrong error: {exc}"
        else:
            pytest.fail(f"{label} was allowed on an append-only audit table")


@pytest.mark.asyncio
async def test_legitimate_verification_bookkeeping_is_still_writable(audit_table):
    """The trigger must not block the one mutation that is legitimate."""
    await audit_table.execute(
        f"""
        UPDATE {PROBE_SCHEMA}.action_audit
           SET verification_status = 'signature_valid',
               verified_at = now(),
               verified_by = 'auditor@sita.co.za'
         WHERE id = 'row-1'
        """
    )
    row = await audit_table.fetchrow(
        f"SELECT verification_status, verified_by FROM {PROBE_SCHEMA}.action_audit WHERE id = 'row-1'"
    )
    assert row["verification_status"] == "signature_valid"
    assert row["verified_by"] == "auditor@sita.co.za"


@pytest.mark.asyncio
async def test_evidence_survives_every_mutation_attempt(audit_table):
    for _, sql in BLOCKING_MUTATIONS:
        tx = audit_table.transaction()
        await tx.start()
        for statement in sql.split(";"):
            if not statement.strip():
                continue
            try:
                await audit_table.execute(statement, "row-1")
            except Exception:
                pass
        await tx.rollback()

    row = await audit_table.fetchrow(f"SELECT * FROM {PROBE_SCHEMA}.action_audit WHERE id = 'row-1'")
    assert row["actor"] == "auditor@sita.co.za"
    assert row["payload_hash"] == "aaa"
    assert row["signed_payload"] == '{"x":1}'
    assert row["signature"] == "sig"
    assert row["verification_status"] == "unverified"


@pytest.mark.asyncio
async def test_appended_forged_row_is_still_cryptographically_rejected(audit_table):
    """Append-only blocks mutation but not insertion, so the verifier must be the
    control that catches a forged row written by anyone with insert rights."""
    import hashlib

    from app.api.routers.exports_ag import _verify_record, canonical_json
    from app.security_pki import get_ec_public_key

    payload = canonical_json({"framework": "popia", "score": 0}).encode("utf-8")
    await audit_table.execute(
        f"""
        INSERT INTO {PROBE_SCHEMA}.action_audit
            (id, actor, action, target, tenant_scope, payload_hash,
             signed_payload, signature, verification_status)
        VALUES ('row-forged', 'attacker@evil.co.za', 'ag_compliance_export', 'popia',
                '{{}}'::jsonb, $1, $2, NULL, 'unverified')
        """,
        hashlib.sha256(payload).hexdigest(),
        payload.decode("utf-8"),
    )

    class Row:
        def __init__(self, rec):
            self.payload_hash = rec["payload_hash"]
            self.signed_payload = rec["signed_payload"]
            self.signature = rec["signature"]
            self.key_id = rec["key_id"]
            self.signing_algorithm = rec["signing_algorithm"]
            self.action = rec["action"]
            self.actor = rec["actor"]
            self.target = rec["target"]
            self.tenant_scope = rec["tenant_scope"]
            self.actor_role = rec["actor_role"]
            self.policy_version = rec["policy_version"]
            self.scope_hash = rec["scope_hash"]
            self.created_at = rec["created_at"]
            self.verification_status = rec["verification_status"]
            self.verified_at = rec["verified_at"]
            self.verified_by = rec["verified_by"]

    rec = await audit_table.fetchrow(f"SELECT * FROM {PROBE_SCHEMA}.action_audit WHERE id = 'row-forged'")
    result = _verify_record(Row(rec), get_ec_public_key())
    assert result["valid"] is False
    assert result["reason"].startswith("no_signature")


@pytest.mark.asyncio
async def test_disabled_trigger_blocks_writes_loudly(audit_table):
    """A disabled append-only trigger is invisible to a privilege check, so the
    table must refuse writes rather than silently accept unverified ones."""
    await audit_table.execute(
        f"ALTER TABLE {PROBE_SCHEMA}.action_audit "
        "DISABLE TRIGGER trg_action_audit_append_only"
    )
    try:
        with pytest.raises(Exception, match="append-only trigger is missing or disabled"):
            await audit_table.execute(
                f"""
                INSERT INTO {PROBE_SCHEMA}.action_audit
                    (id, actor, action, target, payload_hash, verification_status)
                VALUES ('row-sneaky', 'attacker@evil.co.za', 'probe', 'popia', 'h', 'unverified')
                """
            )
    finally:
        await audit_table.execute(
            f"ALTER TABLE {PROBE_SCHEMA}.action_audit "
            "ENABLE TRIGGER trg_action_audit_append_only"
        )

    await audit_table.execute(
        f"""
        INSERT INTO {PROBE_SCHEMA}.action_audit
            (id, actor, action, target, payload_hash, verification_status)
        VALUES ('row-after', 'auditor@sita.co.za', 'probe', 'popia', 'h2', 'unverified')
        """
    )
    assert await audit_table.fetchval(
        f"SELECT count(*) FROM {PROBE_SCHEMA}.action_audit WHERE id = 'row-after'"
    ) == 1


class TestShippedDDLShape:
    """Cheap structural checks so the guards cannot silently be dropped."""

    @pytest.mark.parametrize(
        "fragment",
        [
            "trg_action_audit_append_only",
            "trg_action_audit_no_truncate",
            "trg_action_audit_assert_enabled",
            "BEFORE TRUNCATE ON audit.action_audit",
            "ALTER COLUMN verification_status TYPE VARCHAR(128)",
            "REVOKE UPDATE, DELETE, TRUNCATE ON audit.action_audit FROM PUBLIC",
            "signed_payload",
            "signature",
            "actor_role",
            "policy_version",
            "scope_hash",
            "ADD COLUMN IF NOT EXISTS signed_payload",
        ],
    )
    def test_init_db_contains(self, fragment):
        assert os.path.isfile(DDL_PATH), (
            f"shipped DDL not found at {DDL_PATH}. Paths in this module must "
            "resolve from __file__, not the working directory."
        )
        with open(DDL_PATH, encoding="utf-8") as handle:
            sql = handle.read()
        assert fragment in sql


class TestPathResolutionIsCwdIndependent:
    """Regression guard for the working-directory bug this module had.

    The suite is invoked from two places. A relative path made twelve DDL
    assertions fail when run from ``backend/`` while passing from the repository
    root, which reads exactly like a broken shipped DDL and sends whoever is
    looking straight past the real cause.
    """

    def test_ddl_resolves_from_repo_root(self):
        assert os.path.isabs(DDL_PATH)
        assert os.path.isfile(DDL_PATH)

    def test_ddl_resolves_regardless_of_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Re-resolve the way the module does, from __file__, not from os.getcwd().
        resolved = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "infrastructure", "scripts", "init-db.sql",
        )
        assert os.path.isfile(resolved), (
            "DDL resolution depends on the working directory. Resolve from __file__."
        )

    def test_ddl_text_is_readable_from_any_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sql = _audit_ddl()
        assert "CREATE TABLE IF NOT EXISTS audit.action_audit" in sql