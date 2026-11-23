DROP INDEX IF EXISTS warehouse.uq_findings_tenant_source_external;
CREATE UNIQUE INDEX uq_findings_tenant_source_external
    ON warehouse.findings(tenant_workspace_id, tenant_scope_level_key, source, external_id)
    WHERE tenant_workspace_id IS NOT NULL;

DROP INDEX IF EXISTS warehouse.uq_risk_tenant_app_date;
CREATE UNIQUE INDEX uq_risk_tenant_app_date
    ON warehouse.risk_scores(tenant_workspace_id, tenant_scope_level_key, app_name, score_date)
    WHERE tenant_workspace_id IS NOT NULL;

DROP INDEX IF EXISTS warehouse.uq_slo_tenant_metric_week;
CREATE UNIQUE INDEX uq_slo_tenant_metric_week
    ON warehouse.slo_metrics(tenant_workspace_id, tenant_scope_level_key, metric, week_start)
    WHERE tenant_workspace_id IS NOT NULL;
