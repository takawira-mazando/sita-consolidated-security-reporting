-- SITA Platform Scheduled Maintenance (pg_cron)
-- Idempotent; safe to run repeatedly. All cron jobs are (re)created here.
-- Requires the pg_cron extension (shared_preload_libraries='pg_cron').

DO $$
DECLARE
    job_name TEXT;
BEGIN
    -- (Re)create jobs by dropping and re-adding so config changes apply.
    FOR job_name IN SELECT jobname FROM cron.job LOOP
        PERFORM cron.unschedule(job_name);
    END LOOP;
END
$$;

-- 1. Staging TTL purge (raw records 7d, rejected 30d)
SELECT cron.schedule('staging-ttl', '0 2 * * *',
    $cron$
    DELETE FROM staging.raw_records
    WHERE ttl_expires_at < now();
    DELETE FROM staging.rejected_records
    WHERE ttl_expires_at < now();
    $cron$);

-- 2. Rotate risk scores > 400 days into archive, then purge
SELECT cron.schedule('rotate-risk-scores', '0 3 1 * *',
    $cron$
    INSERT INTO archive.risk_scores
    SELECT * FROM warehouse.risk_scores
    WHERE score_date < CURRENT_DATE - INTERVAL '400 days'
    ON CONFLICT (app_name, score_date) DO NOTHING;
    DELETE FROM warehouse.risk_scores
    WHERE score_date < CURRENT_DATE - INTERVAL '400 days';
    $cron$);

-- 3. Rotate resolved/closed alerts > 90 days into archive, then purge
SELECT cron.schedule('rotate-alerts', '0 3 * * 0',
    $cron$
    INSERT INTO archive.alerts
    SELECT * FROM warehouse.alerts
    WHERE status IN ('resolved','dismissed')
      AND updated_at < now() - INTERVAL '90 days'
    ON CONFLICT (id) DO NOTHING;
    DELETE FROM warehouse.alerts
    WHERE status IN ('resolved','dismissed')
      AND updated_at < now() - INTERVAL '90 days';
    $cron$);

-- 4. Rotate compliance snapshots > 730 days into archive, then purge
SELECT cron.schedule('rotate-compliance', '0 3 1 * *',
    $cron$
    INSERT INTO archive.compliance_snapshots
    SELECT * FROM warehouse.compliance_snapshots
    WHERE snapshot_date < CURRENT_DATE - INTERVAL '730 days'
    ON CONFLICT (id) DO NOTHING;
    DELETE FROM warehouse.compliance_snapshots
    WHERE snapshot_date < CURRENT_DATE - INTERVAL '730 days';
    $cron$);

-- 5. Bloat control on high-write tables
SELECT cron.schedule('reindex-main', '30 3 * * 0',
    $cron$
    REINDEX INDEX CONCURRENTLY idx_findings_app;
    REINDEX INDEX CONCURRENTLY idx_findings_last_seen;
    REINDEX INDEX CONCURRENTLY idx_alerts_last_triggered;
    $cron$);

-- 6. Connector health stale-flag sweep (degraded -> down after missed windows)
SELECT cron.schedule('connector-staleness', '*/15 * * * *',
    $cron$
    UPDATE warehouse.connector_health
    SET status = CASE
            WHEN last_success_at < now() - INTERVAL '30 minutes' THEN 'degraded'
            WHEN last_success_at < now() - INTERVAL '60 minutes' THEN 'down'
            ELSE status END,
        circuit_state = CASE
            WHEN last_success_at < now() - INTERVAL '60 minutes' THEN 'open'
            ELSE circuit_state END
    WHERE last_success_at IS NOT NULL;
    $cron$);
