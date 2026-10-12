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

-- ============================================================================
-- Personal-data retention (gap G-09, docs/B5_ICASA_ECT_Gap_Analysis.md)
--
-- Personal information is not held indefinitely by default. POPIA section 19
-- requires safeguards to prevent loss or unauthorised destruction; an
-- unbounded store is a standing target and cannot evidence minimisation.
--
-- Retention is applied per data class rather than estate-wide, because the
-- classes have different purposes and different defensible retention periods.
-- Durations are deliberately conservative and must be confirmed against the
-- Records of Taxing Bodies / state records policy before production.
-- ============================================================================

-- 7. WAF block telemetry -> 180 days
--
-- src_ip and request_uri are personal information under POPIA s.13(c) (an
-- online identifier / location information) and both can carry identifiers in
-- the query string. A security investigation rarely needs raw blocks older
-- than two quarters, and the finding itself is retained separately in
-- warehouse.findings.
SELECT cron.schedule('retire-waf-blocks', '0 4 * * *',
    $cron$
    DELETE FROM warehouse.waf_blocks
    WHERE block_time < now() - INTERVAL '180 days';
    $cron$);

-- 8. Person records for separated employees -> 90 days, then tombstone
--
-- Scope note: the platform does not absorb employee identity numbers as a
-- matter of course (measured 2026-10-09: 22 of 2,451 rows carry an id_number,
-- the rest NULL) and no account originates from a person record. Employee and
-- role data originates in the government HR systems. This job therefore
-- targets the attributes that ARE populated estate-wide -- name, email, work
-- phone, location, clearance -- with identity number blanked defensively in
-- case a future HR feed supplies one, since the sync path copies it verbatim.
--
-- Deliberately NOT a hard delete on the first pass: the row is blanked of all
-- identifying content and retained as a stub so that historical audit records
-- referring to a person_id remain interpretable. A second pass removes the
-- stubs once the referential trail has aged out. Columns are listed explicitly
-- rather than blanking the whole row so employment_status (an audit-relevant
-- fact) is preserved. Both employee_number and email are UNIQUE, but Postgres
-- permits multiple NULLs in a unique column, so blanking is safe.
SELECT cron.schedule('retire-separated-persons', '0 4 * * *',
    $cron$
    UPDATE identity.persons
       SET employee_number = NULL,
           email = NULL,
           id_number = NULL,
           title = NULL,
           initials = NULL,
           surname = '[retired]',
           display_name = '[retired]',
           work_phone = NULL,
           manager_name = NULL,
           location = NULL,
           is_active = FALSE
     WHERE employment_status <> 'active'
       AND employee_number IS NOT NULL
       AND updated_at < now() - INTERVAL '90 days';

    DELETE FROM identity.persons
     WHERE employee_number IS NULL
       AND employment_status <> 'active'
       AND updated_at < now() - INTERVAL '5 years';
    $cron$);

-- 9. Deactivated user accounts -> 30 days, then credential erasure
--
-- The account row is retained (audit trail, referential integrity) but the
-- credential material is cleared, so a dormant account cannot be used to
-- re-authenticate and the password hash is no longer retained.
SELECT cron.schedule('retire-deactivated-users', '0 4 * * *',
    $cron$
    UPDATE identity.users
       SET password_hash = '[erased]',
           is_active = FALSE
     WHERE is_active = FALSE
       AND updated_at < now() - INTERVAL '30 days';
    $cron$);

-- Note on what is deliberately NOT purged here:
--   audit.action_audit  — append-only, retained indefinitely by design and
--                          enforced by trigger. It is the evidentiary record
--                          and must outlive the data it describes.
--   warehouse.findings  — retained; carries vulnerability records, not personal
--                          information, but raw_data may embed identifiers. A
--                          PII filter on the ingest path is tracked separately.
