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
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON identity.users(email);

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
    id          VARCHAR(36) PRIMARY KEY,
    source      VARCHAR(100) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    app_name    VARCHAR(255) NOT NULL DEFAULT 'unknown',
    severity    VARCHAR(20) NOT NULL,
    title       VARCHAR(500) NOT NULL,
    description TEXT,
    category    VARCHAR(200),
    raw_data    JSONB,
    first_seen  TIMESTAMPTZ NOT NULL,
    last_seen   TIMESTAMPTZ NOT NULL,
    status      VARCHAR(50) NOT NULL DEFAULT 'open',
    version     INTEGER NOT NULL DEFAULT 1,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_findings_source_external UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_app ON warehouse.findings(app_name);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON warehouse.findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_last_seen ON warehouse.findings(last_seen);

-- Daily fused risk scores per application (Exec / Risk dashboards).
CREATE TABLE IF NOT EXISTS warehouse.risk_scores (
    id                      VARCHAR(36) PRIMARY KEY,
    app_name                VARCHAR(255) NOT NULL,
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

-- Unified alert feed with dedup counters (SOC dashboard).
CREATE TABLE IF NOT EXISTS warehouse.alerts (
    id              VARCHAR(36) PRIMARY KEY,
    rule_id         VARCHAR(50) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    severity        VARCHAR(20) NOT NULL,
    source          VARCHAR(100),
    target_id       VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'new',
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    enriched_data   JSONB,
    dedup_key       VARCHAR(64),
    dedup_count     INTEGER NOT NULL DEFAULT 1,
    first_triggered TIMESTAMPTZ NOT NULL,
    last_triggered  TIMESTAMPTZ NOT NULL,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON warehouse.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON warehouse.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_last_triggered ON warehouse.alerts(last_triggered);

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
    endpoint        TEXT NOT NULL,
    method          VARCHAR(10) NOT NULL DEFAULT 'GET',
    is_shadow       BOOLEAN NOT NULL DEFAULT FALSE,
    exposure_score  NUMERIC(5,1) NOT NULL DEFAULT 0,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_app ON warehouse.api_endpoints(app_name);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_shadow ON warehouse.api_endpoints(is_shadow);

CREATE TABLE IF NOT EXISTS warehouse.waf_blocks (
    id          VARCHAR(36) PRIMARY KEY,
    app_name    VARCHAR(255) NOT NULL,
    attack_type VARCHAR(100),
    request_uri VARCHAR(255),
    action      VARCHAR(20) NOT NULL DEFAULT 'block',
    src_ip      VARCHAR(45),
    block_time  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_app ON warehouse.waf_blocks(app_name);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_time ON warehouse.waf_blocks(block_time);

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
    engine         VARCHAR(50),
    monitored      BOOLEAN NOT NULL DEFAULT TRUE,
    agent_version  VARCHAR(30),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_database_inventory_monitored
    ON warehouse.database_inventory(monitored);

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
