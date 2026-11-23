-- Adds tenant and hierarchy-tier identity to tenant-owned warehouse records.
ALTER TABLE warehouse.findings
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.risk_scores
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.alerts
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.dispatch_log
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.compliance_snapshots
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.compliance_gaps
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.api_endpoints
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.waf_blocks
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.agents
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.database_inventory
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);
ALTER TABLE warehouse.slo_metrics
    ADD COLUMN IF NOT EXISTS tenant_workspace_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS tenant_scope_level_key VARCHAR(64);

ALTER TABLE warehouse.findings
    DROP CONSTRAINT IF EXISTS uq_findings_source_external;
ALTER TABLE warehouse.risk_scores
    DROP CONSTRAINT IF EXISTS uq_risk_app_date;
ALTER TABLE warehouse.slo_metrics
    DROP CONSTRAINT IF EXISTS uq_slo_metric_week;
CREATE UNIQUE INDEX IF NOT EXISTS uq_findings_global_source_external
    ON warehouse.findings(source, external_id)
    WHERE tenant_workspace_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_findings_tenant_source_external
    ON warehouse.findings(tenant_workspace_id, tenant_scope_level_key, source, external_id)
    WHERE tenant_workspace_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_global_app_date
    ON warehouse.risk_scores(app_name, score_date)
    WHERE tenant_workspace_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_tenant_app_date
    ON warehouse.risk_scores(tenant_workspace_id, tenant_scope_level_key, app_name, score_date)
    WHERE tenant_workspace_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_slo_global_metric_week
    ON warehouse.slo_metrics(metric, week_start)
    WHERE tenant_workspace_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_slo_tenant_metric_week
    ON warehouse.slo_metrics(tenant_workspace_id, tenant_scope_level_key, metric, week_start)
    WHERE tenant_workspace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_findings_tenant_scope
    ON warehouse.findings(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_risk_scores_tenant_scope
    ON warehouse.risk_scores(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_alerts_tenant_scope
    ON warehouse.alerts(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_dispatch_tenant_scope
    ON warehouse.dispatch_log(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_compliance_snapshots_tenant_scope
    ON warehouse.compliance_snapshots(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_compliance_gaps_tenant_scope
    ON warehouse.compliance_gaps(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_api_endpoints_tenant_scope
    ON warehouse.api_endpoints(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_waf_blocks_tenant_scope
    ON warehouse.waf_blocks(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_agents_tenant_scope
    ON warehouse.agents(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_database_inventory_tenant_scope
    ON warehouse.database_inventory(tenant_workspace_id, tenant_scope_level_key);
CREATE INDEX IF NOT EXISTS idx_slo_metrics_tenant_scope
    ON warehouse.slo_metrics(tenant_workspace_id, tenant_scope_level_key);
