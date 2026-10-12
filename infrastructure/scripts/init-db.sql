-- ============================================================================
-- SITA Security Intelligence Platform — Full Database Schema
-- ============================================================================
-- PostgreSQL 15+. Idempotent (safe to re-run). Mirrors backend/app/models/*.py.
--
-- Schemas:
--   identity  - RBAC users (JWT auth)
--   staging   - raw OEM ingestion buffers (batch_runs, raw_records, DLQ)
--   warehouse - canonical analytics tables consumed by REST API / dashboards
--   archive   - LIKE-copies of hot warehouse tables (maintenance rotation)
--   audit     - reserved for future immutable audit trails
--
-- Dependencies:
--   - pg_stat_statements extension (optional, for observability)
--   - pg_cron jobs are defined separately in maintenance.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS archive;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS identity;

-- ============================================================================
-- identity
-- ============================================================================

CREATE TABLE IF NOT EXISTS identity.users (
    id            VARCHAR(36) PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(100),
    roles         JSONB NOT NULL DEFAULT '["soc"]'::jsonb,
    department_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    branch_ids    JSONB NOT NULL DEFAULT '[]'::jsonb,
    province_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,
    person_id     VARCHAR(36),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON identity.users(email);
CREATE INDEX IF NOT EXISTS idx_users_person ON identity.users(person_id);

CREATE TABLE IF NOT EXISTS identity.persons (
    id               VARCHAR(36) PRIMARY KEY,
    employee_number  VARCHAR(50) UNIQUE,
    email            VARCHAR(255) UNIQUE,
    id_number        VARCHAR(20),
    title            VARCHAR(20),
    initials         VARCHAR(20),
    surname          VARCHAR(100),
    display_name     VARCHAR(100),
    job_title        VARCHAR(120),
    org_unit         VARCHAR(120),
    department_id    VARCHAR(36),
    branch_id        VARCHAR(36),
    manager_id       VARCHAR(36),
    manager_name     VARCHAR(120),
    work_phone       VARCHAR(30),
    location         VARCHAR(120),
    employment_status VARCHAR(30) NOT NULL DEFAULT 'active',
    clearance_level  VARCHAR(30),
    source           VARCHAR(20) NOT NULL DEFAULT 'hr',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- identity.persons.id_number is AES-256-GCM encrypted at rest by the
-- application (app/pii_crypto.py), not by a database extension: pgcrypto is not
-- shipped with the EDB Windows PostgreSQL build and the application role is not
-- a superuser, so CREATE EXTENSION is unavailable.
--
-- The column is TEXT rather than VARCHAR(20) because the stored form is an
-- envelope (v1:<nonce>:<ciphertext>), not a 13-digit string. Encryption and
-- decryption happen transparently in a SQLAlchemy TypeDecorator, so the stored
-- value is ciphertext while every read path still sees plaintext.
ALTER TABLE identity.persons
    ALTER COLUMN id_number TYPE TEXT;

CREATE INDEX IF NOT EXISTS idx_persons_employee ON identity.persons(employee_number);
CREATE INDEX IF NOT EXISTS idx_persons_email ON identity.persons(email);
CREATE INDEX IF NOT EXISTS idx_persons_dept ON identity.persons(department_id);
CREATE INDEX IF NOT EXISTS idx_persons_status ON identity.persons(employment_status);

-- Scheme-qualified external employment identifiers.
--
-- Replaces reliance on persons.employee_number alone. The platform must
-- distinguish the South African public service's three identifier concepts:
--
--   persal        8 digits, issued by National Treasury via PERSAL, bound to
--                 the EMPLOYMENT record (a transfer keeps it, a resignation
--                 and reappointment yields a new one)
--   sap_personnel SITA's own SAP HCM estate, and the scheme the IFMS HR module
--                 (DPSA / National Treasury / SITA, payroll excluded) will
--                 carry nationally
--   internal_hr   feeds carrying no national scheme, including the simulated
--                 HR stand-in
--
-- The SA identity number is deliberately NOT modelled here: it identifies the
-- person, not the employment, and is retained only on persons.id_number under
-- the masking controls in app/pii.py.
--
-- identity.users.person_id remains an internal UUID. A government identifier
-- is an attribute of an account, never its primary key, so a corrected or
-- reissued PERSAL number does not require re-keying an account.
CREATE TABLE IF NOT EXISTS identity.employment_identifier (
    id            VARCHAR(36) PRIMARY KEY,
    person_id     VARCHAR(36) NOT NULL REFERENCES identity.persons(id) ON DELETE CASCADE,
    scheme        VARCHAR(32) NOT NULL,
    value         VARCHAR(64) NOT NULL,
    source_system VARCHAR(64),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_employment_identifier_scheme_value UNIQUE (scheme, value)
);
CREATE INDEX IF NOT EXISTS idx_employment_identifier_person ON identity.employment_identifier(person_id);
CREATE INDEX IF NOT EXISTS idx_employment_identifier_scheme ON identity.employment_identifier(scheme);
CREATE INDEX IF NOT EXISTS idx_employment_identifier_value ON identity.employment_identifier(value);

-- Idempotent backfill: every person provisioned so far carries the originating
-- feed's own identifier. Existing values are synthetic (EMP-...), so they land
-- under internal_hr; a genuine 8-digit PERSAL number would classify as persal.
INSERT INTO identity.employment_identifier (id, person_id, scheme, value, source_system)
SELECT gen_random_uuid()::TEXT,
       p.id,
       CASE
           WHEN p.employee_number ~ '^[0-9]{8}$' THEN 'persal'
           ELSE 'internal_hr'
       END,
       p.employee_number,
       'backfill'
  FROM identity.persons p
 WHERE p.employee_number IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM identity.employment_identifier ei
        WHERE ei.person_id = p.id
          AND ei.value = p.employee_number
   );

-- ============================================================================
-- hr - SIMULATED EXTERNAL HR SYSTEM (PERSAL/payroll employee master)
-- ============================================================================
-- Stands in for SITA's real HR system so the HR -> identity.persons ->
-- platform account pipeline can be exercised end-to-end without a live
-- PERSAL/SCIM feed. It is a SEPARATE logical system: the platform only reads
-- it via the sim endpoints (/admin/hr/sim/*) and never treats it as the
-- identity source of truth. Department/branch codes use the SITA tenancy
-- slugs so the sync validation and tenant scoping apply unchanged.

CREATE SCHEMA IF NOT EXISTS hr;

CREATE TABLE IF NOT EXISTS hr.employees (
    employee_number         VARCHAR(50) PRIMARY KEY,
    -- National Treasury PERSAL personnel number (8 digits). NULL in the
    -- simulated stand-in; a live PERSAL/SCIM feed populates it and HR sync
    -- records it as an identity.employment_identifier with scheme='persal'.
    persal_number           VARCHAR(20),
    id_number               VARCHAR(20),
    title                   VARCHAR(20),
    initials                VARCHAR(20),
    first_name              VARCHAR(100),
    surname                 VARCHAR(100),
    display_name            VARCHAR(100),
    email                   VARCHAR(255) UNIQUE,
    job_title               VARCHAR(120),
    org_unit                VARCHAR(120),
    department_code         VARCHAR(36),
    branch_code             VARCHAR(36),
    manager_employee_number VARCHAR(50) REFERENCES hr.employees(employee_number),
    manager_name            VARCHAR(120),
    work_phone              VARCHAR(30),
    location                VARCHAR(120),
    employment_status       VARCHAR(30) NOT NULL DEFAULT 'active',
    clearance_level         VARCHAR(30),
    hire_date               DATE,
    termination_date        DATE,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hr_emp_dept ON hr.employees(department_code);
CREATE INDEX IF NOT EXISTS idx_hr_emp_branch ON hr.employees(branch_code);
CREATE INDEX IF NOT EXISTS idx_hr_emp_status ON hr.employees(employment_status);
CREATE INDEX IF NOT EXISTS idx_hr_emp_manager ON hr.employees(manager_employee_number);

-- ============================================================================
-- audit - append-only action trail (AG secure export engine)
--
-- Immutability is enforced here, not by application convention: a privileged
-- session may INSERT but may not UPDATE or DELETE, and a trigger rejects any
-- mutation regardless of role. Without this, a hash-bound row in a mutable table
-- is not tamper-evident.
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit.action_audit (
    id                     VARCHAR(36) PRIMARY KEY,
    actor                  VARCHAR(255) NOT NULL,
    action                 VARCHAR(50) NOT NULL,
    target                 VARCHAR(255),
    tenant_scope           JSONB,
    payload_hash           VARCHAR(64) NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    signed_payload         TEXT,
    signature              TEXT,
    key_id                 VARCHAR(64),
    signing_algorithm      VARCHAR(32),
    actor_role             VARCHAR(64),
    policy_version         VARCHAR(32),
    scope_hash             VARCHAR(64),
verification_status  VARCHAR(128),
    verified_at            TIMESTAMPTZ,
    verified_by            VARCHAR(255),
    attestation_size_bytes INTEGER
);
-- Additive column rollout, applied before any index that references them so the
-- script is safe to re-run against a database created by an earlier version.
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS signed_payload TEXT;
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS signature TEXT;
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS key_id VARCHAR(64);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS signing_algorithm VARCHAR(32);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS actor_role VARCHAR(64);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS policy_version VARCHAR(32);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS scope_hash VARCHAR(64);
-- VARCHAR(32) holds the verification outcome codes emitted by the export engine
-- (e.g. signature_invalid: signature does not validate over the recorded payload).
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS verification_status VARCHAR(32);
ALTER TABLE audit.action_audit
    ALTER COLUMN verification_status TYPE VARCHAR(128);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS verified_by VARCHAR(255);
ALTER TABLE audit.action_audit ADD COLUMN IF NOT EXISTS attestation_size_bytes INTEGER;

CREATE INDEX IF NOT EXISTS idx_action_audit_actor ON audit.action_audit(actor);
CREATE INDEX IF NOT EXISTS idx_action_audit_created ON audit.action_audit(created_at);
CREATE INDEX IF NOT EXISTS idx_action_audit_key_id ON audit.action_audit(key_id);

-- Reject UPDATE and DELETE at the engine level. Verification bookkeeping
-- (verification_status/verified_at/verified_by) is the one legitimate mutation,
-- so it is the only column set the trigger will permit.
CREATE OR REPLACE FUNCTION audit.action_audit_append_only()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'audit.action_audit is append-only: % on id=% is not permitted',
            TG_OP, OLD.id
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.actor IS DISTINCT FROM OLD.actor
       OR NEW.action IS DISTINCT FROM OLD.action
       OR NEW.target IS DISTINCT FROM OLD.target
       OR NEW.tenant_scope IS DISTINCT FROM OLD.tenant_scope
       OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.signed_payload IS DISTINCT FROM OLD.signed_payload
       OR NEW.signature IS DISTINCT FROM OLD.signature
       OR NEW.key_id IS DISTINCT FROM OLD.key_id
       OR NEW.signing_algorithm IS DISTINCT FROM OLD.signing_algorithm
       OR NEW.actor_role IS DISTINCT FROM OLD.actor_role
       OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
       OR NEW.scope_hash IS DISTINCT FROM OLD.scope_hash
       OR NEW.attestation_size_bytes IS DISTINCT FROM OLD.attestation_size_bytes
    THEN
        RAISE EXCEPTION
            'audit.action_audit is append-only: % of evidentiary columns is not permitted '
            '(id=%); only verification_status/verified_at/verified_by may be updated',
            TG_OP, OLD.id
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_action_audit_append_only ON audit.action_audit;
CREATE TRIGGER trg_action_audit_append_only
    BEFORE UPDATE OR DELETE ON audit.action_audit
    FOR EACH ROW EXECUTE FUNCTION audit.action_audit_append_only();

-- TRUNCATE bypasses row-level triggers entirely, so it needs its own
-- statement-level guard or the whole trail can be dropped in one statement.
-- Operational guard: fail loudly if the append-only trigger has been disabled.
-- A disabled trigger is indistinguishable from a healthy one to an application
-- that only inspects its own privileges, so detect it at write time instead.
CREATE OR REPLACE FUNCTION audit.action_audit_assert_enabled()
RETURNS TRIGGER AS $$
DECLARE
    state "char";
BEGIN
    SELECT tgenabled INTO state
      FROM pg_trigger
     WHERE tgrelid = 'audit.action_audit'::regclass
       AND tgname   = 'trg_action_audit_append_only'
       AND NOT tgisinternal;

    IF state IS NULL OR state <> 'O' THEN
        RAISE EXCEPTION
            'audit.action_audit append-only trigger is missing or disabled (tgenabled=%)',
            COALESCE(state, '?')
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_action_audit_assert_enabled ON audit.action_audit;
CREATE TRIGGER trg_action_audit_assert_enabled
    BEFORE INSERT ON audit.action_audit
    FOR EACH ROW EXECUTE FUNCTION audit.action_audit_assert_enabled();

CREATE OR REPLACE FUNCTION audit.action_audit_no_truncate()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'audit.action_audit is append-only: TRUNCATE is not permitted'
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_action_audit_no_truncate ON audit.action_audit;
CREATE TRIGGER trg_action_audit_no_truncate
    BEFORE TRUNCATE ON audit.action_audit
    FOR EACH STATEMENT EXECUTE FUNCTION audit.action_audit_no_truncate();

-- Defence in depth: revoke mutation rights from PUBLIC. Application roles that
-- have been granted broader rights must be re-scoped to INSERT/SELECT on audit.
--
-- IMPORTANT: REVOKE only binds roles that are NOT the table owner. An owner can
-- always ALTER/DROP the triggers or re-grant itself privileges, so immutability
-- against a privileged insider additionally requires that the application
-- connect as a role that does not own audit.action_audit. See the OPERATIONAL
-- NOTE at the end of this script.
REVOKE UPDATE, DELETE, TRUNCATE ON audit.action_audit FROM PUBLIC;

-- ============================================================================
-- staging
-- ============================================================================

CREATE TABLE IF NOT EXISTS staging.batch_runs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector        VARCHAR(50) NOT NULL,
    source           VARCHAR(100) NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at      TIMESTAMPTZ,
    records_fetched  INTEGER NOT NULL DEFAULT 0,
    records_valid    INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    status           VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message    TEXT
);
CREATE INDEX IF NOT EXISTS idx_batch_runs_status ON staging.batch_runs(status);
CREATE INDEX IF NOT EXISTS idx_batch_runs_started ON staging.batch_runs(started_at);

CREATE TABLE IF NOT EXISTS staging.raw_records (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id       UUID NOT NULL REFERENCES staging.batch_runs(id),
    source         VARCHAR(100) NOT NULL,
    external_id    VARCHAR(255),
    raw_payload    JSONB NOT NULL,
    received_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ttl_expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '7 days'
);
CREATE INDEX IF NOT EXISTS idx_raw_records_ttl ON staging.raw_records(ttl_expires_at);
CREATE INDEX IF NOT EXISTS idx_raw_records_batch ON staging.raw_records(batch_id);

-- Dead-letter queue for rejected OEM payloads (admin reprocess workflow).
CREATE TABLE IF NOT EXISTS staging.rejected_records (
    id              VARCHAR(36) PRIMARY KEY,
    batch_id        UUID NOT NULL REFERENCES staging.batch_runs(id),
    source          VARCHAR(100) NOT NULL,
    raw_payload     JSONB NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejection_code  VARCHAR(20) NOT NULL,
    rejected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    reprocessed     BOOLEAN NOT NULL DEFAULT FALSE,
    reprocessed_at  TIMESTAMPTZ,
    ttl_expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '30 days'
);
CREATE INDEX IF NOT EXISTS idx_rejected_ttl ON staging.rejected_records(ttl_expires_at);
CREATE INDEX IF NOT EXISTS idx_rejected_batch ON staging.rejected_records(batch_id);

-- ============================================================================
-- warehouse
-- ============================================================================

-- Government tenancy: Province -> Department -> Branch -> App. SITA serves
-- 43 national departments + 113 provincial departments across 9 provinces;
-- the three-tier hierarchy is Tenant (National | Provincial root) ->
-- Sub-Tenant (Department) -> Asset (Application ID). Every app/db-scoped
-- warehouse row denormalises department_id/branch_id (stable slugs) so REST
-- scoping needs no joins. Province scope expands to a department set, so the
-- province_id on departments is a pure reference, not a scoping column.
-- Scope (assigned departments/branches/provinces) is set per user by admin;
-- national roles default to the whole estate.
CREATE TABLE IF NOT EXISTS warehouse.provinces (
    id   VARCHAR(20) PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS warehouse.departments (
    id          VARCHAR(36) PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    code        VARCHAR(60) NOT NULL UNIQUE,
    province_id VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_departments_province ON warehouse.departments(province_id);

CREATE TABLE IF NOT EXISTS warehouse.branches (
    id            VARCHAR(36) PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    code          VARCHAR(60) NOT NULL UNIQUE,
    department_id VARCHAR(36) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_branches_dept ON warehouse.branches(department_id);

-- Connector health / circuit breaker state (SRE dashboard).
CREATE TABLE IF NOT EXISTS warehouse.connector_health (
    name            VARCHAR(50) PRIMARY KEY,
    source          VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'healthy',
    last_poll_at    TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    latency_ms      INTEGER,
    events_per_hour INTEGER,
    error_count     INTEGER NOT NULL DEFAULT 0,
    circuit_state   VARCHAR(20) DEFAULT 'closed',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Canonical OEM findings, deduplicated per (source, external_id).
CREATE TABLE IF NOT EXISTS warehouse.findings (
    id            VARCHAR(36) PRIMARY KEY,
    source        VARCHAR(100) NOT NULL,
    external_id   VARCHAR(255) NOT NULL,
    app_name      VARCHAR(255) NOT NULL DEFAULT 'unknown',
    department_id VARCHAR(36),
    branch_id     VARCHAR(36),
    severity      VARCHAR(20) NOT NULL,
    title         VARCHAR(500) NOT NULL,
    description   TEXT,
    category      VARCHAR(200),
    -- Cross-source OWASP Top 10 classification. `category` above is the OEM's
    -- own vocabulary and is preserved unchanged; these four columns are the
    -- platform's classification, applied at ingest so the rollup can be
    -- aggregated and tenant-scoped like any other warehouse column.
    -- owasp_status distinguishes the non-classified states on purpose:
    --   classified     - mapped to a category
    --   unmapped       - vendor value seen, no mapping yet (maintenance backlog)
    --   not_applicable - source vocabulary is not a vulnerability class
    --   absent         - the OEM supplied no category at all
    -- A NULL owasp_id therefore never means "silently guessed wrong".
    owasp_id          VARCHAR(10),
    cwe_id            VARCHAR(20),
    owasp_status      VARCHAR(20),
    taxonomy_version  VARCHAR(32),
    raw_data      JSONB,
    first_seen    TIMESTAMPTZ NOT NULL,
    last_seen     TIMESTAMPTZ NOT NULL,
    status        VARCHAR(50) NOT NULL DEFAULT 'open',
    version       INTEGER NOT NULL DEFAULT 1,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_findings_source_external UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_app ON warehouse.findings(app_name);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON warehouse.findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_last_seen ON warehouse.findings(last_seen);
CREATE INDEX IF NOT EXISTS idx_findings_dept ON warehouse.findings(department_id);
CREATE INDEX IF NOT EXISTS idx_findings_branch ON warehouse.findings(branch_id);
CREATE INDEX IF NOT EXISTS idx_findings_owasp ON warehouse.findings(owasp_id);
CREATE INDEX IF NOT EXISTS idx_findings_cwe ON warehouse.findings(cwe_id);
CREATE INDEX IF NOT EXISTS idx_findings_owasp_status ON warehouse.findings(owasp_status);
-- The dashboard rollup is always scoped and always grouped, so serve that shape.
CREATE INDEX IF NOT EXISTS idx_findings_owasp_dept
    ON warehouse.findings(department_id, owasp_id);

-- ---------------------------------------------------------------------------
-- CONVERGENT UPGRADES
--
-- Everything above uses CREATE TABLE IF NOT EXISTS, which is a no-op against a
-- table that already exists. A database created from an EARLIER revision of
-- this script therefore never receives columns added in a LATER revision, and
-- the application fails at runtime with
--
--     column findings.owasp_id does not exist
--
-- because the ORM model is ahead of the physical schema. That is not
-- hypothetical: it is what the live database was doing, breaking
-- GET /api/v1/findings with a 500.
--
-- The statements below make this script convergent - safe to re-run against an
-- existing database, adding only what is missing. Keep any ALTER in this
-- section when a column is added to an existing table, and add it to the
-- CREATE TABLE above at the same time so fresh databases get it in one pass.
-- ---------------------------------------------------------------------------

ALTER TABLE warehouse.findings ADD COLUMN IF NOT EXISTS owasp_id          VARCHAR(10);
ALTER TABLE warehouse.findings ADD COLUMN IF NOT EXISTS cwe_id            VARCHAR(20);
ALTER TABLE warehouse.findings ADD COLUMN IF NOT EXISTS owasp_status      VARCHAR(20);
ALTER TABLE warehouse.findings ADD COLUMN IF NOT EXISTS taxonomy_version  VARCHAR(32);

-- Re-issue the OWASP indexes now the columns are guaranteed to exist. They were
-- no-ops above on a database that lacked the columns at that point.
CREATE INDEX IF NOT EXISTS idx_findings_owasp ON warehouse.findings(owasp_id);
CREATE INDEX IF NOT EXISTS idx_findings_cwe ON warehouse.findings(cwe_id);
CREATE INDEX IF NOT EXISTS idx_findings_owasp_status ON warehouse.findings(owasp_status);
CREATE INDEX IF NOT EXISTS idx_findings_owasp_dept
    ON warehouse.findings(department_id, owasp_id);

-- Daily fused risk scores per application (Exec / Risk dashboards).
CREATE TABLE IF NOT EXISTS warehouse.risk_scores (
    id                      VARCHAR(36) PRIMARY KEY,
    app_name                VARCHAR(255) NOT NULL,
    department_id           VARCHAR(36),
    branch_id               VARCHAR(36),
    score_date              DATE NOT NULL,
    fused_score             NUMERIC(5,1) NOT NULL,
    signal_appscan          NUMERIC(5,1),
    signal_imperva          NUMERIC(5,1),
    signal_api_exposure     NUMERIC(5,1),
    signal_compliance_penalty NUMERIC(5,1),
    bucket                  VARCHAR(20),
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_risk_app_date UNIQUE (app_name, score_date)
);
CREATE INDEX IF NOT EXISTS idx_risk_app ON warehouse.risk_scores(app_name);
CREATE INDEX IF NOT EXISTS idx_risk_bucket ON warehouse.risk_scores(bucket);
CREATE INDEX IF NOT EXISTS idx_risk_dept ON warehouse.risk_scores(department_id);
CREATE INDEX IF NOT EXISTS idx_risk_branch ON warehouse.risk_scores(branch_id);

-- Unified alert feed with dedup counters (SOC dashboard).
CREATE TABLE IF NOT EXISTS warehouse.alerts (
    id              VARCHAR(36) PRIMARY KEY,
    rule_id         VARCHAR(50) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    severity        VARCHAR(20) NOT NULL,
    source          VARCHAR(100),
    target_id       VARCHAR(255),
    department_id   VARCHAR(36),
    branch_id       VARCHAR(36),
    status          VARCHAR(20) NOT NULL DEFAULT 'new',
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    enriched_data   JSONB,
    channels        JSONB,
    dedup_key       VARCHAR(190),
    dedup_count     INTEGER NOT NULL DEFAULT 1,
    first_triggered TIMESTAMPTZ NOT NULL,
    last_triggered  TIMESTAMPTZ NOT NULL,
    last_dispatched_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON warehouse.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON warehouse.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_last_triggered ON warehouse.alerts(last_triggered);
CREATE INDEX IF NOT EXISTS idx_alerts_dept ON warehouse.alerts(department_id);
CREATE INDEX IF NOT EXISTS idx_alerts_branch ON warehouse.alerts(branch_id);

-- Per-channel delivery audit trail (which channel was attempted and its result).
CREATE TABLE IF NOT EXISTS warehouse.dispatch_log (
    id            VARCHAR(36) PRIMARY KEY,
    alert_id      VARCHAR(64) NOT NULL,
    channel       VARCHAR(20) NOT NULL,
    department_id VARCHAR(36),
    branch_id     VARCHAR(36),
    status        VARCHAR(20) NOT NULL DEFAULT 'sent',
    error         TEXT,
    attempted_at  TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dispatch_log_alert ON warehouse.dispatch_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_log_channel ON warehouse.dispatch_log(channel);
CREATE INDEX IF NOT EXISTS idx_dispatch_dept ON warehouse.dispatch_log(department_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_branch ON warehouse.dispatch_log(branch_id);

-- Compliance framework snapshots (12-week trend source).
CREATE TABLE IF NOT EXISTS warehouse.compliance_snapshots (
    id              VARCHAR(36) PRIMARY KEY,
    framework       VARCHAR(50) NOT NULL,
    snapshot_date   DATE NOT NULL,
    overall_score   NUMERIC(5,1) NOT NULL,
    details         JSONB,
    total_controls  INTEGER NOT NULL,
    passed_controls INTEGER NOT NULL,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_compliance_snap_framework_date
    ON warehouse.compliance_snapshots(framework, snapshot_date);

-- Compliance / audit gaps (POPIA · ISO 27001).
CREATE TABLE IF NOT EXISTS warehouse.compliance_gaps (
    id             VARCHAR(36) PRIMARY KEY,
    framework      VARCHAR(50) NOT NULL,
    control_id     VARCHAR(50) NOT NULL,
    domain         VARCHAR(100),
    description    TEXT NOT NULL,
    owner          VARCHAR(100),
    severity       VARCHAR(20),
    due_date       DATE,
    status         VARCHAR(30) NOT NULL DEFAULT 'open',
    evidence_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_compliance_gaps_due ON warehouse.compliance_gaps(due_date);
CREATE INDEX IF NOT EXISTS idx_compliance_gaps_framework ON warehouse.compliance_gaps(framework);

-- API exposure inventory (AppSec API Exposure panel).
CREATE TABLE IF NOT EXISTS warehouse.api_endpoints (
    id              VARCHAR(36) PRIMARY KEY,
    app_name        VARCHAR(255) NOT NULL,
    department_id   VARCHAR(36),
    branch_id       VARCHAR(36),
    endpoint        TEXT NOT NULL,
    method          VARCHAR(10) NOT NULL DEFAULT 'GET',
    is_shadow       BOOLEAN NOT NULL DEFAULT FALSE,
    exposure_score  NUMERIC(5,1) NOT NULL DEFAULT 0,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_app ON warehouse.api_endpoints(app_name);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_shadow ON warehouse.api_endpoints(is_shadow);
CREATE INDEX IF NOT EXISTS idx_api_dept ON warehouse.api_endpoints(department_id);
CREATE INDEX IF NOT EXISTS idx_api_branch ON warehouse.api_endpoints(branch_id);

CREATE TABLE IF NOT EXISTS warehouse.waf_blocks (
    id            VARCHAR(36) PRIMARY KEY,
    app_name      VARCHAR(255) NOT NULL,
    department_id VARCHAR(36),
    branch_id     VARCHAR(36),
    attack_type   VARCHAR(100),
    request_uri   VARCHAR(255),
    action        VARCHAR(20) NOT NULL DEFAULT 'block',
    src_ip        VARCHAR(45),
    block_time    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_app ON warehouse.waf_blocks(app_name);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_time ON warehouse.waf_blocks(block_time);
CREATE INDEX IF NOT EXISTS idx_waf_dept ON warehouse.waf_blocks(department_id);
CREATE INDEX IF NOT EXISTS idx_waf_branch ON warehouse.waf_blocks(branch_id);

CREATE TABLE IF NOT EXISTS warehouse.system_metrics (
    id          VARCHAR(36) PRIMARY KEY,
    metric      VARCHAR(50) NOT NULL,
    value       NUMERIC(8,2) NOT NULL,
    unit        VARCHAR(20) NOT NULL DEFAULT '%',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.agents (
    id        VARCHAR(36) PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    role      VARCHAR(50) NOT NULL,
    version   VARCHAR(30) NOT NULL,
    status    VARCHAR(20) NOT NULL DEFAULT 'online',
    host      VARCHAR(100),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agents_role ON warehouse.agents(role);

CREATE TABLE IF NOT EXISTS warehouse.slo_metrics (
    id          VARCHAR(36) PRIMARY KEY,
    metric      VARCHAR(20) NOT NULL,
    week_start  DATE NOT NULL,
    value_hours INTEGER NOT NULL,
    CONSTRAINT uq_slo_metric_week UNIQUE (metric, week_start)
);

CREATE TABLE IF NOT EXISTS warehouse.database_inventory (
    id             VARCHAR(36) PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    department_id  VARCHAR(36),
    branch_id      VARCHAR(36),
    engine         VARCHAR(50),
    monitored      BOOLEAN NOT NULL DEFAULT TRUE,
    agent_version  VARCHAR(30),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Imperva WAF block telemetry (AppSec WAF Block Summary / WAF Blocks stat).
CREATE TABLE IF NOT EXISTS warehouse.waf_blocks (
    id          VARCHAR(36) PRIMARY KEY,
    app_name    VARCHAR(255) NOT NULL,
    attack_type VARCHAR(100),
    request_uri TEXT,
    action      VARCHAR(20) NOT NULL DEFAULT 'block',
    src_ip      VARCHAR(45),
    block_time  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_app ON warehouse.waf_blocks(app_name);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_time ON warehouse.waf_blocks(block_time);

-- SRE system-health metrics (CPU / Memory / Disk I/O / Queue Depth / Uptime).
CREATE TABLE IF NOT EXISTS warehouse.system_metrics (
    id          VARCHAR(36) PRIMARY KEY,
    metric      VARCHAR(50) NOT NULL,
    value       NUMERIC(8,2) NOT NULL,
    unit        VARCHAR(20) NOT NULL DEFAULT '%',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_time
    ON warehouse.system_metrics(metric, recorded_at);

-- SRE agent inventory (DAM agents, WAF agents, ingestion workers).
CREATE TABLE IF NOT EXISTS warehouse.agents (
    id        VARCHAR(36) PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    role      VARCHAR(50) NOT NULL,
    version   VARCHAR(30) NOT NULL,
    status    VARCHAR(20) NOT NULL DEFAULT 'online',
    host      VARCHAR(100),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agents_role ON warehouse.agents(role);

-- SOC SLO metrics, weekly MTTD / MTTR.
CREATE TABLE IF NOT EXISTS warehouse.slo_metrics (
    id          VARCHAR(36) PRIMARY KEY,
    metric      VARCHAR(20) NOT NULL,
    week_start  DATE NOT NULL,
    value_hours NUMERIC(6,2) NOT NULL,
    CONSTRAINT uq_slo_metric_week UNIQUE (metric, week_start)
);

-- Database inventory (DBSec Databases Monitored / Coverage).
CREATE TABLE IF NOT EXISTS warehouse.database_inventory (
    id             VARCHAR(36) PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    department_id  VARCHAR(36),
    branch_id      VARCHAR(36),
    engine         VARCHAR(50),
    monitored      BOOLEAN NOT NULL DEFAULT TRUE,
    agent_version  VARCHAR(30),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_database_inventory_monitored
    ON warehouse.database_inventory(monitored);
CREATE INDEX IF NOT EXISTS idx_db_dept ON warehouse.database_inventory(department_id);
CREATE INDEX IF NOT EXISTS idx_db_branch ON warehouse.database_inventory(branch_id);

-- ============================================================================
-- archive
-- ============================================================================
-- LIKE ... INCLUDING ALL copies columns, defaults, constraints and indexes,
-- so maintenance.sql's ON CONFLICT rotation preserves PK/UNIQUE keys.

CREATE TABLE IF NOT EXISTS archive.risk_scores (LIKE warehouse.risk_scores INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.alerts (LIKE warehouse.alerts INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.compliance_snapshots (LIKE warehouse.compliance_snapshots INCLUDING ALL);
CREATE TABLE IF NOT EXISTS archive.findings (LIKE warehouse.findings INCLUDING ALL);

-- ============================================================================
-- pg_cron maintenance jobs (TTL purge, archive rotation, reindex) are defined
-- in maintenance.sql and require shared_preload_libraries='pg_cron'.
-- Run separately once pg_cron is enabled; init-db.sql stays dependency-free.
-- ============================================================================

-- Baseline connector rows (SRE Connector Health).
INSERT INTO warehouse.connector_health (name, source, status) VALUES
    ('appscan', 'appscan', 'healthy'),
    ('imperva_dam', 'imperva', 'healthy'),
    ('imperva_waf', 'imperva', 'healthy'),
    ('apisec', 'apisec', 'healthy'),
    ('compliance', 'compliance', 'healthy')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- OPERATIONAL NOTE - audit.action_audit ownership
-- ============================================================================
--
-- The append-only guarantee is enforced by triggers, not by privilege.
-- PostgreSQL owners implicitly hold every privilege on their tables and can
-- always run ALTER TABLE ... DISABLE TRIGGER or DROP TRIGGER, so REVOKE does
-- NOT protect against a role that owns audit.action_audit.
--
-- Required production posture: the application must connect as a role that does
-- NOT own this table, with only INSERT and SELECT granted:
--
--   CREATE ROLE sita_app LOGIN PASSWORD '...';
--   GRANT USAGE ON SCHEMA audit TO sita_app;
--   GRANT INSERT, SELECT ON audit.action_audit TO sita_app;
--   REVOKE UPDATE, DELETE, TRUNCATE ON audit.action_audit FROM sita_app;
--   ALTER TABLE audit.action_audit OWNER TO <break-glass DBA role>;
--
-- trg_action_audit_assert_enabled additionally causes every INSERT to fail if
-- the append-only trigger has been disabled, so a disabled guard is loud rather
-- than silent.
