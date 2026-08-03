-- SITA Platform Database Initialization

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS archive;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS staging.batch_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector       VARCHAR(50) NOT NULL,
    source          VARCHAR(100) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_valid   INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS staging.raw_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        UUID NOT NULL REFERENCES staging.batch_runs(id),
    source          VARCHAR(100) NOT NULL,
    external_id     VARCHAR(255),
    raw_payload     JSONB NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ttl_expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '7 days'
);
CREATE INDEX IF NOT EXISTS idx_raw_records_ttl ON staging.raw_records(ttl_expires_at);

CREATE TABLE IF NOT EXISTS staging.rejected_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

CREATE TABLE IF NOT EXISTS warehouse.findings (
    id              VARCHAR(36) PRIMARY KEY,
    source          VARCHAR(100) NOT NULL,
    external_id     VARCHAR(255) NOT NULL,
    app_name        VARCHAR(255) NOT NULL DEFAULT 'unknown',
    severity        VARCHAR(20) NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    category        VARCHAR(200),
    raw_data        JSONB,
    first_seen      TIMESTAMPTZ NOT NULL,
    last_seen       TIMESTAMPTZ NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'open',
    version         INTEGER NOT NULL DEFAULT 1,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_findings_source_external UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_app ON warehouse.findings(app_name);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON warehouse.findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_last_seen ON warehouse.findings(last_seen);

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

CREATE TABLE IF NOT EXISTS warehouse.compliance_gaps (
    id              VARCHAR(36) PRIMARY KEY,
    framework       VARCHAR(50) NOT NULL,
    control_id      VARCHAR(50) NOT NULL,
    domain          VARCHAR(100),
    description     TEXT NOT NULL,
    owner           VARCHAR(100),
    severity        VARCHAR(20),
    due_date        DATE,
    status          VARCHAR(30) NOT NULL DEFAULT 'open',
    evidence_count  INTEGER NOT NULL DEFAULT 0
);

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

-- Optional: schedule staging TTL cleanup if pg_cron is available.
-- Guarded so init succeeds on base images without pg_cron.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule('staging-ttl', '0 2 * * *',
            'DELETE FROM staging.raw_records WHERE ttl_expires_at < now(); DELETE FROM staging.rejected_records WHERE ttl_expires_at < now();'
        );
    END IF;
END
$$;

INSERT INTO warehouse.connector_health (name, source, status) VALUES
    ('appscan', 'appscan', 'healthy'),
    ('imperva_dam', 'imperva', 'healthy'),
    ('imperva_waf', 'imperva', 'healthy'),
    ('apisec', 'apisec', 'healthy'),
    ('compliance', 'compliance', 'healthy')
ON CONFLICT (name) DO NOTHING;
