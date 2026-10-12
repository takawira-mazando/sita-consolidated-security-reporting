-- ============================================================================
-- audit-role-split.sql
--
-- Closes the audit.action_audit ownership gap: the application role currently
-- OWNS the table, and a PostgreSQL owner can always DISABLE or DROP its
-- triggers, so REVOKE alone does not make the trail append-only against a
-- privileged insider.
--
-- MUST be run as a superuser (postgres or takawira on this instance).
-- The sita role cannot run this: it has neither SUPERUSER nor CREATEROLE.
--
--   psql -h localhost -p 5432 -U postgres -d sita -v ON_ERROR_STOP=1 \
--        -f infrastructure/scripts/audit-role-split.sql
--
-- Idempotent. Safe to re-run.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- Sanity: refuse to run with insufficient rights rather than half-applying.
DO $$
BEGIN
    IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
        RAISE EXCEPTION
            'must be run as a superuser; current_user=% is not a superuser',
            current_user;
    END IF;
END
$$;

-- ----------------------------------------------------------------------------
-- 1. Break-glass owner role. NOLOGIN: exists only to own the table so that no
--    human or application can connect as it.
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sita_audit') THEN
        CREATE ROLE sita_audit NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

-- ----------------------------------------------------------------------------
-- 2. Runtime role. This is what the application connects as.
--    Password is NOT set here - set it separately and pass it in, so the secret
--    never lands in a file under version control:
--      psql ... -v app_password='<secret>' -f audit-role-split.sql
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sita_app') THEN
        CREATE ROLE sita_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

-- Set the runtime password separately, so the secret is never stored in a file:
--   psql -h localhost -p 5432 -U postgres -d sita \
--        -v app_password='<secret>' \
--        -c "ALTER ROLE sita_app PASSWORD :'app_password';"
-- (Run that once, after this script.)

-- ----------------------------------------------------------------------------
-- 3. Transfer ownership. This is the step that actually closes the gap:
--    after this, the application role can no longer DROP or DISABLE the guards,
--    because it is no longer the owner.
-- ----------------------------------------------------------------------------
ALTER TABLE audit.action_audit OWNER TO sita_audit;

-- ----------------------------------------------------------------------------
-- 4. Least privilege for both roles. Explicit ACLs only - no reliance on
--    inherited owner rights.
--
--    UPDATE is granted at COLUMN level, not table level. The append-only
--    trigger permits exactly one legitimate mutation: recording verification
--    bookkeeping. GET /api/v1/exports/ag-compliance/verify/{hash} performs
--    that write (app/api/routers/exports_ag.py). A blanket
--    "REVOKE UPDATE ... FROM sita" would therefore break that endpoint, while a
--    blanket GRANT would leave the other fourteen evidentiary columns writable
--    at the ACL layer and rely on the trigger alone.
--
--    Column-level privilege means the fourteen evidentiary columns stay
--    unwritable by both roles regardless of trigger state.
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA audit TO sita_app;
GRANT INSERT, SELECT ON audit.action_audit TO sita_app;
REVOKE UPDATE, DELETE, TRUNCATE ON audit.action_audit FROM sita_app;
GRANT UPDATE (verification_status, verified_at, verified_by)
    ON audit.action_audit TO sita_app;

GRANT INSERT, SELECT ON audit.action_audit TO sita;
REVOKE UPDATE, DELETE, TRUNCATE ON audit.action_audit FROM sita;
GRANT UPDATE (verification_status, verified_at, verified_by)
    ON audit.action_audit TO sita;

-- The guard functions must also be owned by the break-glass role, otherwise the
-- application role could replace a guard body with a no-op via CREATE OR REPLACE.
ALTER FUNCTION audit.action_audit_append_only()  OWNER TO sita_audit;
ALTER FUNCTION audit.action_audit_assert_enabled() OWNER TO sita_audit;
ALTER FUNCTION audit.action_audit_no_truncate()   OWNER TO sita_audit;

COMMIT;

-- ----------------------------------------------------------------------------
-- Verification. Each block must report the stated result.
-- ----------------------------------------------------------------------------
\echo ''
\echo '=== ownership ==='
SELECT pg_get_userbyid(relowner) AS owner,
       coalesce(relacl::text, '(no ACL)') AS acl
  FROM pg_class
 WHERE oid = 'audit.action_audit'::regclass;

\echo ''
\echo '=== guards present and enabled (all three must be O) ==='
SELECT tgname || '=' || tgenabled::text AS state
  FROM pg_trigger
 WHERE tgrelid = 'audit.action_audit'::regclass AND NOT tgisinternal
 ORDER BY tgname;

\echo ''
\echo '=== application role privileges (UPDATE/DELETE/TRUNCATE must be absent) ==='
SELECT grantee, privilege_type
  FROM information_schema.role_table_grants
  WHERE table_schema = 'audit' AND table_name = 'action_audit'
    AND grantee IN ('sita', 'sita_app')
  ORDER BY grantee, privilege_type;

\echo ''
\echo '=== column-level UPDATE (must be verification_status/verified_at/verified_by only) ==='
SELECT grantee, column_name
  FROM information_schema.column_table_privileges
 WHERE table_schema = 'audit' AND table_name = 'action_audit'
   AND privilege_type = 'UPDATE' AND grantee IN ('sita', 'sita_app')
 ORDER BY grantee, column_name;

\echo ''
\echo 'Next: repoint the application at sita_app'
\echo '  DATABASE_URL=postgresql+asyncpg://sita_app:<secret>@localhost:5432/sita'
\echo 'Then confirm the app can no longer tamper, as sita_app:'
\echo '  ALTER TABLE audit.action_audit DISABLE TRIGGER ALL;  -- must ERROR'