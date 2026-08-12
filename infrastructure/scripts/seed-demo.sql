-- SITA Platform — Demo Seed Data
-- Populates warehouse tables so the RBAC dashboards render meaningful data.

-- =====================================================================
-- 1) RISK SCORES — 30-day fused risk trend per application
-- =====================================================================
INSERT INTO warehouse.risk_scores
    (id, app_name, score_date, fused_score, signal_appscan, signal_imperva,
     signal_api_exposure, signal_compliance_penalty, bucket)
SELECT
    gen_random_uuid()::text,
    a.app_name,
    d.day,
    ROUND((a.today_score + a.slope * d.idx + (random() * 2 - 1) * 1.2)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.55 + a.slope * d.idx * 0.4)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.25)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.15)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.05)::numeric, 1),
    CASE
        WHEN a.today_score + a.slope * d.idx >= 70 THEN 'critical'
        WHEN a.today_score + a.slope * d.idx >= 45 THEN 'monitored'
        ELSE 'safe'
    END
FROM (VALUES
    ('legacy-api',       78.2,  0.35),
    ('payment-gateway',  66.4,  0.15),
    ('customer-portal',  53.1, -0.05),
    ('document-svc',     28.6, -0.08),
    ('internal-hr',      13.5, -0.02)
) AS a(app_name, today_score, slope)
CROSS JOIN (
    SELECT CURRENT_DATE - gs AS day, gs AS idx
    FROM generate_series(0, 29) AS gs
) AS d
ON CONFLICT (app_name, score_date) DO UPDATE
    SET fused_score = EXCLUDED.fused_score, bucket = EXCLUDED.bucket;

-- ---------------------------------------------------------------------
-- 1b) PROVINCIAL RISK SCORES — one app per provincial department, so the
--     anonymised provincial peer benchmark (GET /api/v1/benchmark/province)
--     returns a full leaderboard across the 9 provinces. Each row carries
--     the province-namespaced department_id (e.g. gp-health) that
--     tenant_filter expands from the caller's province_ids.
-- ---------------------------------------------------------------------
INSERT INTO warehouse.risk_scores
    (id, app_name, department_id, score_date, fused_score, signal_appscan,
     signal_imperva, signal_api_exposure, signal_compliance_penalty, bucket)
SELECT
    gen_random_uuid()::text,
    a.app_name,
    a.department_id,
    CURRENT_DATE,
    a.today_score,
    ROUND(GREATEST(0, a.today_score * 0.55)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.25)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.15)::numeric, 1),
    ROUND(GREATEST(0, a.today_score * 0.05)::numeric, 1),
    CASE WHEN a.today_score >= 70 THEN 'critical'
         WHEN a.today_score >= 45 THEN 'monitored'
         ELSE 'safe' END
FROM (VALUES
    ('gp-health-core',    'gp-health',          81.4),
    ('gp-education-core', 'gp-education',       67.2),
    ('gp-cogta-core',     'gp-cogta',           58.9),
    ('wc-health-core',    'wc-health',          74.6),
    ('wc-education-core', 'wc-education',       51.3),
    ('wc-transport-core', 'wc-transport',       39.7),
    ('ec-health-core',    'ec-health',          62.1),
    ('ec-education-core', 'ec-education',       44.5),
    ('kzn-health-core',   'kzn-health',         70.8),
    ('kzn-cogta-core',    'kzn-cogta',          55.2),
    ('lp-health-core',    'lp-health',          48.9),
    ('mp-health-core',    'mp-health',          59.3),
    ('nw-health-core',    'nw-health',          42.6),
    ('nc-health-core',    'nc-health',          36.4),
    ('fs-health-core',    'fs-health',          47.1),
    ('fs-education-core', 'fs-education',       33.8)
) AS a(app_name, department_id, today_score)
ON CONFLICT (app_name, score_date) DO UPDATE
    SET fused_score = EXCLUDED.fused_score, bucket = EXCLUDED.bucket;

-- =====================================================================
-- 2) FINDINGS — AppScan vulnerability findings
-- =====================================================================
INSERT INTO warehouse.findings
    (id, source, external_id, app_name, severity, title, description, category,
     raw_data, first_seen, last_seen, status, version)
VALUES
    -- legacy-api
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1001', 'legacy-api', 'critical',
     'SQL Injection in SOAP endpoint', 'Classic SQLi in /soap/login allows auth bypass.',
     'sqli', '{"cve":"CVE-2026-31142","cvss":9.8}', now() - interval '12 days', now() - interval '2 hours', 'open', 3),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1002', 'legacy-api', 'critical',
     'Remote Code Execution in file upload', 'RCE via unsafe deserialization of uploaded files.',
     'rce', '{"cve":"CVE-2026-27815","cvss":8.6}', now() - interval '9 days', now() - interval '1 day', 'open', 2),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1003', 'legacy-api', 'high',
     'Stored XSS in admin console', 'Persistent XSS allows session hijacking for admins.',
     'xss', NULL, now() - interval '8 days', now() - interval '6 hours', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1004', 'legacy-api', 'high',
     'Session fixation in login flow', 'Session ID not regenerated after authentication.',
     'broken_auth', NULL, now() - interval '6 days', now() - interval '3 days', 'in_review', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1005', 'legacy-api', 'medium',
     'Missing security headers', 'No CSP or X-Frame-Options headers set on responses.',
     'misconfig', NULL, now() - interval '5 days', now() - interval '4 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-1006', 'legacy-api', 'low',
     'Verbose error messages', 'Stack traces exposed in API error responses.',
     'info_disclosure', NULL, now() - interval '4 days', now() - interval '4 days', 'open', 1),

    -- payment-gateway
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-2001', 'payment-gateway', 'critical',
     'SQL Injection in /api/pay', 'Blind SQLi in payment callback parameter.',
     'sqli', '{"cve":"CVE-2026-31142","cvss":9.8}', now() - interval '11 days', now() - interval '1 hour', 'open', 2),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-2002', 'payment-gateway', 'critical',
     'JWT algorithm confusion', 'Token signing algorithm not pinned; HS256 accepted.',
     'broken_auth', '{"cve":"CVE-2026-29188","cvss":9.2}', now() - interval '10 days', now() - interval '5 hours', 'open', 2),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-2003', 'payment-gateway', 'high',
     'XSS in receipt view', 'Reflected XSS via order reference parameter.',
     'xss', NULL, now() - interval '7 days', now() - interval '2 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-2004', 'payment-gateway', 'medium',
     'CORS misconfiguration', 'Access-Control-Allow-Origin reflects arbitrary origins.',
     'misconfig', NULL, now() - interval '6 days', now() - interval '6 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-2005', 'payment-gateway', 'low',
     'Path traversal in download', 'Unvalidated filename allows traversal outside dir.',
     'path_traversal', NULL, now() - interval '3 days', now() - interval '3 days', 'open', 1),

    -- customer-portal
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-3001', 'customer-portal', 'critical',
     'SSRF via file upload', 'Server fetches user-supplied URLs without allow-listing.',
     'ssrf', '{"cve":"CVE-2026-26554","cvss":7.9}', now() - interval '13 days', now() - interval '8 hours', 'open', 2),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-3002', 'customer-portal', 'high',
     'Insecure direct object reference', 'Object IDs enumerable via /api/v1/users/{id}.',
     'idor', NULL, now() - interval '9 days', now() - interval '2 days', 'in_review', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-3003', 'customer-portal', 'high',
     'Reflected XSS in profile', 'Profile name reflected unescaped into page.',
     'xss', NULL, now() - interval '5 days', now() - interval '1 day', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-3004', 'customer-portal', 'medium',
     'Default credentials on staging', 'Staging instance still on admin/admin.',
     'misconfig', NULL, now() - interval '4 days', now() - interval '4 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-3005', 'customer-portal', 'medium',
     'Weak password policy', 'Minimum length 6, no complexity enforced.',
     'broken_auth', NULL, now() - interval '2 days', now() - interval '2 days', 'open', 1),

    -- document-svc
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-4001', 'document-svc', 'high',
     'XXE in XML parser', 'External entities resolved in document import.',
     'xxe', '{"cve":"CVE-2026-29188","cvss":9.2}', now() - interval '8 days', now() - interval '1 day', 'open', 2),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-4002', 'document-svc', 'high',
     'SQLi in query parameter', 'Unsigned integer cast bypass in filter clause.',
     'sqli', NULL, now() - interval '6 days', now() - interval '3 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-4003', 'document-svc', 'medium',
     'DOM XSS in preview pane', 'Untrusted HTML rendered in iframe preview.',
     'xss', NULL, now() - interval '5 days', now() - interval '5 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-4004', 'document-svc', 'low',
     'Internal paths in error', 'Filesystem paths leaked in error responses.',
     'info_disclosure', NULL, now() - interval '3 days', now() - interval '3 days', 'closed', 1),

    -- internal-hr
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-5001', 'internal-hr', 'high',
     'Login brute force not throttled', 'No rate limiting or lockout on /login.',
     'broken_auth', NULL, now() - interval '7 days', now() - interval '2 days', 'in_review', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-5002', 'internal-hr', 'medium',
     'Stored XSS in HR notes', 'Employee notes rendered without sanitisation.',
     'xss', NULL, now() - interval '4 days', now() - interval '4 days', 'open', 1),
    (gen_random_uuid()::text, 'appscan', 'ASC-2026-5003', 'internal-hr', 'low',
     'TLS 1.1 still enabled', 'Legacy cipher support weakens transport security.',
     'misconfig', NULL, now() - interval '2 days', now() - interval '2 days', 'open', 1)
ON CONFLICT (source, external_id) DO NOTHING;

-- =====================================================================
-- 3) FINDINGS — Imperva DAM database violations
-- =====================================================================
INSERT INTO warehouse.findings
    (id, source, external_id, app_name, severity, title, description, category,
     raw_data, first_seen, last_seen, status, version)
VALUES
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0422', 'DB-CUST-01', 'critical',
     'Unauthorized access attempt', 'Login as sa from non-approved IP 203.0.113.7.',
     'unauth_access', NULL, now() - interval '2 days', now() - interval '5 hours', 'open', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0419', 'DB-CUST-01', 'critical',
     'Data exfiltration pattern', 'SELECT over 1M rows from customers table at 03:00.',
     'data_exfil', NULL, now() - interval '2 days', now() - interval '8 hours', 'open', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0415', 'DB-CUST-01', 'high',
     'SQL injection pattern', 'UNION-based query attempt from application user.',
     'sql_injection', NULL, now() - interval '3 days', now() - interval '1 day', 'in_review', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0410', 'DB-PAY-01', 'high',
     'Privilege escalation', 'GRANT DBA to app user detected in audit log.',
     'privilege_abuse', NULL, now() - interval '3 days', now() - interval '2 days', 'open', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0408', 'DB-PAY-01', 'medium',
     'Anomalous query volume', 'Query rate 5.1x above 30-day baseline.',
     'anomaly', NULL, now() - interval '4 days', now() - interval '4 days', 'open', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0402', 'DB-DOC-01', 'medium',
     'Policy violation on bulk read', 'Bulk SELECT on documents without approval flag.',
     'policy_other', NULL, now() - interval '5 days', now() - interval '5 days', 'open', 1),
    (gen_random_uuid()::text, 'imperva', 'DAM-2026-0395', 'DB-HR-01', 'low',
     'Login outside business hours', 'ETL account active at 02:47 on Sunday.',
     'anomaly', NULL, now() - interval '6 days', now() - interval '6 days', 'closed', 1)
ON CONFLICT (source, external_id) DO NOTHING;

-- =====================================================================
-- 4) FINDINGS — API Security (shadow / exposed endpoints)
-- =====================================================================
INSERT INTO warehouse.findings
    (id, source, external_id, app_name, severity, title, description, category,
     raw_data, first_seen, last_seen, status, version)
VALUES
    (gen_random_uuid()::text, 'apisec', 'API-2026-0117', 'customer-portal', 'critical',
     'Shadow API endpoint discovered', '/api/v3/export exposed without security review.',
     'shadow_api', '{"endpoint":"/api/v3/export","method":"GET"}', now() - interval '6 days', now() - interval '3 hours', 'open', 1),
    (gen_random_uuid()::text, 'apisec', 'API-2026-0112', 'customer-portal', 'high',
     'Admin endpoint externally routable', '/api/v2/admin reachable from public IP.',
     'shadow_api', '{"endpoint":"/api/v2/admin","method":"POST"}', now() - interval '5 days', now() - interval '1 day', 'in_review', 1),
    (gen_random_uuid()::text, 'apisec', 'API-2026-0109', 'payment-gateway', 'medium',
     'No rate limiting on pay endpoint', '/api/v1/pay accepts unlimited requests.',
     'rate_limit', '{"endpoint":"/api/v1/pay","method":"POST"}', now() - interval '4 days', now() - interval '4 days', 'open', 1),
    (gen_random_uuid()::text, 'apisec', 'API-2026-0103', 'document-svc', 'low',
     'Deprecated endpoint not retired', '/api/v1/export still accepting traffic.',
     'shadow_api', '{"endpoint":"/api/v1/export","method":"GET"}', now() - interval '3 days', now() - interval '3 days', 'open', 1)
ON CONFLICT (source, external_id) DO NOTHING;

-- =====================================================================
-- 5) ALERTS — unified alert feed
-- =====================================================================
INSERT INTO warehouse.alerts
    (id, rule_id, title, description, severity, source, target_id, status,
     acknowledged_by, acknowledged_at, dedup_key, dedup_count,
     first_triggered, last_triggered, resolved_at)
VALUES
    (gen_random_uuid()::text, 'risk_critical', 'Fused risk crossed critical threshold',
     'Fused score 78.2 exceeds threshold 71 for legacy-api.', 'critical', 'fusion', 'legacy-api',
     'new', NULL, NULL, 'risk_critical:legacy-api', 4,
     now() - interval '20 hours', now() - interval '1 hour', NULL),
    (gen_random_uuid()::text, 'new_critical_cve', 'New Critical CVE',
     'CVE-2026-31142 (CVSS 9.8) detected in auth module of payment-gateway.', 'critical', 'appscan', 'payment-gateway',
     'new', NULL, NULL, 'cve:CVE-2026-31142', 2,
     now() - interval '22 hours', now() - interval '6 hours', NULL),
    (gen_random_uuid()::text, 'shadow_api_detected', 'Shadow API Detected',
     'New shadow endpoint /api/v3/export discovered on customer-portal.', 'high', 'apisec', 'customer-portal',
     'acknowledged', 'soc@example.com', now() - interval '14 hours', 'shadow:customer-portal', 1,
     now() - interval '26 hours', now() - interval '14 hours', NULL),
    (gen_random_uuid()::text, 'violation_spike', 'Database Violation Spike',
     'Violations 142 vs baseline 28 (5.1x multiplier) on DB-CUST-01.', 'high', 'imperva', 'DB-CUST-01',
     'investigating', 'dbsec@example.com', now() - interval '10 hours', 'spike:DB-CUST-01', 2,
     now() - interval '30 hours', now() - interval '10 hours', NULL),
    (gen_random_uuid()::text, 'connector_auth_failure', 'Connector Auth Failure',
     'Imperva WAF connector returning 401 on poll.', 'critical', 'ingestion', 'imperva_waf',
     'acknowledged', 'sre@example.com', now() - interval '18 hours', 'auth:imperva_waf', 6,
     now() - interval '40 hours', now() - interval '18 hours', NULL),
    (gen_random_uuid()::text, 'appscan_high', 'High severity AppScan finding',
     'Stored XSS in admin console of legacy-api.', 'high', 'appscan', 'legacy-api',
     'new', NULL, NULL, 'appscan_high:ASC-2026-1003', 1,
     now() - interval '6 hours', now() - interval '6 hours', NULL),
    (gen_random_uuid()::text, 'compliance_drop', 'Compliance score drop > 10%',
     'POPIA breach-response domain dropped 8% week over week.', 'high', 'compliance', 'popia',
     'new', NULL, NULL, 'compliance:popia', 1,
     now() - interval '12 hours', now() - interval '12 hours', NULL),
    (gen_random_uuid()::text, 'waf_block_rce', 'WAF blocked RCE attempt',
     'Imperva WAF blocked command injection payload on legacy-api.', 'medium', 'imperva_waf', 'legacy-api',
     'resolved', 'sre@example.com', now() - interval '28 hours', 'waf:rce', 3,
     now() - interval '50 hours', now() - interval '28 hours', now() - interval '26 hours'),
    (gen_random_uuid()::text, 'api_anomaly', 'API traffic anomaly',
     'Traffic to /api/v1/pay up 3.4x; potential scraping.', 'medium', 'apisec', 'payment-gateway',
     'resolved', 'soc@example.com', now() - interval '52 hours', 'api:pay', 1,
     now() - interval '3 days', now() - interval '52 hours', now() - interval '48 hours'),
    (gen_random_uuid()::text, 'risk_monitored', 'Fused risk into monitored band',
     'document-svc moved from safe to monitored band.', 'low', 'fusion', 'document-svc',
     'dismissed', 'exec@example.com', now() - interval '70 hours', 'risk:document-svc', 1,
     now() - interval '4 days', now() - interval '70 hours', now() - interval '68 hours')
ON CONFLICT (id) DO NOTHING;

-- =====================================================================
-- 6) COMPLIANCE — POPIA + ISO 27001 snapshots and gaps
-- =====================================================================
INSERT INTO warehouse.compliance_snapshots
    (id, framework, snapshot_date, overall_score, details, total_controls, passed_controls)
VALUES
    (gen_random_uuid()::text, 'popia', CURRENT_DATE, 84.0,
     '{"data_inventory":88,"consent":76,"breach_response":65,"subject_rights":70,"cross_border":45}',
     117, 98),
    (gen_random_uuid()::text, 'iso_27001', CURRENT_DATE, 72.0,
     '{"A5_policies":80,"A6_org":75,"A8_asset":70,"A9_access":65,"A12_ops":60,"A16_incident":78}',
     130, 94)
ON CONFLICT (id) DO NOTHING;

INSERT INTO warehouse.compliance_gaps
    (id, framework, control_id, domain, description, owner, severity, due_date, status, evidence_count)
VALUES
    (gen_random_uuid()::text, 'popia', 'POPIA-72', 'Cross-Border',
     'Cross-border data transfer not documented or covered by lawful basis.', 'Legal', 'critical',
     CURRENT_DATE + interval '3 days', 'open', 2),
    (gen_random_uuid()::text, 'popia', 'POPIA-22', 'Breach Response',
     'Breach notification procedure untested; notification timelines unverified.', 'CISO', 'high',
     CURRENT_DATE + interval '12 days', 'open', 5),
    (gen_random_uuid()::text, 'popia', 'POPIA-19', 'Consent',
     'Consent records for marketing data incomplete for 2019 cohort.', 'DPO', 'high',
     CURRENT_DATE + interval '20 days', 'in_progress', 8),
    (gen_random_uuid()::text, 'popia', 'POPIA-57', 'Data Subject Rights',
     'Subject access request SLA not instrumented end-to-end.', 'DPO', 'medium',
     CURRENT_DATE + interval '25 days', 'open', 3),
    (gen_random_uuid()::text, 'popia', 'POPIA-63', 'Data Inventory',
     'Data inventory missing classification for 12 new apps.', 'Data Ops', 'medium',
     CURRENT_DATE + interval '30 days', 'in_progress', 4),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.12.6', 'Operations',
     'Vulnerability scan frequency inadequate for production estate.', 'AppSec', 'high',
     CURRENT_DATE + interval '10 days', 'in_progress', 6),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.9.2', 'Access Control',
     'Access review for Q2 not performed for privileged accounts.', 'IT Ops', 'medium',
     CURRENT_DATE + interval '5 days', 'open', 1),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.8.2', 'Asset Management',
     'Asset register missing ownership for 4 shared services.', 'IT Ops', 'medium',
     CURRENT_DATE + interval '18 days', 'open', 2),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.16.1', 'Incident Management',
     'Incident response playbook not tested in last 12 months.', 'CISO', 'high',
     CURRENT_DATE + interval '35 days', 'open', 0),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.5.1', 'Policies',
     'Information security policy review cycle overdue by 60 days.', 'CISO', 'medium',
     CURRENT_DATE - interval '20 days', 'open', 3),
    (gen_random_uuid()::text, 'popia', 'POPIA-11', 'Data Inventory',
     'Data flow map for payment data incomplete.', 'Data Ops', 'medium',
     CURRENT_DATE - interval '10 days', 'open', 2),
    (gen_random_uuid()::text, 'iso_27001', 'ISO-A.9.4', 'Access Control',
     'Privileged session monitoring not enabled on DB-CUST-01.', 'DB Sec', 'high',
     CURRENT_DATE + interval '15 days', 'open', 1)
ON CONFLICT (id) DO NOTHING;

-- =====================================================================
-- 7) CONNECTOR HEALTH — realistic pipeline metrics
-- =====================================================================
INSERT INTO warehouse.connector_health
    (name, source, status, last_poll_at, last_success_at, latency_ms, events_per_hour, error_count, circuit_state)
VALUES
    ('appscan',        'appscan',     'healthy',  now() - interval '2 minutes',  now() - interval '2 minutes',  120,  4200, 0,   'closed'),
    ('imperva_dam',    'imperva',     'healthy',  now() - interval '1 minute',   now() - interval '1 minute',   80,   3800, 1,   'closed'),
    ('imperva_waf',    'imperva',     'healthy',  now() - interval '3 minutes',  now() - interval '3 minutes',  150,  1100, 2,   'closed'),
    ('apisec',         'apisec',      'degraded', now() - interval '4 minutes',  now() - interval '18 minutes', 4000, 680,  14,  'half_open'),
    ('compliance',     'compliance',  'healthy',  now() - interval '5 minutes',  now() - interval '5 minutes',  20,   220,  0,   'closed')
ON CONFLICT (name) DO UPDATE SET
    status = EXCLUDED.status,
    last_poll_at = EXCLUDED.last_poll_at,
    last_success_at = EXCLUDED.last_success_at,
    latency_ms = EXCLUDED.latency_ms,
    events_per_hour = EXCLUDED.events_per_hour,
    error_count = EXCLUDED.error_count,
    circuit_state = EXCLUDED.circuit_state;

-- =====================================================================
-- 8) API ENDPOINTS — exposure inventory
-- =====================================================================
INSERT INTO warehouse.api_endpoints
    (id, app_name, endpoint, method, is_shadow, exposure_score, discovered_at, last_seen)
VALUES
    (gen_random_uuid()::text, 'customer-portal', '/api/v3/export', 'GET',    TRUE,  85.0, now() - interval '6 days',  now() - interval '1 hour'),
    (gen_random_uuid()::text, 'customer-portal', '/api/v2/admin',   'POST',  TRUE,  70.0, now() - interval '5 days',  now() - interval '1 day'),
    (gen_random_uuid()::text, 'payment-gateway', '/api/v1/pay',     'POST',  FALSE, 45.0, now() - interval '30 days', now() - interval '2 hours'),
    (gen_random_uuid()::text, 'document-svc',    '/api/v1/export',  'GET',   FALSE, 20.0, now() - interval '60 days', now() - interval '3 days'),
    (gen_random_uuid()::text, 'legacy-api',      '/soap/login',     'POST',  FALSE, 60.0, now() - interval '90 days', now() - interval '4 hours'),
    (gen_random_uuid()::text, 'payment-gateway', '/api/v1/refunds', 'POST',  FALSE, 30.0, now() - interval '45 days', now() - interval '6 hours')
ON CONFLICT (id) DO NOTHING;

-- =====================================================================
-- 9) DEAD LETTER QUEUE — rejected records for SRE/admin
-- =====================================================================
INSERT INTO staging.batch_runs
    (id, connector, source, started_at, finished_at, records_fetched, records_valid, records_rejected, status)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'imperva_waf', 'imperva',
     now() - interval '7 hours', now() - interval '6 hours', 1200, 1196, 4, 'completed'),
    ('22222222-2222-2222-2222-222222222222', 'apisec',       'apisec',
     now() - interval '6 hours', now() - interval '5 hours', 800, 799, 1, 'completed'),
    ('33333333-3333-3333-3333-333333333333', 'appscan',      'appscan',
     now() - interval '4 hours', now() - interval '3 hours', 500, 499, 1, 'completed'),
    ('44444444-4444-4444-4444-444444444444', 'compliance',   'compliance',
     now() - interval '26 hours', now() - interval '25 hours', 300, 299, 1, 'completed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO staging.rejected_records
    (id, batch_id, source, raw_payload, rejection_reason, rejection_code, rejected_at, reprocessed)
VALUES
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'imperva_waf',
     '{"rule":"SQLi","app":"legacy-api","action":"block","src_ip":"203.0.113.9"}',
     'Missing mandatory field: src_ip', 'ERR_MISSING_FIELD', now() - interval '6 hours', FALSE),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 'apisec',
     '{"endpoint":"/api/v3/export","method":"GET","exposure":85}',
     'Payload exceeds size limit', 'ERR_TOO_LARGE', now() - interval '5 hours', FALSE),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', 'appscan',
     '{"title":"SQL Injection","severity":"critical"}',
     'External ID conflicts with existing record', 'ERR_DUPLICATE', now() - interval '3 hours', FALSE),
    (gen_random_uuid(), '44444444-4444-4444-4444-444444444444', 'compliance',
     '{"framework":"popia","control":"POPIA-19"}',
     'Unsupported control id for framework', 'ERR_SCHEMA', now() - interval '1 day', TRUE)
ON CONFLICT (id) DO NOTHING;
