
const details = {
  root: {
    title: 'sita-platform',
    badge: 'root',
    body: String.raw`
      <p>A full-stack security pipeline platform that ingests findings from <strong>multiple OEM security tools</strong> (HCL AppScan, Imperva DAM/WAF, API Security platform, compliance CSV sources), normalises and deduplicates them into a <strong>central PostgreSQL database</strong>, runs risk scoring and alert engines against the warehouse, and serves <strong>reports via REST API</strong> to a React frontend. Alerts are also dispatched out-of-band through Email, PagerDuty, or Microsoft Teams.</p>
      <h3>Data flow: OEMs &rarr; Pipeline &rarr; Database &rarr; Reports</h3>
      <p><code>OEM Tools</code> <span class="flow-arrow">&rarr;</span> <code>Connectors</code> <span class="flow-arrow">&rarr;</span> <code>Ingestion</code> <span class="flow-arrow">&rarr;</span> <code>staging.raw_records</code> <span class="flow-arrow">&rarr;</span> <code>Normaliser</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.findings</code> <span class="flow-arrow">&rarr;</span> <code>Alert/Risk/Compliance Engines</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.*</code> <span class="flow-arrow">&rarr;</span> <code>API</code> <span class="flow-arrow">&rarr;</span> <code>Reports UI</code></p>
      <h3>Key directories</h3>
      <ul>
        <li><code>C:\sita-platform\.github\</code> &mdash; CI pipeline</li>
        <li><code>C:\sita-platform\backend\</code> &mdash; Python/FastAPI API server</li>
        <li><code>C:\sita-platform\frontend\</code> &mdash; React/TypeScript dashboard</li>
        <li><code>C:\sita-platform\infrastructure\</code> &mdash; Docker, nginx, monitoring, deploy scripts</li>
        <li><code>&#128202; reporting interface</code> &mdash; the final product: role-based dashboards for all users (click the tree item below)</li>
      </ul>
      <h3>Demo data</h3>
      <p>The database is populated by <code>C:\sita-platform\infrastructure\scripts\seed-demo.sql</code> so every dashboard renders realistic content: 150 rows of 30-day risk trends, 36 findings (AppScan / Imperva DAM / API Security), 36 alerts, POPIA + ISO 27001 snapshots and gaps, connector health, shadow-API endpoints, and DLQ records.</p>
    `
  },
  github: {
    title: '.github',
    badge: 'CI / CD',
    body: String.raw`
      <p>Contains the CI workflow configuration for GitHub Actions.</p>
      <h3>Files</h3>
      <div class="file-list"><span class="file-tag">CODEOWNERS</span><span class="file-tag">ci.yml</span></div>
      <ul>
        <li><code>C:\sita-platform\.github\CODEOWNERS</code> &mdash; Defines which teams/users are responsible for code review on each path.</li>
        <li><code>C:\sita-platform\.github\workflows\ci.yml</code> &mdash; GitHub Actions CI pipeline. Likely runs linting, type-checking, tests, and builds for both backend and frontend on every push/PR.</li>
      </ul>
    `
  },
  backend: {
    title: 'backend',
    badge: 'FastAPI &middot; Python',
    body: String.raw`
      <p>The Python backend built with FastAPI. It orchestrates the entire pipeline: <strong>pulls raw data from OEM tools</strong> via connectors, normalises it into the PostgreSQL warehouse, runs processing engines that write results back to the database, and finally <strong>serves reports via REST API</strong> by reading directly from the warehouse tables.</p>
      <h3>Layers</h3>
      <ul>
        <li><code>C:\sita-platform\backend\app\main.py</code> &mdash; FastAPI application entry point.</li>
        <li><code>C:\sita-platform\backend\app\config.py</code> &mdash; Central configuration (env-based).</li>
        <li><code>C:\sita-platform\backend\app\api\</code> &mdash; REST layer: routers (<code>alerts</code>, <code>findings</code>, <code>risks</code>, <code>compliance</code>, <code>admin</code>, <code>dashboard</code>, <code>benchmark</code> (provincial peer comparison), <code>exports_ag</code> (Auditor-General signed export)), Pydantic <code>schemas/</code>, auth deps, and error handling. <strong>Every endpoint queries the warehouse DB</strong> to serve report data.</li>
        <li><code>C:\sita-platform\backend\app\connectors\</code> &mdash; Adapters for OEM security tools: <code>appscan</code> (HCL), <code>apisec</code>, <code>imperva</code>, and <code>compliance</code> (CSV/API). All extend a <code>base</code> connector.</li>
        <li><code>C:\sita-platform\backend\app\ingestion\</code> &mdash; Reliable data intake from OEMs with <code>circuit_breaker</code>, <code>retry</code>, <code>token_bucket</code> rate limiting, a <code>scheduler</code>, and a dead-letter queue (<code>dlq</code>). Writes raw payloads to <code>staging.raw_records</code>.</li>
        <li><code>C:\sita-platform\backend\app\bus\</code> &mdash; Internal event stream producer/consumer used to hand records between the ingestion, processing, and analytics stages.</li>
        <li><code>C:\sita-platform\backend\app\lake\</code> &mdash; Raw-record writer that persists OEM payloads before normalisation.</li>
        <li><code>C:\sita-platform\backend\app\processing\</code> &mdash; Core pipeline: <code>normaliser</code> (canonical field mapping via <code>field_mapper.yaml</code>), <code>alert_dedup</code>, <code>alert_enricher</code>, <code>alert_engine</code> (rule-based via <code>alert_rules.yaml</code>), <code>risk_engine</code> + <code>risk_aggregator</code>, and <code>compliance</code> checks. <strong>Reads from and writes to warehouse tables.</strong></li>
        <li><code>C:\sita-platform\backend\app\dispatch\</code> &mdash; Notifications via <code>email_adapter</code>, <code>pagerduty_adapter</code>, <code>teams_adapter</code>, routed through a background <code>worker</code>.</li>
        <li><code>C:\sita-platform\backend\app\models\</code> &mdash; SQLAlchemy ORM models mapping to warehouse tables (<code>alert</code>, <code>finding</code>, <code>risk_score</code>, <code>compliance</code>, <code>connector_status</code>, <code>dlq</code>), plus <code>tenant.py</code> (<code>Department</code>/<code>Branch</code>).</li>
        <li><code>C:\sita-platform\backend\app\tenant.py</code> &mdash; the government multi-tenancy catalog (<code>Department &rarr; Branch &rarr; App</code>) that drives REST scoping and delegated admin tiers.</li>
        <li><code>C:\sita-platform\backend\app\entrypoints\</code> &mdash; Runnable entry points for each long-running process (ingestion, processing, dispatch, analytics) used by the Docker Compose services.</li>
        <li><code>C:\sita-platform\backend\app\monitoring\</code> &mdash; Structured <code>logging</code> and Prometheus <code>metrics</code>.</li>
        <li><code>C:\sita-platform\backend\migrations\</code> &mdash; Alembic database migration config.</li>
      </ul>
      <h3>OEM &rarr; Pipeline &rarr; DB &rarr; Reports flow</h3>
      <p><code>OEM Connector</code> <span class="flow-arrow">&rarr;</span> <code>Ingestion</code> (circuit-breaker/retry/DLQ) <span class="flow-arrow">&rarr;</span> <code>staging.raw_records</code> <span class="flow-arrow">&rarr;</span> <code>Normaliser</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.findings</code> <span class="flow-arrow">&rarr;</span> <code>Alert Engine</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.alerts</code> <span class="flow-arrow">&rarr;</span> <code>Risk Engine</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.risk_scores</code> <span class="flow-arrow">&rarr;</span> <code>API reads warehouse</code> <span class="flow-arrow">&rarr;</span> <code>Report UI</code></p>
    `
  },
  frontend: {
    title: 'frontend',
    badge: 'React &middot; TypeScript &middot; Vite',
    body: String.raw`
      <p>A single-page application built with React, TypeScript, and Vite. Authenticated users log in with a role, and the app renders that role's dashboard. <strong>All dashboard numbers come from the backend REST API, which reads PostgreSQL</strong> — there is no hardcoded sample data in the UI.</p>
      <h3>Structure</h3>
      <ul>
        <li><code>C:\sita-platform\frontend\src\api\</code> &mdash; Typed API client modules: <code>client.ts</code> (axios, JWT from localStorage, 401 redirect), plus domain files for <code>alerts</code>, <code>findings</code>, <code>risks</code>, <code>compliance</code>, <code>dashboard</code>, <code>admin</code>.</li>
        <li><code>C:\sita-platform\frontend\src\components\dashboard\</code> &mdash; Reusable widgets: <code>StatCard</code>, <code>Panel</code>, <code>Gauge</code>, <code>MiniBarChart</code>, <code>BarRow</code>, <code>Chip</code>, <code>OemTag</code>, <code>DashHeader</code>, <code>ExplainOverlay</code>.</li>
        <li><code>C:\sita-platform\frontend\src\components\layout\RoleNav.tsx</code> &mdash; Role-aware navigation sidebar.</li>
        <li><code>C:\sita-platform\frontend\src\context\AuthContext.tsx</code> &mdash; Auth state provider; demo accounts map to roles; token minted via <code>src\utils\jwt.ts</code>.</li>
        <li><code>C:\sita-platform\frontend\src\hooks\</code> &mdash; Data hooks: <code>useExecData</code>, <code>useSocData</code>, <code>useAppSecData</code>, <code>useDbSecData</code>, <code>useComplianceData</code>, <code>useSreData</code>, built on the generic <code>useApi</code> fetcher.</li>
        <li><code>C:\sita-platform\frontend\src\data\</code> &mdash; <code>mappers.ts</code> (severity/bucket/status color mapping) and <code>explanations.ts</code> (dynamic "how this dashboard is built" narratives built from live API facts).</li>
        <li><code>C:\sita-platform\frontend\src\pages\</code> &mdash; Six role-gated dashboards: <code>ExecDashboard</code>, <code>SocDashboard</code>, <code>AppSecDashboard</code>, <code>DbSecDashboard</code>, <code>ComplianceDashboard</code>, <code>SreDashboard</code>, plus <code>LoginPage</code>.</li>
        <li><code>C:\sita-platform\frontend\src\utils\</code> &mdash; <code>constants.ts</code>, <code>formatters.ts</code>, and <code>jwt.ts</code> (mints the demo JWT with <code>aud: ""</code>).</li>
      </ul>
      <h3>Routing &amp; data flow</h3>
      <p><code>LoginPage</code> <span class="flow-arrow">&rarr;</span> <code>AuthContext</code> (role JWT) <span class="flow-arrow">&rarr;</span> <code>RoleNav</code> <span class="flow-arrow">&rarr;</span> role dashboard <span class="flow-arrow">&rarr;</span> <code>useXData</code> hook <span class="flow-arrow">&rarr;</span> <code>/api/v1/*</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.*</code> tables</p>
    `
  },
  infrastructure: {
    title: 'infrastructure',
    badge: 'Docker &middot; nginx &middot; Prometheus &middot; Grafana',
    body: String.raw`
      <p>Container orchestration, reverse proxy, monitoring stack, and operational scripts for deploying and running the platform.</p>
      <h3>Components</h3>
      <ul>
        <li><code>C:\sita-platform\infrastructure\docker-compose.yml</code> &mdash; Local stack: postgres + redis + backend + frontend + ingestion/processing/dispatch/analytics services + nginx.</li>
        <li><code>C:\sita-platform\infrastructure\docker-compose.prod.yml</code> &mdash; Production overrides (resource limits, secrets, replicas).</li>
        <li><code>C:\sita-platform\infrastructure\nginx\sita.conf</code> &mdash; Reverse proxy config routing <code>/api/*</code> and <code>/admin/*</code> to the backend and serving the frontend SPA.</li>
        <li><code>C:\sita-platform\infrastructure\monitoring\prometheus.yml</code> &mdash; Prometheus scrape config targeting the backend metrics endpoint.</li>
        <li><code>C:\sita-platform\infrastructure\monitoring\grafana-dashboards\sita-pipeline.json</code> &mdash; Pre-built Grafana dashboard for pipeline health, throughput, error rates, and latency.</li>
        <li><code>C:\sita-platform\infrastructure\scripts\deploy.sh</code> &mdash; Deployment script (pull images, run migrations, restart services).</li>
        <li><code>C:\sita-platform\infrastructure\scripts\backup.sh</code> &mdash; Database and config backup.</li>
        <li><code>C:\sita-platform\infrastructure\scripts\init-db.sql</code> &mdash; Initial schema: <code>staging</code>, <code>warehouse</code>, <code>archive</code>, <code>audit</code> schemas and tables.</li>
        <li><code>C:\sita-platform\infrastructure\scripts\seed-demo.sql</code> &mdash; Demo seed (idempotent via <code>ON CONFLICT</code>) filling every warehouse table so the dashboards render realistic data.</li>
      </ul>
      <h3>Architecture</h3>
      <p><code>Browser</code> <span class="flow-arrow">&rarr;</span> <code>nginx :80</code> <span class="flow-arrow">&rarr;</span> <code>/api/* &rarr; backend :8000</code> &nbsp;|&nbsp; <code>/ &rarr; frontend (static files)</code></p>
      <p><code>Prometheus</code> <span class="flow-arrow">&rarr;</span> scrapes <code>backend/metrics</code> <span class="flow-arrow">&rarr;</span> <code>Grafana</code> visualises</p>
    `
  },
  reporting: {
    title: 'Reporting Interface',
    badge: 'final product &mdash; 6 role-gated views',
    body: String.raw`
      <p>The reporting interface is the end-user facing product. It surfaces all processed data &mdash; alerts, findings, risk scores, compliance status &mdash; through <strong>six role-gated dashboards</strong> in the React SPA, plus a Grafana dashboard for operational health monitoring. <strong>Every displayed number is queried from the PostgreSQL warehouse via the REST API.</strong></p>

      <h3>Architecture: OEMs &rarr; Pipeline &rarr; Database &rarr; Reports</h3>
      <p>Data flows through three distinct stages before reaching the user:</p>
      <ol>
        <li><strong>OEM ingestion</strong> &mdash; connectors pull raw findings from HCL AppScan, Imperva DAM/WAF, API Security platform, and compliance CSV sources into <code>staging.raw_records</code></li>
        <li><strong>Pipeline processing</strong> &mdash; the normaliser, alert engine, risk engine, and compliance engine read from staging, transform/deduplicate/enrich, and write results into the <code>warehouse</code> schema</li>
        <li><strong>Database &rarr; Reports</strong> &mdash; the REST API queries <code>warehouse.*</code> tables directly; the React frontend pages render these query results as reports. <em>Reports never read from the live pipeline or staging tables.</em></li>
      </ol>

      <h3>Database schema (PostgreSQL)</h3>
      <p>Defined in <code>C:\sita-platform\infrastructure\scripts\init-db.sql</code>. All reports query only the <code>warehouse</code> schema:</p>
      <ul>
        <li><code>staging</code> &mdash; raw OEM ingestion: <code>batch_runs</code>, <code>raw_records</code> (JSONB, 7-day TTL), <code>rejected_records</code> (DLQ, 30-day TTL). <em>Only the DLQ is exposed to reports (SRE admin).</em></li>
        <li><code>warehouse</code> &mdash; normalised data for reporting: <code>connector_health</code>, <code>findings</code>, <code>alerts</code>, <code>risk_scores</code>, <code>compliance_snapshots</code>, <code>compliance_gaps</code>, <code>api_endpoints</code>. <strong>This is what all reports query.</strong></li>
        <li><code>archive</code> &mdash; historical retention</li>
        <li><code>audit</code> &mdash; governance trail</li>
      </ul>
      <p>TTL cleanup via <code>pg_cron</code> nightly at 2 AM.</p>

      <h3>End-to-end flow: OEM &rarr; Pipeline &rarr; DB &rarr; Report</h3>
      <p><code>OEM Tools</code> <span class="flow-arrow">&rarr;</span> <code>Connectors</code> <span class="flow-arrow">&rarr;</span> <code>staging.raw_records</code> <span class="flow-arrow">&rarr;</span> <code>Normaliser</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.findings</code> <span class="flow-arrow">&rarr;</span> <code>Processing Engines</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.alerts/risk_scores/compliance_*</code> <span class="flow-arrow">&rarr;</span> <code>API queries warehouse</code> <span class="flow-arrow">&rarr;</span> <code>Report UI</code></p>

      <h3>Demo data (seed-demo.sql)</h3>
      <p>Run once against the live database (<code>docker exec -i infrastructure-postgres-1 psql -U sita -d sita &lt; infrastructure\\scripts\\seed-demo.sql</code>). Idempotent <code>ON CONFLICT</code> upserts produce:</p>
      <ul>
        <li><strong>150 risk-score rows</strong> &mdash; 30-day fused-risk trends for legacy-api (critical), payment-gateway (monitored), customer-portal, document-svc, internal-hr</li>
        <li><strong>36 findings</strong> &mdash; 27 AppScan (SQLi/RCE/XSS/IDOR/SSRF/XXE + CVE-2026 CVEs), 7 Imperva DAM, 4 API-Security (shadow APIs)</li>
        <li><strong>36 alerts</strong> &mdash; risk_critical, new_critical_cve, shadow_api_detected, violation_spike, connector_auth_failure, compliance_drop, WAF/RCE, etc.</li>
        <li><strong>Compliance</strong> &mdash; POPIA (84%) + ISO 27001 (72%) snapshots and 12 gaps, some overdue</li>
        <li><strong>Operational</strong> &mdash; 5 connector-health rows (apisec degraded), 6 API endpoints (2 shadow), 4 DLQ records + batch runs</li>
      </ul>

      <h3>Role-based dashboard access</h3>
      <p>Access is controlled by JWT role claims. The backend RBAC hierarchy (<code>C:\sita-platform\backend\app\api\auth.py</code>) grants each role specific API permissions, and <code>RoleNav</code> (<code>C:\sita-platform\frontend\src\components\layout\RoleNav.tsx</code>) renders only the routes each role may open:</p>
      <ul>
        <li><strong>Executive</strong> (<code>exec</code>) &mdash; <code>ExecDashboard</code>: fused risk, findings, compliance gauges, alerts</li>
        <li><strong>SOC Analyst</strong> (<code>soc</code>) &mdash; <code>SocDashboard</code>: unified alert timeline, alert queue, findings</li>
        <li><strong>AppSec</strong> (<code>appsec</code>) &mdash; <code>AppSecDashboard</code>: findings by app/severity, OWASP categories, critical CVEs</li>
        <li><strong>DB Security</strong> (<code>dbsec</code>) &mdash; <code>DbSecDashboard</code>: database violations, categories, active DAM alerts</li>
        <li><strong>Compliance Officer</strong> (<code>compliance</code>) &mdash; <code>ComplianceDashboard</code>: POPIA/ISO scores, audit gaps, evidence</li>
        <li><strong>SRE</strong> (<code>sre</code>) &mdash; <code>SreDashboard</code>: connector health, throughput, error rate, DLQ</li>
      </ul>

      <h3>Page-by-page breakdown</h3>

      <h3 style="color:rgb(var(--amber))">&#128202; ExecDashboard (/exec)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\ExecDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /api/v1/dashboard/summary</code>, <code>/api/v1/risks</code>, <code>/api/v1/findings</code>, <code>/api/v1/compliance</code>, <code>/api/v1/alerts</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.risk_scores</code>, <code>warehouse.alerts</code>, <code>warehouse.findings</code></p>
      <p>The executive landing dashboard. Displays KPI cards, a 30-day fused-risk trend, compliance gauges, severity donut, application heatmap, top-5 risk table, and a live alert summary &mdash; all computed from warehouse queries:</p>
      <ul>
        <li><strong>Fused Risk Score</strong> &mdash; composite score (0&ndash;100) across all monitored apps</li>
        <li><strong>Open Findings</strong> &mdash; total unfixed vulnerabilities from <code>warehouse.findings</code></li>
        <li><strong>POPIA / ISO gauges</strong> &mdash; from <code>warehouse.compliance_snapshots</code></li>
        <li><strong>Active Alerts</strong> &mdash; unacknowledged alert count from <code>warehouse.alerts</code></li>
      </ul>

      <h3 style="color:rgb(var(--amber))">&#128680; SocDashboard (/soc)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\SocDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /api/v1/alerts</code>, <code>PATCH /api/v1/alerts/{id}/acknowledge</code>, <code>PATCH /api/v1/alerts/{id}/resolve</code>, <code>GET /api/v1/findings</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.alerts</code>, <code>warehouse.findings</code></p>
      <p>The SOC incident view reads from <code>warehouse.alerts</code>: a chronological timeline, an alert queue with acknowledge/resolve actions (PATCH writes status back to the DB), and a findings table.</p>
      <p>Alerts are generated by <code>AlertRuleEngine</code> (<code>C:\sita-platform\backend\app\processing\alert_engine.py</code>), deduplicated by <code>AlertDeduplicator</code> (<code>alert_dedup.py</code>), enriched by <code>AlertEnricher</code> (<code>alert_enricher.py</code>), and dispatched to Email/PagerDuty/Teams via <code>DispatchWorker</code> (<code>C:\sita-platform\backend\app\dispatch\worker.py</code>).</p>

      <h3 style="color:rgb(var(--amber))">&#128269; AppSecDashboard (/appsec)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\AppSecDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /api/v1/findings</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.findings</code></p>
      <p>Raw vulnerability findings from all connected OEMs, grouped by application and by OWASP category, plus a critical-findings list. Columns from <code>warehouse.findings</code> (<code>id</code>, <code>source</code>, <code>external_id</code>, <code>app_name</code>, <code>severity</code>, <code>title</code>, <code>category</code>, <code>raw_data</code>, <code>first_seen</code>, <code>last_seen</code>, <code>status</code>). Data arrives via OEM connectors into <code>staging.raw_records</code>, normalised by <code>Normaliser</code> (<code>C:\sita-platform\backend\app\processing\normaliser.py</code>) via <code>field_mapper.yaml</code>, and lands in <code>warehouse.findings</code>.</p>

      <h3 style="color:rgb(var(--amber))">&#128737;&#65039; DbSecDashboard (/dbsec)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\DbSecDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /api/v1/findings</code> (source=imperva), <code>GET /api/v1/alerts</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.findings</code>, <code>warehouse.alerts</code></p>
      <p>Imperva DAM database violations per DB server (DB-CUST-01, DB-PAY-01, DB-DOC-01, DB-HR-01), violation categories, alert activity, and the active database alert table.</p>

      <h3 style="color:rgb(var(--amber))">&#128203; ComplianceDashboard (/compliance)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\ComplianceDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /api/v1/compliance</code>, <code>GET /api/v1/compliance/gaps</code>, <code>GET /api/v1/compliance/evidence</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.compliance_snapshots</code>, <code>warehouse.compliance_gaps</code></p>
      <p>Dual-framework compliance dashboard reading from <code>warehouse.compliance_snapshots</code> and <code>warehouse.compliance_gaps</code>:</p>
      <ul>
        <li><strong>POPIA Readiness</strong> &mdash; weighted score (<code>framework='popia'</code>, <code>overall_score</code>, <code>details</code> JSONB)</li>
        <li><strong>ISO 27001 Progress</strong> &mdash; (<code>framework='iso_27001'</code>)</li>
        <li><strong>Compliance Gaps</strong> &mdash; control gaps with severity, owner, due date, status, evidence count</li>
        <li><strong>Evidence Collection</strong> &mdash; <em>computed from the gaps table</em>: available = gaps with <code>evidence_count &gt; 0</code>, missing = the rest, expiring = non-closed gaps due within 30 days</li>
      </ul>
      <p>Computed by <code>C:\sita-platform\backend\app\processing\compliance.py</code> and upserted into the warehouse.</p>

      <h3 style="color:rgb(var(--amber))">&#9881;&#65039; SreDashboard (/sre)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\frontend\src\pages\SreDashboard.tsx</code> &nbsp;|&nbsp; <strong>API:</strong> <code>GET /admin/connectors</code>, <code>GET /admin/dead-letter</code>, <code>POST /admin/connectors/{name}/reset</code>, <code>POST /admin/dead-letter/reprocess/{id}</code> &nbsp;|&nbsp; <strong>DB:</strong> <code>warehouse.connector_health</code>, <code>staging.rejected_records</code></p>
      <p>Operational views for SRE:</p>
      <ul>
        <li><strong>Connector Health</strong> &mdash; reads <code>warehouse.connector_health</code> (status, circuit state, latency, events/hour, errors); the API Security connector is seeded as <code>degraded</code></li>
        <li><strong>Dead-Letter Queue</strong> &mdash; reads <code>staging.rejected_records</code> (rejection reason, code, source, reprocessed flag)</li>
        <li><strong>Reset / Reprocess</strong> actions to recover from OEM connector failures</li>
      </ul>

      <h3>"Explain this dashboard" overlays</h3>
      <p>Every dashboard header exposes <strong>Explain</strong> and <strong>Layman's Guide</strong> buttons. The narrative is generated by <code>C:\sita-platform\frontend\src\data\explanations.ts</code> (<code>buildExplain</code> / <code>buildLayman</code>), which interpolates the <em>live</em> numbers from each dashboard's hook &mdash; no hardcoded figures.</p>

      <h3>Alert dispatch (out-of-band reporting)</h3>
      <p>Beyond the UI, critical/high alerts are pushed via <code>DispatchWorker</code> (<code>C:\sita-platform\backend\app\dispatch\worker.py</code>):</p>
      <ul>
        <li><code>C:\sita-platform\backend\app\dispatch\email_adapter.py</code> &mdash; HTML email via Jinja2</li>
        <li><code>C:\sita-platform\backend\app\dispatch\teams_adapter.py</code> &mdash; Microsoft Teams MessageCard</li>
        <li><code>C:\sita-platform\backend\app\dispatch\pagerduty_adapter.py</code> &mdash; PagerDuty Events API v2</li>
      </ul>
      <p>Critical/high fire on all three; medium/low go to email + Teams only.</p>

      <h3>Grafana dashboard (infrastructure monitoring)</h3>
      <p><strong>File:</strong> <code>C:\sita-platform\infrastructure\monitoring\grafana-dashboards\sita-pipeline.json</code></p>
      <p>Visualises Prometheus metrics from <code>C:\sita-platform\backend\app\monitoring\metrics.py</code>: connector poll rates, ingestion throughput, normalisation outcomes, API latency, alert rule firings, active alert counts.</p>

      <h3>Key design observations</h3>
      <ul>
        <li>No CSV/PDF export &mdash; reporting is on-screen only</li>
        <li>No charting library used in the dashboards (recharts in package.json but not imported; custom CSS charts instead)</li>
        <li>All API endpoints query PostgreSQL; no hardcoded report data remains</li>
        <li>Most complete aggregation: <code>fused_risk()</code> in <code>risk_engine.py</code></li>
        <li>TTL lifecycle: <code>staging.raw_records</code> purged after 7 days, DLQ after 30 via <code>pg_cron</code></li>
      </ul>
    `
  },
  ingest: {
    title: 'Stage 1 — OEM Ingestion',
    badge: 'pull & persist raw',
    body: String.raw`
      <p><strong>Purpose:</strong> Pull raw security data from each OEM tool and persist it, untouched, into <code>staging.raw_records</code> so nothing is lost and the pipeline can be replayed.</p>
      <h3>How it works</h3>
      <ol>
        <li><strong>Connector</strong> (<code>C:\sita-platform\backend\app\connectors\</code>) — one adapter per OEM: <code>appscan.py</code> (HCL AppScan), <code>imperva.py</code> (DAM/WAF), <code>apisec.py</code> (API security), <code>compliance.py</code> (CSV/API). Each extends <code>base.py</code>.</li>
        <li><strong>Ingestion hardening</strong> (<code>C:\sita-platform\backend\app\ingestion\</code>) — <code>circuit_breaker.py</code> stops hammering a failing OEM, <code>retry.py</code> back-off, <code>token_bucket.py</code> rate limiting, <code>scheduler.py</code> cadence.</li>
        <li><strong>Dead-letter queue</strong> (<code>dlq.py</code>) — records that fail validation go to <code>staging.rejected_records</code> instead of being dropped.</li>
        <li><strong>Persist</strong> — the <code>lake/writer.py</code> writes each raw payload (JSONB) plus a <code>batch_run</code> record into the <code>staging</code> schema (7-day TTL).</li>
      </ol>
      <h3>Tables touched</h3>
      <div class="file-list"><span class="file-tag">staging.batch_runs</span><span class="file-tag">staging.raw_records</span><span class="file-tag">staging.rejected_records</span></div>
<p><em>Run as its own container/service: <code>C:\sita-platform\backend\app\entrypoints\ingestion.py</code>.</em></p>
    `
  },
  oem: {
    title: 'OEM Tools',
    badge: 'external security sources',
    body: String.raw`
      <p><strong>What this is:</strong> The third-party security tools that produce raw findings. These are the <em>source</em> systems feeding the pipeline &mdash; nothing in the platform generates data on its own.</p>
      <h3>The connected OEMs</h3>
      <ul>
        <li><strong>HCL AppScan</strong> &mdash; application security / SAST &amp; DAST scanning (SQLi, RCE, XSS, IDOR, SSRF, XXE + CVE-2026 CVEs); pulled by <code>backend\app\connectors\appscan.py</code>.</li>
        <li><strong>Imperva DAM / WAF</strong> &mdash; database activity monitoring and web-app firewall events (DB-CUST-01, DB-PAY-01, DB-DOC-01, DB-HR-01); pulled by <code>backend\app\connectors\imperva.py</code>.</li>
        <li><strong>API Security platform</strong> &mdash; discovers shadow APIs and API risk; pulled by <code>backend\app\connectors\apisec.py</code>.</li>
        <li><strong>Compliance sources</strong> &mdash; CSV / API feeds of compliance posture; pulled by <code>backend\app\connectors\compliance.py</code>.</li>
      </ul>
      <h3>Role in the flow</h3>
      <p>Each OEM exposes its findings over its own API; the pipeline never touches these tools directly &mdash; it talks to them <em>only through its connector adapters</em>. Data leaves the OEM as raw JSON/CSV and enters <code>staging.raw_records</code> untouched.</p>
    `
  },
  connectors: {
    title: 'Connectors',
    badge: 'one adapter per OEM',
    body: String.raw`
      <p><strong>Purpose:</strong> Bridging code that adapts each OEM tool&rsquo;s API into a uniform interface, so the rest of the pipeline talks to a single contract instead of each vendor&rsquo;s quirks.</p>
      <h3>Location</h3>
      <p><code>C:\sita-platform\backend\app\connectors\</code> &mdash; every connector extends <code>base.py</code> (shared fetch/auth/parse logic):</p>
      <div class="file-list"><span class="file-tag">appscan.py</span><span class="file-tag">imperva.py</span><span class="file-tag">apisec.py</span><span class="file-tag">compliance.py</span><span class="file-tag">base.py</span></div>
      <ul>
        <li><code>base.py</code> &mdash; common interface &amp; retry hooks</li>
        <li><code>appscan.py</code> &mdash; HCL AppScan findings</li>
        <li><code>imperva.py</code> &mdash; Imperva DAM/WAF events</li>
        <li><code>apisec.py</code> &mdash; API security / shadow-API risks</li>
        <li><code>compliance.py</code> &mdash; compliance CSV/API feeds</li>
      </ul>
      <h3>Important</h3>
      <p>Connectors only <strong>pull</strong>. Any robustness (retries, rate limiting, circuit breaking, dead-lettering) is layered on by <code>backend\app\ingestion\</code>, not here &mdash; so a connector stays thin and focused purely on translation.</p>
    `
  },
  synthetic: {
    title: 'synthetic',
    badge: 'simulated OEM feed',
    body: String.raw`
      <p><strong>Purpose:</strong> Deterministic stand-in for the live OEM connectors while tenant/API access is pending. Emits payloads shaped exactly like each real connector&rsquo;s <code>poll()</code> output so every downstream stage runs and is tested before live access exists.</p>
      <h3>Files</h3>
      <div class="file-list"><span class="file-tag">generator.py</span><span class="file-tag">__init__.py</span></div>
      <ul>
        <li><code>C:\sita-platform\backend\app\synthetic\generator.py</code> &mdash; <code>SyntheticOEMFeed</code> (deterministic, seed=42) with per-source generators <code>appscan_finding</code>, <code>imperva_dam_event</code>, <code>imperva_waf_event</code>, <code>apisec_endpoint</code>, <code>compliance_row</code>, and <code>batch()</code>/<code>sample()</code>.</li>
        <li><code>C:\sita-platform\backend\tests\fixtures\</code> &mdash; OEM-shaped JSON fixtures (3 records each) used by the pytest suite and the seed pipeline.</li>
      </ul>
      <h3>Why it is safe to build on</h3>
      <ul>
        <li><strong>Field-shape parity</strong> &mdash; mirrors the connector contracts in <code>backend\app\connectors\</code>, so switching to live data is a source swap, not a rewrite.</li>
        <li><strong>Deterministic &amp; replayable</strong> &mdash; fixed seed gives reproducible fixtures and stable test expectations.</li>
        <li><strong>Downstream untouched</strong> &mdash; everything after <code>staging.raw_records</code> consumes JSONB payloads regardless of producer.</li>
      </ul>
      <h3>How the live feed replaces it</h3>
      <p><code>SyntheticOEMFeed</code> <span class="flow-arrow">&rarr;</span> <code>seed_simulated.py</code> <span class="flow-arrow">&rarr;</span> <code>staging.raw_records</code>. On cutover, <code>entrypoints\ingestion.py</code> points at the real connectors instead &mdash; same shapes, same schema, no downstream change. See the &ldquo;Synthetic OEM feed + fixtures&rdquo; button at the top for the full cutover plan.</p>
    `
  },
  tests: {
    title: 'tests',
    badge: 'pytest &middot; 86 cases',
    body: String.raw`
      <p><strong>Purpose:</strong> Prove the pipeline from OEM-shaped fixtures through normalisation, alerting, risk scoring, and tenancy-aware RBAC so regressions surface immediately &mdash; and so CI actually runs a real test command.</p>
      <h3>Files</h3>
      <div class="file-list"><span class="file-tag">conftest.py</span><span class="file-tag">test_normaliser.py</span><span class="file-tag">test_alert_engine.py</span><span class="file-tag">test_risk_engine.py</span><span class="file-tag">test_tenancy.py</span><span class="file-tag">fixtures/</span></div>
      <ul>
        <li><code>C:\sita-platform\backend\tests\test_normaliser.py</code> &mdash; config-driven flattening, severity mapping (incl. apisec exposure thresholds), timestamp/type casting, 1h window dedup, in-batch dedup.</li>
        <li><code>C:\sita-platform\backend\tests\test_alert_engine.py</code> &mdash; rule loading, critical/high firing, per-rule throttling, complete alert fields, enricher owner/priority/links.</li>
        <li><code>C:\sita-platform\backend\tests\test_risk_engine.py</code> &mdash; bucket thresholds, signal scaling, fused-risk bounds, determinism, custom weights.</li>
        <li><code>C:\sita-platform\backend\tests\test_tenancy.py</code> &mdash; <code>tenant_filter</code> scoping, admin-set department/branch scope validation, admin-tier delegation (<code>can_manage</code>/<code>grantable_roles</code>), tenancy-consistent branch scope, and ministry/cluster derivation.</li>
        <li><code>C:\sita-platform\backend\tests\fixtures\</code> &mdash; JSON fixtures for all five sources loaded via <code>load_fixture()</code>.</li>
      </ul>
      <h3>CI</h3>
      <p><code>.github\workflows\ci.yml</code> runs <code>python -m pytest backend/tests</code> (was a no-op before); <code>pytest</code>/<code>pytest-asyncio</code>/<code>httpx</code> are pinned in <code>backend\requirements.txt</code>.</p>
    `
  },
  staging: {
    title: 'staging.raw_records',
    badge: 'raw, replayable buffer',
    body: String.raw`
      <p><strong>What it is:</strong> A PostgreSQL table in the <code>staging</code> schema that holds each OEM payload, verbatim, as <code>JSONB</code> &mdash; the durable copy before anything is transformed.</p>
      <h3>Why it exists</h3>
      <ul>
        <li><strong>Nothing is lost</strong> &mdash; even malformed records are preserved (or moved to <code>staging.rejected_records</code>, the DLQ) rather than silently dropped.</li>
        <li><strong>Replayability</strong> &mdash; the normaliser can reprocess raw data if the field map or rules change.</li>
        <li><strong>Audit</strong> &mdash; you can always trace a canonical warehouse row back to its original OEM payload.</li>
      </ul>
      <h3>Lifecycle</h3>
      <ul>
        <li>Written by <code>backend\app\lake\writer.py</code> under <code>entrypoints\ingestion.py</code>.</li>
        <li>Consumed by the Normaliser (<code>backend\app\processing\normaliser.py</code>).</li>
        <li><strong>TTL:</strong> purged after 7 days via <code>pg_cron</code> (nightly 2 AM); the DLQ is retained 30 days.</li>
        <li>Reports <em>never</em> read this table directly &mdash; only the SRE DLQ view touches staging.</li>
      </ul>
      <h3>Schema</h3>
      <div class="file-list"><span class="file-tag">staging.batch_runs</span><span class="file-tag">staging.raw_records</span><span class="file-tag">staging.rejected_records</span></div>
    `
  },
  normaliser: {
    title: 'Normaliser',
    badge: 'canonical field mapping',
    body: String.raw`
      <p><strong>Purpose:</strong> Convert raw OEM records <em>and their vendor-specific field names</em> into the platform&rsquo;s canonical schema, writing clean, report-ready rows into <code>warehouse.findings</code>.</p>
      <h3>How it works</h3>
      <p>Implemented in <code>C:\sita-platform\backend\app\processing\normaliser.py</code>, driven by <code>field_mapper.yaml</code> &mdash; a declarative map of <code>source-field &rarr; canonical-field</code> per OEM.</p>
      <ol>
        <li>Read raw records from <code>staging.raw_records</code> (JSONB).</li>
        <li>Map each OEM&rsquo;s fields onto canonical columns (<code>app_name</code>, <code>severity</code>, <code>title</code>, <code>category</code>, <code>status</code>, &hellip;).</li>
        <li>Deduplicate &amp; enrich (collapsing on <code>dedup_key</code>) &mdash; co-located in <code>alert_dedup.py</code> and <code>alert_enricher.py</code>.</li>
        <li>Upsert into <code>warehouse.findings</code>.</li>
      </ol>
      <h3>Canonical <code>findings</code> columns</h3>
      <div class="file-list"><span class="file-tag">id</span><span class="file-tag">source</span><span class="file-tag">external_id</span><span class="file-tag">app_name</span><span class="file-tag">severity</span><span class="file-tag">title</span><span class="file-tag">category</span><span class="file-tag">raw_data</span><span class="file-tag">first_seen</span><span class="file-tag">last_seen</span><span class="file-tag">status</span></div>
    `
  },
  findings: {
    title: 'warehouse.findings',
    badge: 'canonical findings table',
    body: String.raw`
      <p><strong>What it is:</strong> The primary <code>warehouse</code> table holding normalised, deduplicated vulnerability findings from every OEM &mdash; the single source of truth for the AppSec, DB Sec, and Exec dashboards.</p>
      <h3>Lifecycle</h3>
      <ul>
        <li><strong>Writes:</strong> output of the Normaliser (<code>backend\app\processing\normaliser.py</code>) &mdash; read from staging and persisted here.</li>
        <li><strong>Reads:</strong> <code>GET /api/v1/findings</code> (<code>backend\app\api\routers\findings.py</code>) &rarr; <code>AppSecDashboard</code> and <code>SocDashboard</code>.</li>
      </ul>
      <h3>Key columns</h3>
      <div class="file-list"><span class="file-tag">id</span><span class="file-tag">source</span><span class="file-tag">app_name</span><span class="file-tag">severity</span><span class="file-tag">category</span><span class="file-tag">status</span><span class="file-tag">raw_data</span></div>
      <p><em>Reports queried from this table: findings by app/severity/OWASP category, critical CVE lists (AppSec), violation categories (DbSec), and open-finding counts (Exec).</em></p>
    `
  },
  engines: {
    title: 'Alert / Risk / Compliance Engines',
    badge: 'rule-based processors',
    body: String.raw`
      <p><strong>Purpose:</strong> Pattern-match against normalised data to generate <strong>alerts</strong>, compute <strong>risk scores</strong>, and evaluate <strong>compliance</strong> posture &mdash; each writing its results back into the <code>warehouse</code>.</p>
      <h3>Alert engine</h3>
      <p><code>alert_engine.py</code> evaluates rules from <code>alert_rules.yaml</code> (e.g. <code>risk_critical</code>, <code>new_critical_cve</code>, <code>shadow_api_detected</code>, <code>violation_spike</code>, <code>connector_auth_failure</code>) &rarr; deduplicated by <code>alert_dedup.py</code>, enriched by <code>alert_enricher.py</code> &rarr; <code>warehouse.alerts</code>.</p>
      <h3>Risk engine</h3>
      <p><code>risk_engine.py</code> + <code>risk_aggregator.py</code> compute the fused risk score &mdash; appscan 35% / imperva 25% / exposure 20% / compliance 20% &rarr; <code>warehouse.risk_scores</code>. Most complete aggregation in the system.</p>
      <h3>Compliance engine</h3>
      <p><code>backend\app\processing\compliance.py</code> scores POPIA &amp; ISO 27001 domains and writes <code>compliance_snapshots</code> + <code>compliance_gaps</code>.</p>
      <h3>Files</h3>
      <div class="file-list"><span class="file-tag">alert_engine.py</span><span class="file-tag">alert_rules.yaml</span><span class="file-tag">alert_dedup.py</span><span class="file-tag">alert_enricher.py</span><span class="file-tag">risk_engine.py</span><span class="file-tag">risk_aggregator.py</span><span class="file-tag">compliance.py</span></div>
      <p><em>Reads from findings, writes back to <code>warehouse.*</code> &mdash; bridging the finding/risk/compliance/alert tables shown next.</em></p>
    `
  },
  warehouse: {
    title: 'warehouse.*',
    badge: 'reporting schema',
    body: String.raw`
      <p><strong>What it is:</strong> The <code>warehouse</code> PostgreSQL schema &mdash; the <em>only</em> source the reporting layer is allowed to read. All normalised, report-ready data lives here.</p>
      <h3>Tables</h3>
      <div class="file-list"><span class="file-tag">findings</span><span class="file-tag">alerts</span><span class="file-tag">risk_scores</span><span class="file-tag">compliance_snapshots</span><span class="file-tag">compliance_gaps</span><span class="file-tag">connector_health</span><span class="file-tag">api_endpoints</span><span class="file-tag">departments</span><span class="file-tag">branches</span></div>
      <ul>
        <li><strong>findings</strong> &mdash; normalised vulnerabilities (from Normaliser)</li>
        <li><strong>alerts</strong> &mdash; engine-generated, deduped alerts (SOC/SRE + dispatch)</li>
        <li><strong>risk_scores</strong> &mdash; fused per-app risk trends (Exec)</li>
        <li><strong>compliance_snapshots / compliance_gaps</strong> &mdash; POPIA + ISO 27001 posture (Compliance)</li>
        <li><strong>connector_health</strong> &mdash; OEM connector status (SRE)</li>
        <li><strong>api_endpoints</strong> &mdash; shadow-API discovery (SRE/AppSec)</li>
        <li><strong>departments / branches</strong> &mdash; the tenancy tree (<code>Department &rarr; Branch &rarr; App</code>) that scopes every app/db row</li>
      </ul>
      <h3>Contract</h3>
      <p>The REST API (<code>backend\app\api\routers\</code>) queries these tables and serves them to the frontend &mdash; the database is the boundary between the pipeline and reporting. Seeded by <code>infrastructure\scripts\seed-demo.sql</code>.</p>
    `
  },
  process: {
    title: 'Stage 2 — Pipeline Processing',
    badge: 'normalise &amp; enrich',
    body: String.raw`
      <p><strong>Purpose:</strong> Transform raw OEM records into canonical, deduplicated, enriched data and run the rule engines that produce alerts, risk scores, and compliance results.</p>
      <h3>How it works</h3>
      <ol>
        <li><strong>Normaliser</strong> (<code>C:\sita-platform\backend\app\processing\normaliser.py</code>) — maps each OEM's fields onto the canonical schema using <code>field_mapper.yaml</code>; writes to <code>warehouse.findings</code>.</li>
        <li><strong>Alert dedup / enrich</strong> (<code>alert_dedup.py</code>, <code>alert_enricher.py</code>) — collapse duplicates via <code>dedup_key</code>/<code>dedup_count</code>, attach context.</li>
        <li><strong>Alert engine</strong> (<code>alert_engine.py</code>) — evaluates rules from <code>alert_rules.yaml</code> (e.g. <code>risk_critical</code>, <code>new_critical_cve</code>, <code>shadow_api_detected</code>) and writes to <code>warehouse.alerts</code>.</li>
        <li><strong>Risk engine</strong> (<code>risk_engine.py</code> + <code>risk_aggregator.py</code>) — computes the fused risk score (appscan 35% / imperva 25% / exposure 20% / compliance 20%) and persists to <code>warehouse.risk_scores</code>.</li>
        <li><strong>Compliance engine</strong> (<code>processing/compliance.py</code>) — scores POPIA / ISO 27001 domains and writes snapshots + gaps.</li>
        <li><strong>Dispatch</strong> (<code>C:\sita-platform\backend\app\dispatch\</code>) — <code>worker.py</code> sends critical/high alerts via Email, PagerDuty, and Teams.</li>
      </ol>
      <h3>Tables written</h3>
      <div class="file-list"><span class="file-tag">warehouse.findings</span><span class="file-tag">warehouse.alerts</span><span class="file-tag">warehouse.risk_scores</span><span class="file-tag">warehouse.compliance_snapshots</span><span class="file-tag">warehouse.compliance_gaps</span></div>
      <p><em>Run as its own container/service: <code>C:\sita-platform\backend\app\entrypoints\processing.py</code> (+ <code>dispatch.py</code> for notifications).</em></p>
    `
  },
  store: {
    title: 'Stage 3 — PostgreSQL Warehouse',
    badge: 'single source of truth',
    body: String.raw`
      <p><strong>Purpose:</strong> Store normalised, report-ready data in PostgreSQL. The warehouse schema is the <em>only</em> source the reporting layer reads from.</p>

      <div class="schema-erd" id="erdStore"></div>
      <p class="erd-caption"><strong>PK</strong> primary key &middot; <strong>UQ</strong> unique &middot; <strong>FK</strong> foreign key (solid <strong>accent</strong> arrows) &middot; dashed <strong>amber</strong> arrows = maintenance rotation into <code>archive</code> (LIKE copies, <code>ON CONFLICT DO NOTHING</code>) &middot; bright column name = <strong>NOT NULL</strong>, dim = nullable &middot; <code>DF</code> = server default &middot; hover any box for its purpose. Rendered from the same DDL as <code>infrastructure\scripts\init-db.sql</code> &mdash; 6 schemas (incl. <code>audit.action_audit</code> for AG exports), 24 tables (20 canonical + 4 archive LIKE copies). <strong>Tenancy:</strong> every app/db-scoped warehouse row (<code>findings</code>, <code>risk_scores</code>, <code>alerts</code>, <code>dispatch_log</code>, <code>api_endpoints</code>, <code>waf_blocks</code>, <code>database_inventory</code>) denormalises <code>department_id</code>/<code>branch_id</code> (accent arrows &rarr; <code>warehouse.departments</code> / <code>warehouse.branches</code>), so <code>tenant_filter</code> scoping needs no joins; <code>identity.users</code> carries the admin-set <code>province_ids</code>/<code>department_ids</code>/<code>branch_ids</code> scope lists, and provincial departments resolve via <code>departments.province_id</code> &rarr; <code>warehouse.provinces</code>. <strong>Click the diagram to open it full-screen and zoom.</strong></p>

      <h3>The database is built by the pipeline, not just loaded</h3>
      <p>PostgreSQL is the <strong>terminal materialisation of a streaming log pipeline</strong>. Every row in the warehouse is a normalised, deduplicated, alerted, and risk-scored descendant of an OEM security log, written idempotently into <code>staging</code> (provenance) then <code>warehouse</code> (canonical model), with <code>archive</code> + <code>maintenance.sql</code> managing its lifecycle.</p>

      <p><code>OEM sources</code> <span class="flow-arrow">&rarr;</span> <code>scheduler/connectors</code> <span class="flow-arrow">&rarr;</span> <code>Redis stream (raw)</code> <span class="flow-arrow">&rarr;</span> <code>normaliser + alert engine</code> <span class="flow-arrow">&rarr;</span> <code>lake writer (1 txn)</code> <span class="flow-arrow">&rarr;</span> <code>staging.*</code> <span class="flow-arrow">&rarr;</span> <code>warehouse.*</code> <span class="flow-arrow">&rarr;</span> <code>analytics scheduler &rarr; risk_scores</code> <span class="flow-arrow">&rarr;</span> <code>FastAPI / React reports</code></p>

      <h3>Stage 1 &mdash; Ingestion: OEM logs &rarr; Redis (no DB yet)</h3>
      <p>Five connectors (<code>appscan</code>, <code>imperva_dam</code>, <code>imperva_waf</code>, <code>apisec</code>, <code>compliance</code>) poll on APScheduler intervals. Each poll is guarded by a <strong>TokenBucket</strong> rate limiter, a <strong>CircuitBreaker</strong> (CLOSED &rarr; OPEN &rarr; HALF_OPEN &rarr; PERM_OPEN) and a 3-attempt <strong>RetryHandler</strong> before anything reaches PostgreSQL. Records are published to the Redis stream <code>STREAM_RAW = sita:ingestion:raw</code>; the only DB write here is the <code>warehouse.connector_health</code> heartbeat.</p>

      <h3>Stage 2 &mdash; Streaming consumption &amp; normalisation</h3>
      <p><code>C:\sita-platform\backend\app\entrypoints\processing.py</code> consumes the stream as a Redis consumer group and runs each batch through <code>C:\sita-platform\backend\app\processing\normaliser.py</code>, offloaded to threads per source:</p>
      <ul>
        <li><code>_flatten_fields</code> &mdash; <code>field_mapper.yaml</code> maps OEM JSON paths (<code>$.a.b[0].c</code>) to canonical columns.</li>
        <li><code>_normalise_severity</code> &mdash; OEM enums &rarr; <code>{info, low, medium, high, critical}</code>; API Security derives severity from <code>exposure_score</code> thresholds.</li>
        <li><code>_normalise_timestamps</code> &mdash; ISO 8601 / Unix ms / OEM formats coerced to <strong>UTC</strong>; <code>first_seen</code> / <code>last_seen</code> derived.</li>
        <li><code>_cast_types</code> &mdash; per-source type hints (float / int / bool).</li>
        <li><code>_dedup</code> &mdash; in-batch dedup plus a <strong>1-hour window DB lookup</strong>: same status &rarr; suppress insert (touch <code>last_seen</code> only), changed &rarr; upsert.</li>
      </ul>
      <p>Per-row alert rules (<code>alert_rules.yaml</code>) fire, throttled by the Redis <code>AlertDeduplicator</code> and enriched from <code>app_catalog.yaml</code>.</p>

      <h3>Stage 3 &mdash; The lake writer develops the database</h3>
      <p><code>C:\sita-platform\backend\app\lake\writer.py</code> is where streaming meets the relational database, in <strong>one transaction</strong> (<code>upsert_lake_batch</code>):</p>
      <ul>
        <li><code>record_to_finding()</code> maps a canonical row &rarr; <code>warehouse.findings</code>, generating a UUID <code>id</code> and stashing the <strong>entire original payload</strong> in <code>raw_data JSONB</code>.</li>
        <li><code>INSERT ... ON CONFLICT DO UPDATE</code> keyed on <strong>UNIQUE (source, external_id)</strong>: a re-polled finding is <em>not duplicated</em> &mdash; it is refreshed and <code>version = version + 1</code>.</li>
        <li>Alerts upsert into <code>warehouse.alerts</code> on alert <code>id</code> (idempotent).</li>
        <li>Risk scores upsert on <strong>UNIQUE (app_name, score_date)</strong> &mdash; per-app daily snapshot.</li>
      </ul>

      <h3>Schema</h3>
      <ul>
        <li><code>staging</code> &mdash; raw ingestion (<code>batch_runs</code> run traceability, <code>raw_records</code> verbatim JSONB, <code>rejected_records</code> DLQ). TTL: 7 / 30 days via <code>pg_cron</code>.</li>
        <li><code>warehouse</code> &mdash; canonical reporting tables: <code>connector_health</code>, <code>findings</code>, <code>alerts</code>, <code>risk_scores</code>, <code>compliance_snapshots</code>, <code>compliance_gaps</code>, <code>api_endpoints</code>.</li>
        <li><code>archive</code> &mdash; historical retention (created <code>LIKE warehouse.* INCLUDING ALL</code> so rotation keeps the UNIQUE/PK keys for <code>ON CONFLICT DO NOTHING</code>); <code>audit</code> &mdash; governance trail.</li>
      </ul>
      <p>Lifecycle is automated by <code>C:\sita-platform\infrastructure\scripts\maintenance.sql</code> (pg_cron): staging TTL purge, archive rotation of risk_scores / alerts / compliance, weekly <code>REINDEX ... CONCURRENTLY</code>, and a 15-minute connector-staleness sweep.</p>

      <h3>Risk scores are a pipeline product too</h3>
      <p>The analytics scheduler (<code>entrypoints\analytics.py</code>) reads <code>warehouse.findings</code> per app and fuses four signals &mdash; <code>Sa</code> appscan severity-weighted, <code>Si = log2(count+1)&times;10</code> imperva, <code>E</code> mean exposure, <code>C = 100 &minus; compliance%</code> &mdash; into <code>R = (0.35&middot;Sa + 0.25&middot;Si + 0.20&middot;E + 0.20&middot;C) / &Sigma;w</code>, clipped to [0,100], bucketed safe(&le;30) / monitored(&le;70) / critical(&gt;70).</p>

      <h3>Why the database is developed, not just loaded</h3>
      <ul>
        <li><strong>Idempotent</strong> &mdash; unique constraints + <code>ON CONFLICT DO UPDATE</code> evolve rows; <code>version++</code> and <code>last_seen</code> semantics encode "newest observation wins".</li>
        <li><strong>Provenance</strong> &mdash; <code>staging.batch_runs</code> + <code>raw_records</code> + <code>raw_data JSONB</code> keep every original OEM payload beside its canonical form.</li>
        <li><strong>Transient vs durable</strong> &mdash; Redis streams (transient) &rarr; staging (short TTL audit) &rarr; warehouse (canonical) &rarr; archive (long retention).</li>
        <li><strong>Schema driven by pipeline output</strong> &mdash; <code>field_mapper.yaml</code> dictates canonical columns, <code>alert_rules.yaml</code> what becomes an alert, <code>risk_engine.py</code> what becomes a score. Change a YAML rule and the DB content changes without migration churn.</li>
      </ul>

      <h3>Seed / demo data</h3>
      <p><code>C:\sita-platform\infrastructure\scripts\init-db.sql</code> creates the schema; <code>seed-demo.sql</code> fills it with realistic demo rows (idempotent <code>ON CONFLICT</code> upserts):</p>
      <div class="file-list"><span class="file-tag">150 risk_scores</span><span class="file-tag">36 findings</span><span class="file-tag">36 alerts</span><span class="file-tag">2 compliance snapshots</span><span class="file-tag">12 gaps</span><span class="file-tag">5 connector_health</span><span class="file-tag">6 api_endpoints</span><span class="file-tag">4 DLQ records</span></div>
      <p><em>Load with:</em> <code>docker exec -i infrastructure-postgres-1 psql -U sita -d sita &lt; infrastructure\scripts\seed-demo.sql</code></p>

    `
  },
  api: {
    title: 'Stage 4 — REST API',
    badge: 'read-only reporting + actions',
    body: String.raw`
      <p><strong>Purpose:</strong> Serve warehouse data to the frontend. Every endpoint queries PostgreSQL via SQLAlchemy — there is no hardcoded report data.</p>
      <h3>Routers (<code>C:\sita-platform\backend\app\api\routers\</code>)</h3>
      <ul>
        <li><code>risks.py</code> &mdash; <code>GET /api/v1/risks</code>, <code>GET /api/v1/risks/{app}/trend</code> &rarr; <code>warehouse.risk_scores</code></li>
        <li><code>findings.py</code> &mdash; <code>GET /api/v1/findings</code>, <code>GET /api/v1/findings/{id}</code> &rarr; <code>warehouse.findings</code></li>
        <li><code>alerts.py</code> &mdash; <code>GET /api/v1/alerts</code>, <code>PATCH .../acknowledge</code>, <code>PATCH .../resolve</code> &rarr; <code>warehouse.alerts</code></li>
        <li><code>compliance.py</code> &mdash; <code>GET /api/v1/compliance</code>, <code>.../gaps</code>, <code>.../evidence</code> &rarr; <code>warehouse.compliance_snapshots</code>, <code>compliance_gaps</code></li>
        <li><code>dashboard.py</code> &mdash; <code>GET /api/v1/dashboard/summary</code> &rarr; aggregates from <code>risk_scores</code> + <code>alerts</code></li>
        <li><code>admin.py</code> &mdash; <code>GET /admin/connectors</code>, <code>GET /admin/dead-letter</code> &rarr; <code>warehouse.connector_health</code>, <code>staging.rejected_records</code></li>
      </ul>
      <h3>Auth &amp; RBAC</h3>
      <p><code>C:\sita-platform\backend\app\api\auth.py</code> validates the JWT (dev mode: <code>verify_signature=False</code>) and enforces a role hierarchy. Example grants: <code>exec</code> &rarr; risks/compliance/alerts; <code>soc</code> &rarr; findings/alerts; <code>dbsec</code> &rarr; risks/findings/alerts-read; <code>sre</code> &rarr; admin_read/admin_write. Department-scoped roles are further constrained by <code>tenant_filter(claims, model)</code>, which scopes every read to the JWT&rsquo;s <code>department_ids</code>/<code>branch_ids</code> &mdash; see the <strong>Multi-Tenancy</strong> panel.</p>
      <p><em>Served by FastAPI on :8000; nginx proxies <code>/api/</code> and <code>/admin/</code> to it.</em></p>
    `
  },
  tenancy: {
    title: 'Multi-Tenancy & Governance',
    badge: 'Tier 4 SITA Command &middot; Tier 3 National &middot; Tier 2 DHA / Prov &middot; Tier 1 Branch',
    body: String.raw`
      <p><strong>Platform Managing Authority &amp; Client:</strong> <strong>SITA (State Information Technology Agency)</strong> operates at <strong>Tier 4 (SITA National Security Command Center)</strong> with overarching transversal authority across the entire South African Government (all 173 national departments and 9 provincial administrations across the Next Generation Network).</p>
      <p><strong>Designated Demo &amp; PoC Test Bed:</strong> The <strong>Department of Home Affairs (DHA)</strong> (<code>home-affairs-digital</code>) serves as the primary live demonstration tenant with <strong>8 real DDG operational branches</strong> (<code>dha-civic</code>, <code>dha-digital</code>, <code>dha-immigration</code>, etc.). DHA telemetry is driven by live ingested <strong>HCL AppScan Cloud</strong> findings and <strong>Thales DAM</strong> database activity monitoring.</p>
      <h3>The 4-Tier Tenancy Hierarchy</h3>
      <p><code>Tier 4: SITA Command Center</code> <span class="flow-arrow">&rarr;</span> <code>Tier 3: National Estate</code> <span class="flow-arrow">&rarr;</span> <code>Tier 2: Departments &amp; Provinces</code> <span class="flow-arrow">&rarr;</span> <code>Tier 1: Operational Branches</code> &mdash; modelled in <code>C:\sita-platform\backend\app\tenant.py</code> as stable-slug catalogs (<code>PROVINCES</code> (9), <code>DEPARTMENTS</code> (173), <code>BRANCHES</code> (347), <code>APP_DEPARTMENTS</code>, <code>DB_TO_DEPARTMENT</code>, <code>MINISTRIES</code>/<code>CLUSTERS</code> for rollups).</p>
      <div class="file-list"><span class="file-tag">tenant.py</span><span class="file-tag">models/tenant.py</span><span class="file-tag">models/audit.py</span><span class="file-tag">api/auth.py</span><span class="file-tag">api/routers/auth.py</span><span class="file-tag">api/routers/admin.py</span><span class="file-tag">security.py</span><span class="file-tag">_migrate_province.py</span><span class="file-tag">tests/test_tenancy.py</span></div>
      <h3>Scoping &amp; Security Isolation</h3>
      <ul>
        <li><strong>Tier 4 &mdash; SITA Superadmins</strong> (<code>admin@</code>, <code>operator@</code>): Overarching transversal authority across all 173 departments and 9 provinces. Unrestricted superadmin provisioning down the entire cascade.</li>
        <li><strong>Tier 3 &mdash; National Estate</strong> (<code>transversal-admin</code>, <code>exec</code>, <code>compliance</code>, <code>sre</code>): Strategic, whole-of-government visibility, fused risk aggregation, and AG compliance export with SHA-256 integrity hash verification.</li>
        <li><strong>Tier 2 &mdash; Department &amp; Provincial Admins</strong> (<code>dept-admin</code>, <code>provincesoc</code>): Tactical operations scoped strictly to the assigned department (e.g. DHA) or province. Provincial peer blinding prevents cross-tenant leakage.</li>
        <li><strong>Tier 1 &mdash; Branch Superadmins &amp; Specialists</strong> (<code>branch-admin</code>, <code>soc</code>, <code>appsec</code>, <code>dbsec</code>): Operational triage strictly confined to the assigned DDG branch (e.g. <code>dha-digital</code>).</li>
        <li><strong>Write-Time Denormalisation</strong>: Every warehouse record carries <code>department_id</code> and <code>branch_id</code> at ingestion; <code>tenant_filter()</code> guarantees zero cross-tenant leakage.</li>
      </ul>
      <h3>Superadmin Provisioning Cascade</h3>
      <p>SITA Command Center administrators possess overarching authority to provision superusers and administrative roles down the entire cascade (<code>TIER_GRANTABLE_ROLES</code>, <code>GRANTABLE_ROLES</code> in <code>tenant.py</code>):</p>
      <ul>
        <li><strong>Tier 4 (SITA Command Center)</strong> &mdash; May provision superusers and roles at <strong>all tiers</strong> (transversal-admin, dept-admin, province-dept-admin, branch-admin, all operational roles).</li>
        <li><strong>Tier 3 (National Superadmin)</strong> &mdash; May provision Department Superadmins (<code>dept-admin</code>), Provincial Admins, and Branch Superadmins down the hierarchy. Cannot provision Tier 4 SITA admins.</li>
        <li><strong>Tier 2 (Department Superadmin)</strong> &mdash; May provision Branch Superadmins (<code>branch-admin</code>) and departmental operational specialists (<code>soc</code>, <code>appsec</code>, <code>dbsec</code>) strictly within DHA. Cannot elevate above Tier 2.</li>
        <li><strong>Tier 1 (Branch Superadmin)</strong> &mdash; May provision local operational analysts strictly within the assigned branch. Cannot cross branches or elevate.</li>
      </ul>
      <h3>Database Schema</h3>
      <p>Tenant reference tables live in the <code>warehouse</code> schema (<code>warehouse.departments</code>, <code>warehouse.branches</code>, <code>warehouse.provinces</code>, and <code>province_ids</code>/<code>department_ids</code>/<code>branch_ids</code> JSONB scope lists on <code>identity.users</code>); the <code>audit</code> schema contains <code>action_audit</code> for the AG export and administrative audit trail. Backed by immutable PostgreSQL logs.</p>
    `
  },
  ui: {
    title: 'Stage 5 — Reports UI',
    badge: 'role-gated React SPA',
    body: String.raw`
      <p><strong>Purpose:</strong> Render the processed data as six role-gated dashboards. The UI contains <em>no</em> hardcoded sample numbers &mdash; every figure comes from the API (which reads PostgreSQL).</p>
      <h3>Flow</h3>
      <p><code>LoginPage</code> <span class="flow-arrow">&rarr;</span> <code>AuthContext</code> mints role JWT via <code>src/utils/jwt.ts</code> <span class="flow-arrow">&rarr;</span> <code>RoleNav</code> gates routes <span class="flow-arrow">&rarr;</span> role dashboard <span class="flow-arrow">&rarr;</span> <code>useXData</code> hook <span class="flow-arrow">&rarr;</span> <code>src/api/*.ts</code> <span class="flow-arrow">&rarr;</span> <code>/api/v1/*</code> or <code>/admin/*</code></p>
      <h3>Dashboards (<code>C:\sita-platform\frontend\src\pages\</code>)</h3>
      <ul>
        <li><strong>Exec</strong> (<code>exec</code>) — fused risk trend, compliance gauges, heatmap, top-5 apps, alert summary</li>
        <li><strong>SOC</strong> (<code>soc</code>) — unified timeline, alert queue with acknowledge/resolve, findings</li>
        <li><strong>AppSec</strong> (<code>appsec</code>) — findings by app, OWASP categories, critical CVEs</li>
        <li><strong>DB Security</strong> (<code>dbsec</code>) — violations by DB, categories, active alerts</li>
        <li><strong>Compliance</strong> (<code>compliance</code>) — POPIA/ISO gauges, audit gaps, evidence</li>
        <li><strong>SRE</strong> (<code>sre</code>) — connector health, throughput, error rate, DLQ</li>
      </ul>
      <h3>"Explain this dashboard"</h3>
      <p>Each header has Explain / Layman's Guide buttons rendered by <code>src/components/dashboard/ExplainOverlay.tsx</code>. The narrative is built by <code>src/data/explanations.ts</code> (<code>buildExplain</code>/<code>buildLayman</code>) from the <em>live</em> facts of the page &mdash; no hardcoded figures.</p>
      <p><em>Served as a static SPA by nginx; dev proxy <code>/api</code> &rarr; :8000.</em></p>
    `
  },
  benchmark: {
    title: 'Anonymised Provincial Peer Benchmark',
    badge: 'provincial analytics &middot; tenant-safe',
    body: String.raw`
      <p><strong>Purpose:</strong> Let a provincial executive compare its province against peers on the <strong>fused risk score</strong> without breaching tenant isolation. Implemented in <code>C:\sita-platform\backend\app\api\routers\benchmark.py</code> as <code>GET /api/v1/benchmark/province</code>.</p>
      <div class="file-list"><span class="file-tag">benchmark.py</span><span class="file-tag">tests/test_benchmark.py</span><span class="file-tag">tests/test_new_endpoints.py</span></div>
      <h3>Identity vs analytics separation</h3>
      <ul>
        <li><strong>Own province unblinded</strong> &mdash; the caller&rsquo;s province is returned by name with a department-level drill-down (each provincial department&rsquo;s fused score, bucket, app count and primary driver).</li>
        <li><strong>Peers anonymised</strong> &mdash; every other province appears only as <code>Peer Province A/B/&hellip;</code> with its <em>aggregated fused score</em>; the payload deliberately contains no raw vulnerability counts, findings, signals or logs.</li>
        <li><strong>National view</strong> &mdash; nationwide roles (e.g. <code>exec</code>, <code>admin</code>) with no province scope see all nine provinces unblinded plus a national average.</li>
        <li><strong>Scoped end-to-end</strong> &mdash; the endpoint still runs <code>tenant_filter(claims, RiskScore)</code>, so a provincial caller&rsquo;s SQL cannot touch rows outside its province.</li>
      </ul>
      <h3>Scoring</h3>
      <p>Province score = mean of its department averages (each provincial department equal weight); leaderboard ranks by descending fused score. Only provincial-department rows participate &mdash; national departments are out of scope for the peer comparison.</p>
    `
  },
  exportsag: {
    title: 'Auditor-General Compliance Export Engine',
    badge: 'signed aggregation &middot; SHA-256 audit trail',
    body: String.raw`
      <p><strong>Purpose:</strong> Produce an Auditor-General-grade <strong>aggregation-only</strong> compliance attestation with tamper-evident integrity. Implemented in <code>C:\sita-platform\backend\app\api\routers\exports_ag.py</code> as <code>POST /api/v1/exports/ag-compliance</code>.</p>
      <div class="file-list"><span class="file-tag">exports_ag.py</span><span class="file-tag">models/audit.py</span><span class="file-tag">tests/test_exports_ag.py</span><span class="file-tag">tests/test_new_endpoints.py</span></div>
      <h3>What the attestation contains</h3>
      <ul>
        <li><strong>Snapshot summary</strong> &mdash; latest POPIA snapshot: overall score, passed/total controls, per-domain scores from <code>compliance_snapshots.details</code>.</li>
        <li><strong>Control aggregation</strong> &mdash; <code>compliance_gaps</code> rolled up into status / severity / domain counts &mdash; never the raw gap rows.</li>
        <li><strong>Scoped risk profile</strong> &mdash; bucket counts, scoped app/department totals and signal averages from <code>risk_scores</code>, scoped to the caller&rsquo;s province via <code>tenant_filter</code>.</li>
      </ul>
      <h3>Integrity &amp; accountability</h3>
      <ul>
        <li><strong>Aggregation-only</strong> &mdash; raw findings, vulnerability counts, logs and PII are stripped; the payload carries a provenance statement to that effect.</li>
        <li><strong>SHA-256 integrity hash</strong> &mdash; computed over the canonical JSON of the attestation and returned as <code>integrity_hash</code> alongside a <code>verify_url</code> (<code>GET /api/v1/exports/ag-compliance/verify/{hash}</code>).</li>
        <li><strong>Immutable action audit</strong> &mdash; every export writes one <code>audit.action_audit</code> row (actor, action, tenant scope, payload hash) via <code>C:\sita-platform\backend\app\models\audit.py</code>, giving non-repudiation. Table created in <code>C:\sita-platform\infrastructure\scripts\init-db.sql</code> and <code>C:\sita-platform\backend\_migrate_province.py</code>.</li>
      </ul>
    `
  },
  reports: {
    title: 'Stage 6 &mdash; Reports',
    badge: 'the reporting interface &mdash; final product',
    body: String.raw`
      <p><strong>Purpose:</strong> The reporting interface is the end-user product that surfaces all processed data. It is <em>not</em> a separate system &mdash; it is the combination of the role-gated React dashboards (frontend), the report-serving REST endpoints (backend), the out-of-band alert dispatch, and the Grafana operational dashboard. <strong>Every number shown is queried from PostgreSQL</strong> &mdash; reports never read the live pipeline or staging tables.</p>
      <h3>What makes up "Reports"</h3>
      <ul>
        <li><strong>Report pages</strong> &mdash; <code>C:\sita-platform\frontend\src\pages\</code>: <code>ExecDashboard</code>, <code>SocDashboard</code>, <code>AppSecDashboard</code>, <code>DbSecDashboard</code>, <code>ComplianceDashboard</code>, <code>SreDashboard</code>.</li>
        <li><strong>Data hooks</strong> &mdash; <code>C:\sita-platform\frontend\src\hooks\</code>: <code>useExecData</code>, <code>useSocData</code>, <code>useAppSecData</code>, <code>useDbSecData</code>, <code>useComplianceData</code>, <code>useSreData</code> (built on <code>useApi</code>).</li>
        <li><strong>API clients</strong> &mdash; <code>C:\sita-platform\frontend\src\api\</code>: typed modules hitting <code>/api/v1/*</code> and <code>/admin/*</code>.</li>
        <li><strong>Narratives</strong> &mdash; <code>C:\sita-platform\frontend\src\data\explanations.ts</code> (<code>buildExplain</code>/<code>buildLayman</code>) + <code>C:\sita-platform\frontend\src\components\dashboard\ExplainOverlay.tsx</code> render live-fact "how this is built" overlays.</li>
        <li><strong>Report API</strong> &mdash; <code>C:\sita-platform\backend\app\api\routers\dashboard.py</code> (aggregations) plus risks/findings/alerts/compliance routers; all query the <code>warehouse</code> schema.</li>
        <li><strong>Out-of-band reporting</strong> &mdash; <code>C:\sita-platform\backend\app\dispatch\</code>: critical/high alerts pushed via Email, PagerDuty, Teams.</li>
        <li><strong>Operational reporting</strong> &mdash; <code>C:\sita-platform\infrastructure\monitoring\grafana-dashboards\sita-pipeline.json</code> + <code>prometheus.yml</code> for pipeline health.</li>
      </ul>
      <h3>Role &rarr; report matrix</h3>
      <p><code>exec</code> &rarr; Exec &middot; <code>soc</code> &rarr; SOC &middot; <code>appsec</code> &rarr; AppSec &middot; <code>dbsec</code> &rarr; DB Sec &middot; <code>compliance</code> &rarr; Compliance &middot; <code>sre</code> &rarr; SRE + Grafana.</p>
      <h3>Data contract</h3>
      <p>Reports read only the <code>warehouse</code> schema tables (<code>risk_scores</code>, <code>findings</code>, <code>alerts</code>, <code>compliance_snapshots</code>, <code>compliance_gaps</code>, <code>connector_health</code>) and, for SRE only, <code>staging.rejected_records</code> (DLQ). Seeded by <code>C:\sita-platform\infrastructure\scripts\seed-demo.sql</code> so every view renders realistic demo data.</p>
    `
  }
,
  aidocs: {
    title: 'docs',
    badge: 'plan of record &middot; + NEW',
    body: String.raw`
      <p>Added by the AI workstream. The baseline had no <code>docs\</code> tree entry in this view &mdash; the master plan now lives in the repository as the document of record for the whole programme.</p>
      <h3>Contents relevant to this architecture</h3>
      <div class="file-list"><span class="file-tag">AI_INTEGRATION_PLAN_MASTER.md</span><span class="file-tag">G1_AI_Integration_Plan.md</span><span class="file-tag">G2_AI_Report_Generation_Plan.md</span><span class="file-tag">G2_POC_2026-10-15\</span></div>
      <h3>Status</h3>
      <p><code>AI_INTEGRATION_PLAN_MASTER.md</code> is <strong>document <code>AI-MASTER-R1</code>, prepared 6 October 2026</strong>. It <strong>supersedes <code>G1_AI_Integration_Plan.md</code> and <code>G2_AI_Report_Generation_Plan.md</code> in full</strong>. Those two remain as their dated originals and contain material this plan corrects &mdash; seven corrections, each load-bearing.</p>
      <p>Builds on <code>05</code> G2-ARCH-R1, <code>06</code> G2-ADR-R1 and <code>07</code> G2-EXEC-PLAN-R1 in <code>docs\G2_POC_2026-10-15\</code>. Verification method: <strong>code read + live database + live HTTP</strong>, baseline commit <code>57e080d</code>.</p>
      <div class="callout violet">
        <span class="co-t">Plan hygiene, resolved 7 October 2026</span>
        The master flight plan&rsquo;s <em>Project Teams</em> sheet names <strong>Peter Rashaya</strong> as Technical Lead; <em>Project Plan</em> R11 reads &ldquo;Project Lead Takawira and Peter&rdquo;. <strong>Peter returns to the POC window and takes the verification tasks</strong> &mdash; without him, one person writes both sides of every control and the claim that the verifier is independent stops being true.
      </div>
    `
  },

  aimaster: {
    title: 'docs\\AI_INTEGRATION_PLAN_MASTER.md',
    badge: 'AI-MASTER-R1 &middot; 6 Oct 2026 &middot; + NEW',
    body: String.raw`
      <p>The plan of record for the entire AI workstream, and the source for every annotation in this file. Sixteen sections; the architecture-bearing ones map onto the views you can click through here.</p>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>&sect;</th><th>Title</th><th>Where it appears in this file</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>Executive summary &mdash; the three claims</td><td>AI integration modal; the 4-layer modal</td></tr>
          <tr><td><strong>2</strong></td><td><strong>Corrections to the prior plans</strong></td><td>Change ledger &rarr; corrections C1&ndash;C7</td></tr>
          <tr><td>3</td><td>Verified current state &mdash; environment, 16-table inventory, tenancy rule</td><td>Change ledger; 4-layer modal</td></tr>
          <tr><td><strong>4</strong></td><td><strong>Governing architecture</strong> &mdash; four layers, one agent, reuse map</td><td><strong>4-layer control model modal</strong>; the AI narrative path strip</td></tr>
          <tr><td>5</td><td>Governance gate &mdash; Phase 0</td><td>Change ledger &rarr; ~ CHANGED and &minus; REMOVED</td></tr>
          <tr><td>6</td><td>Capability roadmap</td><td>AI integration modal &rarr; phase map</td></tr>
          <tr><td>7</td><td>Phase detail and exit criteria</td><td>AI integration modal &rarr; phase map</td></tr>
          <tr><td>8&ndash;9</td><td>NFR register; verification suites S1&ndash;S10</td><td>4-layer modal &rarr; verification table</td></tr>
          <tr><td>10&ndash;11</td><td>Report catalogue; endpoint contract</td><td>4-layer modal &rarr; matrices and contract</td></tr>
          <tr><td>12</td><td>Data model &mdash; <code>ai</code> schema, <code>finding_triage</code></td><td><strong>Stage 3 ERD</strong> &mdash; the <code>ai</code> schema</td></tr>
          <tr><td>13&ndash;16</td><td>Risks; non-goals; open decisions; traceability</td><td>4-layer modal; Change ledger</td></tr>
        </tbody>
      </table></div>
    `
  },

  aisuperseded: {
    title: 'G1_AI_Integration_Plan.md &middot; G2_AI_Report_Generation_Plan.md',
    badge: '= reference &middot; superseded',
    body: String.raw`
      <p>Both drafted <strong>5 October 2026</strong>. Both are good documents that have since been tested against the live system, and <strong>several of their claims did not survive</strong>. They remain in the repository as their dated originals.</p>
      <h3>Why they matter to this architecture</h3>
      <p>Five of the seven corrections changed a real design decision rather than a sentence &mdash; and this file&rsquo;s architecture is drawn from the corrected position, not the original:</p>
      <ul>
        <li><strong>C1</strong> replaced a GPU/vLLM design with Ollama on CPU &mdash; zero CAPEX, and it closed R-AI-7 outright</li>
        <li><strong>C2</strong> inverted the <code>tenant_filter()</code> failure mode on unscopable tables, which promoted typed disclosure from mitigation to <em>only control</em></li>
        <li><strong>C3</strong> changed 11 roles to 14, which changes what S1 must enumerate</li>
        <li><strong>C4</strong> replaced a fabricated example figure (estate risk 62) with the live value (max 25.2)</li>
        <li><strong>C5</strong> replaced &ldquo;nothing existing modified&rdquo; with a precise, defensible one-line claim</li>
      </ul>
      <p>Full table in the <strong>Change ledger</strong> modal, and the secret-purge closure is on the AI-integration modal.</p>
    `
  },

  ai: {
    title: 'backend\\app\\ai',
    badge: '+ NEW &middot; the whole AI capability',
    body: String.raw`
      <p>One new package holds the entire AI capability. It is <strong>additive</strong> &mdash; no existing module imports it, so nothing existing changes behaviour &mdash; and it is organised <strong>by layer</strong>, because the layer boundary is the security boundary.</p>
      <h3>Module map, by layer</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Layer</th><th>Modules</th><th>Contains a model?</th></tr></thead>
        <tbody>
          <tr><td>1 &middot; Scope resolution</td><td><code>scope.py</code> (+ <code>permissions</code> in <code>app\api\</code>)</td><td class="no">NO</td></tr>
          <tr><td>2 &middot; Fact assembly</td><td><code>accessors.py</code>, <code>capability.py</code>, <code>disclosure.py</code></td><td class="no">NO</td></tr>
          <tr><td>3 &middot; Narrative</td><td><code>prompts\</code>, <code>generate.py</code>, <code>gateway.py</code>, <code>redaction.py</code></td><td class="cell-hot">YES &mdash; only here</td></tr>
          <tr><td>4 &middot; Verification</td><td><code>verify.py</code></td><td class="no">NO</td></tr>
          <tr><td>Cross-cutting</td><td><code>config.py</code>, <code>cache.py</code>, <code>settings.py</code></td><td>&mdash;</td></tr>
          <tr><td>Phase C</td><td><code>copilot\router.py</code>, <code>intent.py</code>, <code>compiler.py</code></td><td>LLM #1 constrained</td></tr>
          <tr><td>Phase D</td><td><code>triage\batch.py</code>, <code>service.py</code></td><td>out-of-band batch</td></tr>
        </tbody>
      </table></div>
      <h3>Why the package is additive</h3>
      <p>The only existing file the AI workstream must touch is <code>app\main.py</code>, and only to add one <code>include_router</code> line. Keeping the AI settings in <code>app\ai\settings.py</code> rather than <code>app\config.py</code> during the POC is what <strong>holds non-interference to that single line</strong>; Phase A promotes them when the constraint stops binding.</p>
      <div class="callout violet">
        <span class="co-t">The one property that makes this package safe to add</span>
        Because nothing existing imports <code>app\ai\</code>, the entire AI capability can be deleted by removing one router line &mdash; and conversely, no AI defect can propagate into the pipeline. The new <code>ai.report</code> schema is the only state it writes, and it writes nothing the baseline reads.
      </div>
    `
  },

  ail1: {
    title: 'Layer 1 &middot; ai\\scope.py',
    badge: 'scope resolution &middot; NO MODEL &middot; POC',
    body: String.raw`
      <p>Turns a validated JWT into a <strong>frozen, hashed</strong> <code>ReportScope</code>. Nothing downstream can widen it. <strong>Contains no inference call</strong>, so it is testable with the model stopped.</p>
      <h3>Sequence</h3>
      <ol class="steps">
        <li><strong>Gate 1 &mdash; default-deny.</strong> <code>permissions.require_report_permission()</code>. A role absent from <code>ROLE_REPORT_AI</code> gets nothing. Unknown role &rarr; 403, never a default grant.</li>
        <li><strong>Resolve.</strong> <code>scope.resolve_report_scope(claims)</code> &rarr; frozen <code>ReportScope</code> with <code>department_ids</code>, <code>branch_ids</code>, <code>scope_class</code>.</li>
        <li><strong>Hash.</strong> <code>scope_hash = sha256_hex(canonical_json(scope tuple))</code>, reusing <code>exports_ag.py:48,58</code>. The same hash then appears in the envelope, the cache key <em>and</em> the audit row &mdash; if they disagree, S5 catches it.</li>
        <li><strong>Delegate.</strong> <code>tenant_filter(claims, model)</code> does the scoping. Layer 1 <strong>never re-implements it</strong> &mdash; one scoping implementation, one set of bugs.</li>
      </ol>
      <h3>NFR-AI-14 &mdash; the trap that looks like correct behaviour</h3>
      <div class="callout danger">
        <span class="co-t">An unknown province slug is indistinguishable from correct scoping</span>
        <code>PROVINCES</code> uses <strong>two-letter slugs</strong> (<code>gp</code>, <code>kzn</code>, <code>wc</code>&hellip;). A probe using <code>province_ids=["gauteng"]</code> returned <strong>0 rows</strong> &mdash; correct for an unknown slug, but identical in appearance to correct scoping. NFR-AI-14 therefore requires a <strong>named error, never a silent empty scope</strong>.
      </div>
      <p>Verified live against the baseline data: <code>exec</code> &rarr; 2&nbsp;244 findings &middot; <code>soc</code> scoped to <code>home-affairs-digital</code> &rarr; <strong>745</strong> &middot; <code>dept-admin</code> with no scope &rarr; <strong>0</strong> via <code>expression.false()</code> &middot; province <code>gp</code> &rarr; 15 departments.</p>
      <h3>Ambient scope &mdash; and why Phase 0 P0-6 matters here</h3>
      <p>Scope is <strong>ambient</strong>: it comes from the JWT and is not re-derived per request. <code>verify_token</code> (<code>auth.py:52-73</code>) trusts that token, so a revoked admin stays admin for up to 12 h. Layer 1 therefore holds <strong>no ambient authority of its own</strong> &mdash; helpers take scope explicitly, and P0-6 closes the staleness window at the source.</p>
    `
  },

  ail2: {
    title: 'Layer 2 &middot; ai\\accessors.py',
    badge: 'fact assembly &middot; NO MODEL &middot; S6',
    body: String.raw`
      <p>Where a fact becomes a <strong>fact pack</strong>: a pure, hashable, typed object a prompt can be built from and a verifier can be run against. <strong>Nothing here talks to a model.</strong></p>
      <h3>The signature is the control</h3>
      <pre class="code"><span class="c">// accessors.py</span>
<span class="k">def</span> <span class="n">risk_summary</span>(scope: <span class="s">ReportScope</span>, db: AsyncSession) -&gt; RiskFact:
    stmt = select(...).where(<span class="n">tenant_filter</span>(scope.claims, RiskScore))
    <span class="c">#            ^ a straight-line statement in our code,</span>
    <span class="c">#            not an instruction in a prompt</span>

<span class="k">def</span> <span class="n">compliance_status</span>(scope: <span class="s">ReportScope</span>, db: AsyncSession) -&gt; ComplianceFact:
    <span class="c"># capability() == UNSCOPABLE -&gt; typed ESTATE_WIDE disclosure,</span>
    <span class="c"># NOT a filtered result and NOT an AttributeError</span>
    <span class="k">return</span> ComplianceFact(disclosure=<span class="n">ESTATE_WIDE</span>, rows=<span class="n">456</span>, ...)</pre>
      <div class="callout ok">
        <span class="co-t">S6 &mdash; the suite that prevents regression</span>
        Assert <code>scope: ReportScope</code> is the <strong>first positional parameter of every public function</strong> in the module. 100% compliance. Because it is a <em>signature</em> test, it is not a code review that can be forgotten &mdash; the property either holds or the build fails. Carried by Peter Rashaya against code Takawira wrote.
      </div>
      <h3>Aggregate in SQL, never port <code>mappers.ts</code></h3>
      <p>The frontend has its own mappers. Porting or reusing them into the fact-pack path would create <strong>two implementations of one number</strong> &mdash; and the narrative would eventually disagree with the dashboard sitting next to it. Aggregates are computed in SQL against the warehouse and are the only source for both.</p>
      <h3>Pure builders, following <code>build_attestation()</code></h3>
      <p>Fact packs are built by <strong>pure functions</strong> &mdash; no DB handle escapes, no ambient state, and <code>fact_pack_hash</code> is <code>sha256_hex(canonical_json(...))</code> on the output. Same pattern as <code>build_attestation()</code> at <code>exports_ag.py:62</code>, already pure and unit-tested without a database (<code>tests\test_exports_ag.py:71-109</code>).</p>
      <h3>Bucket discipline (P0-5)</h3>
      <p>Until the three bucket definitions are consolidated, <strong>read <code>risk_scores.bucket</code> from the column, never recompute it</strong>, and never mix a stored bucket with a recomputed one in a single fact pack. Live: all 15&nbsp;283 rows bucket <code>safe</code>, max <code>fused_score</code> 25.2, <code>critical</code> bucket empty.</p>
    `
  },

  ail2b: {
    title: 'Layer 2 &middot; ai\\capability.py',
    badge: 'capability gate &middot; NO MODEL &middot; S7',
    body: String.raw`
      <p>Classifies every mapped class into one of four kinds &mdash; <strong>by introspection, never a hardcoded list</strong>, so a new table cannot escape classification by simply not being listed.</p>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Class</th><th>Meaning</th><th>Example tables</th></tr></thead>
        <tbody>
          <tr><td><code>SCOPABLE</code></td><td>Has tenancy columns; <code>tenant_filter</code> applies</td><td><code>risk_scores</code> (15&nbsp;283), <code>findings</code> (2&nbsp;244), <code>alerts</code> (551), <code>waf_blocks</code>, <code>api_endpoints</code>, <code>database_inventory</code></td></tr>
          <tr><td><code>REFERENCE</code></td><td>No tenancy columns, but carries only scope <em>labels</em></td><td><code>departments</code> (173), <code>branches</code> (347), <code>provinces</code> (0)</td></tr>
          <tr><td><code>UNSCOPABLE</code></td><td>No tenancy columns <em>and</em> real data &mdash; must be disclosed as estate-wide</td><td><code>compliance_snapshots</code> (456), <code>compliance_gaps</code> (228)</td></tr>
          <tr><td><code>NEVER_READ</code></td><td>Not agent-readable at all &mdash; <strong>raises at import</strong></td><td><code>identity.users</code>, <code>audit.action_audit</code></td></tr>
        </tbody>
      </table></div>
      <p><strong>9 of 16 warehouse tables are unscopable.</strong></p>
      <h3>NFR-AI-11 &mdash; zero read paths, not merely unused</h3>
      <div class="callout danger">
        <span class="co-t">R23 &mdash; the severe one</span>
        <code>identity.users</code> and <code>audit.action_audit</code> must be <strong>unreachable</strong> from the agent, not simply unqueried. <code>NEVER_READ</code> raises at import, suite S7 enumerates <code>Base.registry</code> and asserts both raise, and <strong>no accessor path exists</strong>. Rated M / <strong>Severe</strong> because the failure mode if rushed is credential and audit exposure.
      </div>
      <p>Phase A generalises the POC-scope version of this module into a <strong>platform-wide route/table guard</strong> (1.5 PD).</p>
    `
  },

  ail2c: {
    title: 'Layer 2/L3 &middot; ai\\disclosure.py',
    badge: 'typed disclosure &middot; NFR-AI-12',
    body: String.raw`
      <p>Every fact carries one of <strong>three typed classes</strong>. No free-text disclosure &mdash; supersedes G1 &sect;4A.4&rsquo;s free-form <code>data_disclosure</code> field, which could not be asserted.</p>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Class</th><th>Meaning</th><th>Raised when</th><th>Verifier check</th></tr></thead>
        <tbody>
          <tr><td><code>TENANT_SCOPED</code></td><td>The fact passed <code>tenant_filter(claims, model)</code></td><td><code>capability() == SCOPABLE</code></td><td>&#9314; scope containment</td></tr>
          <tr><td><code>ESTATE_WIDE</code></td><td>No tenancy columns exist &mdash; must be labelled estate-wide in the prose</td><td><code>UNSCOPABLE</code> or <code>REFERENCE</code></td><td>&#9315; attribution</td></tr>
          <tr><td><code>DERIVED_FROM_ESTATE_WIDE</code></td><td>A tenant-scoped figure whose computation takes an unscopable column as an input</td><td>a scoped aggregate consumes an unscopable column</td><td>&#9315; attribution</td></tr>
        </tbody>
      </table></div>
      <h3>Why this is the only control on unscopable tables</h3>
      <div class="callout danger">
        <span class="co-t">Correction C2 &mdash; the failure mode is inverted, not absent</span>
        Both prior plans recorded that <code>tenant_filter()</code> &ldquo;raises <code>AttributeError</code> on compliance tables&rdquo; and treated it as a crash risk. Verified reality: it raises <strong>only for scoped callers</strong>, who are denied the report at Gate 1 anyway. Nationwide callers short-circuit to <code>None</code> <strong>before</strong> touching <code>model.department_id</code> (<code>auth.py:238-241</code>), so they receive the <strong>full table silently</strong>.
      </div>
      <p>For the intended audience that is a <strong>silent, total bypass of 684 rows</strong> &mdash; 456 <code>compliance_snapshots</code> plus 228 <code>compliance_gaps</code>. Typed disclosure is therefore the <em>only</em> control, not a mitigation, and the verifier&rsquo;s attribution check is what makes it binding.</p>
      <h3>Disclosure is not optional in the envelope</h3>
      <p>The limitation must travel with the payload so no consumer can present estate-wide figures as department-scoped. <code>disclosure</code> is asserted in the response envelope (NFR-AI-12) and in <code>ai.report</code>. Wording of the third class is <strong>OD-5</strong>, defaulting to envelope-only typed class with no prose.</p>
    `
  },

  ail3: {
    title: 'Layer 3 &middot; ai\\prompts\\ &rarr; ai\\gateway.py',
    badge: '&#9679; THE ONLY MODEL LAYER &middot; Ollama qwen2.5:3b',
    body: String.raw`
      <p>This is the only layer in the architecture that can fail open. Everything else is deterministic &mdash; which is exactly why <strong>scope is enforced before this layer and verified after it</strong>, not by this layer.</p>
      <h3>What crosses the boundary</h3>
      <div class="pre-code"><span class="cm">// what the model receives</span>
  template text
+ <span class="an">pack.serialise(allowed=claims)</span>     <span class="cm"># FACT-FILTERED; the data boundary, not a rule</span>
+ allowed_claim_list
+ scope_block.labelled(<span class="an">"for_attribution"</span>)      <span class="cm"># disclosure, NOT control</span>

  <span class="cm">// what the model never receives</span>
  <span class="k">NO</span> db handle   <span class="k">NO</span> sql   <span class="k">NO</span> tools   <span class="k">NO</span> unscoped row

<span class="cm">// redacted immediately before egress</span>
  fact_pack &#8594; redaction.py &#8594; gateway.py &#8594; http://localhost:11434  (Ollama 0.35.1, PID 27452)</div>
      <h3>The redaction gate is outside the gateway on purpose</h3>
      <p>It sits <strong>immediately before egress</strong>, not inside <code>gateway.py</code>, so that a gateway-provider swap (OD-11 being overturned) cannot bypass it. The same gate is applied on the sovereign DR route &mdash; R-AI-6, sovereign DR must not become an egress path under pressure.</p>
      <h3>Runtime</h3>
      <p><strong>Ollama 0.35.1</strong>, installed and running on <code>localhost:11434</code>. Model <code>qwen2.5:3b</code> (~2.0 GB), pulled <strong>day 1</strong>. Host: i5-11400H, 6-core, <strong>no GPU</strong>, 15.6 GB RAM, 84.3 GB free. <strong>Zero CAPEX, zero procurement lead time</strong> &mdash; which is correction <strong>C1</strong>, and it closes risk <strong>R-AI-7</strong> outright. GPU/vLLM is deferred to a <strong>Phase C scale decision</strong>.</p>
      <h3>Token cap is decided day 1, on measured latency</h3>
      <div class="callout warn">
        <span class="co-t">R21 &mdash; CPU-only inference latency under demo conditions</span>
        With no GPU, latency is the binding constraint. The mitigation is not &ldquo;optimise later&rdquo; &mdash; it is to fix the token cap <strong>on day 1 against measured latency</strong> rather than discovering it on rehearsal day, and to rehearse on day 7. NFR-AI-01 targets <strong>&le;8 s cached, &le;20 s cold</strong>.
      </div>
      <h3>Provenance is recorded, always</h3>
      <p><code>model_id</code>, <code>model_digest</code> and <code>prompt_version</code> go into the envelope and into <code>ai.report</code>. That is NFR-AI-08, and it is what makes the eval harness meaningful &mdash; otherwise a model change cannot be attributed.</p>
      <div class="callout violet">
        <span class="co-t">Rebuild the prompt examples from live fact packs (correction C4)</span>
        G2 &sect;6 offered &ldquo;estate risk is 62&rdquo; as example <code>exec</code> output. <strong>Live max <code>fused_score</code> is 25.2, average 7.46, all 15&nbsp;283 rows bucket <code>safe</code>, and the <code>critical</code> bucket is empty.</strong> A prompt seeded with 62 teaches the model to produce 62 &mdash; so prompt examples and the eval set must be regenerated from live fact packs before any quality claim is made.
      </div>
    `
  },

  claims: {
    title: 'Layer 1 &middot; ai\\claims.py',
    badge: '14-ROLE CLAIM MAP &middot; GATE 1 &middot; default-deny',
    body: String.raw`
      <p>Resolves <strong>which claim classes this caller may be told</strong> &mdash; and does it for <strong>all 14 roles</strong>, not just the six that appear in the report catalogue. This is what makes prompt-driven reporting safe, because with the catalogue it was the <em>template</em> that constrained output shape; remove the template and this map is the only thing stopping an <code>exec</code> from receiving CVE identifiers.</p>
      <h3>The derivation rule &mdash; no claim wider than the permission it rests on</h3>
      <div class="callout ok">
        <span class="co-t">A claim set can never exceed the role&rsquo;s existing read permission</span>
        <code>risks</code> &rarr; <code>risk_buckets</code>, <code>headline_metrics</code> &middot; <code>compliance</code> &rarr; <code>aggregate_compliance</code> &middot; <code>findings</code> &rarr; <code>cve_ids</code>, <code>app_names</code>, <code>owner_names</code>, <code>rule_ids</code> &middot; <code>alerts_read</code> &rarr; <code>alert_ids</code>.
      </div>
      <p>So the map is <strong>derived from <code>ROLES_HIERARCHY</code> (<code>auth.py:21-36</code>)</strong>, not asserted alongside it. A role cannot be handed a claim class it has no underlying read permission for, and a permission grant that is later removed narrows the claim set automatically.</p>
      <h3>The gap this closes</h3>
      <div class="callout warn">
        <span class="co-t">9 of 14 roles had no claim set at all</span>
        The catalogue matrix covers <strong>6</strong> roles and the claim matrix covered <strong>5</strong>. Uncovered: <code>sre</code>, <code>province-soc-lead</code>, <code>province-dept-admin</code>, <code>dept-admin</code>, <code>branch-admin</code>, <code>local-appsec</code>, <code>admin</code>, <code>operator</code>, <code>transversal-admin</code>. With a fixed catalogue that was harmless &mdash; they simply were not in <code>ROLE_REPORT_AI</code> and were denied. With free-text prompting it becomes load-bearing, because every role that can prompt needs a resolved set.
      </div>
      <h3>Wildcards do not imply claims</h3>
      <div class="callout danger">
        <span class="co-t"><code>admin</code> and <code>operator</code> both hold <code>{"*"}</code> in ROLES_HIERARCHY</span>
        That is a <strong>permission</strong> wildcard. It is <strong>not</strong> a claim wildcard, and this module resolves it explicitly rather than by inheritance. Granting <code>cve_ids</code> because a role holds <code>"*"</code> is precisely the &ldquo;for completeness&rdquo; failure mode the signed claim matrix exists to prevent.
      </div>
      <h3>Unknown roles</h3>
      <p>Resolve to the <strong>empty set</strong>, not to a default. An unknown role &rarr; 403, and S1 fails if the role count in <code>ROLES_HIERARCHY</code> changes without a corresponding entry here (correction C3).</p>
      <h3>Output</h3>
      <p>A frozen, sorted claim set that goes into the envelope as <code>claim_classes_applied</code> and into <code>ai.report.claim_set</code> &mdash; so the audit row records the exact disclosure set that was in force, not the role name that implied it.</p>
      <div class="callout violet">
        <span class="co-t">Where the row-level sign-off sits</span>
        The 9 newly-derived rows are marked <strong>PROVISIONAL</strong> until Compliance signs them. Default-deny applies in the meantime: a provisional role receives its derived set, and widening any row requires approval <em>before</em> implementation. This is a Compliance decision, not a development one, and it belongs on the critical path ahead of any demo involving those roles.
      </div>
    `
  },

  canonical: {
    title: 'Layer 2 &middot; ai\\canonical.py',
    badge: 'CANONICAL FACT FOLDER &middot; ONE SQL PASS &middot; no model',
    body: String.raw`
      <p>Builds <strong>one fact folder per scope</strong>, in a single SQL pass, through <code>tenant_filter()</code>. This replaces the per-report-type accessors as the thing the model actually reads from, and it is what makes prompt-driven reporting possible.</p>
      <h3>Why one folder rather than one pack per report type</h3>
      <div class="callout ok">
        <span class="co-t">You cannot pre-aggregate for arbitrary prompts</span>
        Eight fixed report types justify eight purpose-built accessors. A user-supplied prompt does not: the set of questions is unbounded, so the pack must be bounded and the prompt must select <em>within</em> it. One folder also serves every prompt for that scope, so the cost is one query pass rather than one per request.
      </div>
      <h3>Construction rules</h3>
      <ul>
        <li><strong>Scope-first.</strong> <code>canonical(scope, db)</code> &mdash; same signature discipline as every other accessor, so suite <strong>S6</strong> covers it unchanged.</li>
        <li><strong>One pass.</strong> All scoped aggregates for the caller&rsquo;s scope in a single query plan, so no accessor can be called with a different scope.</li>
        <li><strong>Stable fact IDs.</strong> Every fact gets a deterministic ID. This is what makes the selection step bounded &mdash; see <code>select.py</code>.</li>
        <li><strong>Typed disclosure on every fact.</strong> One of <code>TENANT_SCOPED</code> / <code>ESTATE_WIDE</code> / <code>DERIVED_FROM_ESTATE_WIDE</code>, decided by <code>capability()</code>, not by the prompt.</li>
        <li><strong>Bucket read, never recomputed</strong> (P0-5): read <code>risk_scores.bucket</code> from the column.</li>
        <li><strong>Pure</strong> &rarr; <code>fact_pack_hash</code> = <code>sha256_hex(canonical_json(...))</code>, following the <code>build_attestation()</code> pattern.</li>
      </ul>
      <h3>Verification without a model</h3>
      <p>Layers 1, 2 and 4 contain no inference call, so the folder is built and hashed on a machine with Ollama stopped. <strong>NFR-AI-13</strong> asserts the fallback and model paths read the identical folder <strong>by object identity</strong>.</p>
      <div class="callout danger">
        <span class="co-t">The folder is the whole security boundary</span>
        If a fact can get into the folder, it can reach the model. That is why the folder is built by <code>tenant_filter()</code> and <code>capability()</code> only, why the claim filter is applied at serialisation rather than in the prompt, and why <strong>NFR-AI-11</strong> (<code>identity.users</code> and <code>audit.action_audit</code> raise at import) applies to the folder builder itself.
      </div>
      <h3>Live shape</h3>
      <pre class="code">canonical_fact_folder(scope) -&gt; FactFolder
  facts:       [ { fact_id, value, unit, disclosure, source_table, row_count }, ... ]
  bucket_counts: { safe: 15283, critical: 0 }        <span class="c">// read from the column</span>
  compliance:    { status: n/a, disclosure: ESTATE_WIDE }
  scope:         { class, departments: 173, hash: sha256:9f2c... }
  folder_hash:   sha256_hex(canonical_json(facts))</pre>
    `
  },

  select: {
    title: 'Layer 3 &middot; ai\\select.py',
    badge: 'SELECTION &middot; FACT IDs ONLY &middot; bounded by the folder',
    body: String.raw`
      <p><strong>This is the step that makes prompt-driven reporting safe.</strong> The model sees the folder and decides <em>which</em> facts its prompt needs &mdash; but it returns <strong>fact IDs, not text</strong>, and the set of legal answers is bounded by folder membership.</p>
      <h3>The pipeline</h3>
      <pre class="code">user prompt (free text, or a seeded template the user edited)
     <span class="s">&#9660;</span>
[1] Gate 1   <span class="c">may this role generate?  resolve CLAIM SET server-side</span>
     <span class="s">&#9660;</span>
[2] folder   <span class="c">canonical_fact_folder(scope)  &mdash; ONE SQL pass through tenant_filter()</span>
     <span class="s">&#9660;</span>
[3] SELECT  <span class="c">which fact_ids does this prompt need?</span>
           <span class="c">returns IDs only &mdash; never rows, never text</span>
     <span class="s">&#9660;</span>
[4] prompt   <span class="c">= template + selected facts + claim set + scope block</span>
     <span class="s">&#9660;</span>
[5] LLM &#8594; prose
     <span class="s">&#9660;</span>
[6] four checks  <span class="c">any failure &#8594; deterministic template over the SAME folder</span>
     <span class="s">&#9660;</span>
[7] ai.report + audit row  <span class="c">prompt_text, fact_ids, claim_set, scope_hash</span></pre>
      <h3>What the model is and is not allowed to do</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>The model does this</th><th>What happens</th><th>Axis</th></tr></thead>
        <tbody>
          <tr><td>Selects a low-signal figure over a high-signal one</td><td>Bad brief. Nobody is paged. Passes every check</td><td class="cell-hot">quality</td></tr>
          <tr><td>Selects a fact outside the claim set</td><td>Rejected at selection &mdash; the ID is not offered</td><td>safety</td></tr>
          <tr><td>Returns an ID that is not in the folder</td><td>Rejected &mdash; set membership against <code>folder_hash</code></td><td>safety</td></tr>
          <tr><td>Names an entity outside <code>ReportScope</code> in prose</td><td>Check &#9314; &mdash; whole draft discarded</td><td>safety</td></tr>
          <tr><td>Emits a figure not in the folder</td><td>Check &#9312; &mdash; whole draft discarded</td><td>safety</td></tr>
          <tr><td>Presents an estate-wide fact as department-scoped</td><td>Check &#9315; &mdash; whole draft discarded</td><td>safety</td></tr>
        </tbody>
      </table></div>
      <p><strong>That separation is the design.</strong> Emphasis is a quality axis and is deliberately not policed &mdash; you do not throw away a draft for picking the wrong headline. Falsity is a safety axis and is policed twice: once at selection, once at verification.</p>
      <h3>It is read-only</h3>
      <p>Selection emits no SQL. It is roughly the copilot&rsquo;s <code>compiler.py</code> in read-only form, returning fact IDs instead of a statement &mdash; which is why it does not need the ALLOWLIST, the enum validation or the row caps, and why it is <strong>~2&ndash;3 PD</strong> rather than six.</p>
      <div class="callout violet">
        <span class="co-t">Non-negotiable</span>
        Selection is <strong>bounded by folder membership, not by prompt review</strong>. A prompt is not a control. The folder is the control; selection only decides what to read out of it.
      </div>
    `
  },

  promptmode: {
    title: 'reporting mode &middot; the third state of an existing switch',
    badge: 'null | explain | layman | ai',
    body: String.raw`
      <p>The reporting switch already exists with two positions. The AI mode is a <strong>third value of the same <code>useState</code></strong> &mdash; not a new page, not a new route, and not a replacement for the fixed visuals.</p>
      <h3>What is already there</h3>
      <pre class="code"><span class="c">// frontend/src/pages/ExecDashboard.tsx:40</span>
<span class="k">const</span> [overlay, setOverlay] = useState&lt;null | <span class="s">'explain'</span> | <span class="s">'layman'</span>&gt;(null);

<span class="c">// :70-76 &mdash; both existing modes, driven by two existing buttons</span>
&lt;DashHeader onExplain={() =&gt; setOverlay(<span class="s">'explain'</span>)} onLayman={() =&gt; setOverlay(<span class="s">'layman'</span>)} &hellip;

<span class="c">// :198-203 &mdash; both render into ONE component</span>
&lt;ExplainOverlay
  open={overlay !== null}
  title={&hellip;}
  body={overlay === <span class="s">'layman'</span> ? buildLayman(<span class="s">'exec'</span>, facts) : buildExplain(<span class="s">'exec'</span>, facts)}
  onClose={() =&gt; setOverlay(null)}
/&gt;</pre>
      <p>Adding the AI mode is one more arm of that ternary:</p>
      <pre class="code">body={overlay === <span class="s">'ai'</span>       ? aiNarrative                       <span class="c">// POST /reports-ai/generate</span>
     : overlay === <span class="s">'layman'</span> ? buildLayman(<span class="s">'exec'</span>, facts)
     :                     buildExplain(<span class="s">'exec'</span>, facts)}</pre>
      <h3>The seam is exactly one thing: <code>body: string</code></h3>
      <p><code>buildExplain(role, facts)</code> and <code>narrative_html</code> from the envelope are <strong>the same type</strong>. That is why the plan reuses <code>ExplainOverlay</code> unchanged and mounts the trigger through the <code>DashHeader</code> <code>children</code> slot (<code>DashHeader.tsx:36</code>) &mdash; the same slot on all six dashboards, with <strong>zero route changes</strong>, inheriting each dashboard&rsquo;s existing role gating.</p>
      <h3>Sanitisation is already in the path</h3>
      <p><code>ExplainOverlay.tsx:17</code> is <code>dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(body) }}</code>. Model HTML passes the identical sanitiser the deterministic HTML already passes &mdash; so <strong>the Phase B exit criterion is literally &ldquo;<code>ExplainOverlay</code> unchanged&rdquo;</strong>, and no new injection surface is introduced.</p>
      <h3>What does not change</h3>
      <p><code>StatCard</code>, <code>Gauge</code>, <code>MiniBarChart</code>, <code>Panel</code> and the tables still render from <code>useExecData()</code> exactly as before. The AI narrative is an overlay <em>on top of</em> the visuals &mdash; which is what the Phase B exit criterion means by &ldquo;all 8 report types render, offline and online, <strong>with identical numbers</strong>.&rdquo;</p>
      <h3>Where the facts come from &mdash; the one real difference</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th></th><th>Deterministic modes</th><th>AI mode</th></tr></thead>
        <tbody>
          <tr><td>Fact source</td><td><code>facts</code>, assembled <strong>client-side</strong> from the dashboard payload (<code>ExecDashboard.tsx:59-66</code>)</td><td><code>FactFolder</code>, assembled <strong>server-side</strong> by <code>canonical.py</code> through <code>tenant_filter()</code></td></tr>
          <tr><td>Why</td><td>The browser already holds a scoped payload</td><td>The model must never receive a row that has not passed <code>tenant_filter()</code></td></tr>
        </tbody>
      </table></div>
      <p>Two fact sources exist; <strong>only the server-side one feeds the model.</strong> That is why the plan says &ldquo;aggregate in SQL, <strong>never port the frontend&rsquo;s <code>mappers.ts</code></strong>&rdquo; &mdash; reusing the client-side mappers would put a second, unscoped-by-construction number source into the narrative path.</p>
      <div class="callout warn">
        <span class="co-t">A finding from tracing the code &mdash; worth briefing before any demo</span>
        <code>tenant_filter</code> is applied to <code>RiskScore</code> (<code>dashboard.py:21</code>) and <code>Alert</code> (<code>:22</code>) &mdash; but <strong>not</strong> to <code>ComplianceSnapshot</code>. And <code>facts.popia = d.popiaScore</code> (<code>ExecDashboard.tsx:62</code>) flows straight into <code>buildExplain()</code>. So the <strong>baseline deterministic narrative already renders an estate-wide compliance figure with no disclosure class and no scoping label</strong> &mdash; correction C2&rsquo;s silent bypass, live in the current product. The AI mode does not cause it and does not fix it; it makes it observable (typed disclosure plus check &#9315;).
      </div>
      <h3>How it degrades</h3>
      <p>If the tier is off, <code>GET /reports-ai/available</code> returns nothing to seed from and the <code>'ai'</code> state is never entered &mdash; the user stays on <code>buildExplain</code>. If the model is down, Layer 4 returns the deterministic template with <code>fallback_used: true</code>. Either way the ternary resolves to something that was already working.</p>
    `
  },

  seeds: {
    title: 'Seeded prompts &middot; the 8 catalogue entries',
    badge: 'PROMPT_SEEDS &middot; editable &middot; not permissions',
    body: String.raw`
      <p><code>GET /api/v1/reports-ai/seeds</code> returns the catalogue entries <strong>filtered to what this caller may use</strong>. Each is a <strong>starting point the user can edit</strong> &mdash; not a permission and not a fixed template.</p>
      <h3>What changes conceptually</h3>
      <div class="callout ok">
        <span class="co-t">The catalogue stops being authorisation</span>
        The claim matrix was <strong>always keyed by role</strong> (<code>ClaimClass &times; role</code>), never by report type &mdash; the report type only co-varied with the role because the catalogue matrix is also role-scoped. So prompt-driven reporting removes a convenience, not a control. <strong>&ldquo;Here is something to start from&rdquo;</strong> replaces &ldquo;here is what you may have&rdquo;.
      </div>
      <h3>The eight seeds</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Seed</th><th>Scope class</th><th>Roles it is offered to</th><th>Phase</th></tr></thead>
        <tbody>
          <tr><td><code>executive_briefing</code></td><td>tenant (province/estate)</td><td>exec, compliance, transversal-admin</td><td><strong>POC</strong></td></tr>
          <tr><td><code>compliance_status</code></td><td><strong>estate-wide &mdash; disclosed</strong></td><td>exec, compliance, transversal-admin</td><td><strong>POC</strong></td></tr>
          <tr><td><code>peer_benchmark</code></td><td>tenant + anonymised peers</td><td>exec, compliance, transversal-admin</td><td>B</td></tr>
          <tr><td><code>department_monthly</code></td><td>tenant (single dept)</td><td>appsec, dbsec, transversal-admin, dept-admin, branch-admin, province-dept-admin</td><td>B</td></tr>
          <tr><td><code>soc_shift_handover</code></td><td>tenant</td><td>soc, appsec, province-soc-lead, transversal-admin</td><td>B</td></tr>
          <tr><td><code>appsec_posture</code></td><td>tenant</td><td>soc, appsec, local-appsec, transversal-admin</td><td>B</td></tr>
          <tr><td><code>dbsec_posture</code></td><td>tenant</td><td>dbsec, transversal-admin</td><td>B</td></tr>
        </tbody>
      </table></div>
      <p><strong>The 9 newly-covered roles</strong> are added with seeds appropriate to their derived claim sets, so nobody is silently denied: <code>dept-admin</code> and <code>province-dept-admin</code> get <code>department_monthly</code>; <code>branch-admin</code> gets a branch-scoped variant; <code>local-appsec</code> gets <code>appsec_posture</code>; <code>province-soc-lead</code> gets <code>soc_shift_handover</code>; <code>sre</code> gets a connector-health narrative; <code>admin</code> and <code>operator</code> get the full seed set. <strong>Seed availability is a convenience derived from the claim map &mdash; never a grant.</strong></p>
      <h3>Gate 1 semantics, restated</h3>
      <p>From <code>require_report_permission(role, report_type)</code> to <strong>&ldquo;may this role generate narrative, and which claim set applies?&rdquo;</strong> The claim set is resolved <strong>server-side, per request</strong>, and recorded in the envelope as <code>claim_classes_applied</code>. A seed the user edits beyond its original scope does not widen the claim set &mdash; the claim set comes from the role, and the scope comes from the JWT.</p>
      <h3>Auditability</h3>
      <p>Every request stores <code>prompt_source = 'seed'</code>, the <code>report_type</code>, and the <strong>redacted <code>prompt_text</code> actually used</strong> &mdash; the seed plus the user&rsquo;s edits, not the pristine template. Otherwise a narrative cannot be reproduced or reviewed.</p>
    `
  },

  freeform: {
    title: 'Free-text prompting',
    badge: 'PHASE A+ &middot; GATED ON S4 &middot; same four checks',
    body: String.raw`
      <p>The user writes their own request instead of editing a seed. <strong>This is a Phase A+ capability and it is gated</strong> &mdash; not on effort, but on suite <strong>S4</strong> being widened and green, because free-text prompting promotes S4 from one suite among ten to the control the whole disclosure model rests on.</p>
      <h3>The gate, stated precisely</h3>
      <div class="callout danger">
        <span class="co-t">Why S4 becomes load-bearing</span>
        With eight fixed templates, the <strong>template</strong> constrained the output shape. Remove the template and the <strong>claim filter is the only thing</strong> preventing an <code>exec</code> from receiving CVE identifiers, alert UUIDs, owner names or rule IDs. S4 currently scans <code>exec</code> output for those patterns against a known matrix; it must now scan <strong>arbitrary prompts</strong> from <strong>every role</strong>.
      </div>
      <h3>Widened S4 &mdash; what it must now prove</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Assertion</th><th>Why</th></tr></thead>
        <tbody>
          <tr><td>For every (role &times; claim class) pair, seeded <strong>and</strong> free-text, output contains zero artefacts of an unheld class</td><td>The core property, generalised past the 5-role matrix</td></tr>
          <tr><td>The resolved <code>claim_set</code> is a <strong>subset</strong> of the role&rsquo;s map entry, on every request</td><td>A prompt cannot widen the claim set</td></tr>
          <tr><td>An unknown role resolves to the <strong>empty set</strong>, never a default</td><td>Default-dend preserved under a new entry point</td></tr>
          <tr><td>Holding <code>{"*"}</code> in <code>ROLES_HIERARCHY</code> does <strong>not</strong> imply any claim class</td><td>Permission wildcard &ne; claim wildcard</td></tr>
          <tr><td>Every fact ID returned by selection is a member of the folder addressed by <code>folder_hash</code></td><td>Selection cannot reach outside the folder</td></tr>
          <tr><td>A prompt attempting prompt extraction returns no template, claim list or claim-set contents</td><td>New vector &mdash; the user&rsquo;s own keyboard</td></tr>
          <tr><td>The redacted <code>prompt_text</code> written to <code>ai.report</code> matches the prompt submitted, modulo redactions</td><td>Reproducibility of every narrative</td></tr>
        </tbody>
      </table></div>
      <h3>The user prompt is a new injection vector</h3>
      <p>Same class as S9&rsquo;s warehouse-field injection, except the keyboard is now the vector. Checks &#9312;/&#9313;/&#9314; catch scope-widening and claim violations. <strong>Prompt extraction</strong> &mdash; &ldquo;print your instructions verbatim&rdquo; &mdash; is a new, low-severity leak of the template and claim set, and S4 now asserts it returns nothing.</p>
      <h3>Three smaller consequences, stated honestly</h3>
      <ul>
        <li><strong>NFR-AI-14 now applies to prompt parameters.</strong> &ldquo;Eastern Cape&rdquo; versus the <code>eastern-cape</code> slug must fail <strong>loudly</strong>, exactly as province slugs do &mdash; silent zero rows would read as clean data.</li>
        <li><strong>Disclosure labelling is harder.</strong> With <code>compliance_status</code> you know upfront it is estate-wide. With a free prompt the model may reach for a national fact in something that reads as departmental. Check &#9315; catches it, but it is leaned on harder than before.</li>
        <li><strong>Redaction now applies to input.</strong> The user prompt is stored and is untrusted text; it goes through <code>redaction.py</code> before it is persisted and before it is placed in any prompt.</li>
      </ul>
      <h3>What free-text prompting does <em>not</em> change</h3>
      <p>Layer 1 scope resolution, the folder boundary, the four checks, the disclosure classes, the one-atomic-commit ledger, digest pinning and the five-part cache key are all unchanged. <strong>The model still never receives a row that has not passed <code>tenant_filter()</code>.</strong> Free-text prompting widens what may be <em>asked</em>, never what may be <em>seen</em>.</p>
      <div class="callout violet">
        <span class="co-t">Sequencing</span>
        <strong>1.</strong> Complete and sign the 14-role claim map (Compliance) &rarr; <strong>2.</strong> Widen S4 and make it a gate &rarr; <strong>3.</strong> Build <code>canonical.py</code> + <code>select.py</code>, store <code>prompt_text</code> &rarr; <strong>4.</strong> Ship seeded prompting &rarr; <strong>5.</strong> then open free-text. Steps 1&ndash;3 are mostly small and mostly already designed; step 5 is a one-line change to Gate 1. The risk is not in the code &mdash; it is that S4 becomes load-bearing, and that belongs green <em>before</em> a demo, not after.
      </div>
    `
  },

  aiprompts: {
    title: 'Layer 3 &middot; ai\\prompts\\',
    badge: 'narrative generation &middot; THE ONLY MODEL LAYER',
    body: String.raw`
      <p>Prompts are <strong>assembled by code in versioned immutable modules</strong>, not hand-edited YAML (supersedes G1 &sect;4A.2, G2 &sect;8).</p>
      <h3>What that buys</h3>
      <ul>
        <li><code>prompt_version</code> is an <strong>integer</strong> in <code>ai.report</code> and the audit row &mdash; a narrative can always be traced to the exact prompt text that produced it</li>
        <li>The diff is reviewed like code</li>
        <li>NFR-AI-09&rsquo;s inventory is a registry, not a filesystem crawl</li>
      </ul>
      <h3>The prompt is not the control</h3>
      <pre class="code">prompt = template
      + pack.serialise(allowed=claims)      <span class="c"># the DATA BOUNDARY, not a rule</span>
      + allowed_claim_list
      + scope_block.labelled(<span class="s">"for_attribution"</span>)  <span class="c"># disclosure, not control</span>

<span class="c"># model receives:  NO db handle   NO sql   NO tools</span></pre>
      <p><code>pack.serialise(allowed=claims)</code> <strong>physically removes</strong> facts the role may not hold. They are not in the payload. That is the difference between a boundary and an instruction.</p>
      <h3>Catalogued in this file</h3>
      <div class="file-list"><span class="file-tag">executive_briefing.py (POC)</span><span class="file-tag">compliance_status.py (POC)</span><span class="file-tag">peer_benchmark.py (B)</span><span class="file-tag">soc_shift_handover.py (B)</span><span class="file-tag">appsec_posture.py (B)</span><span class="file-tag">dbsec_posture.py (B)</span><span class="file-tag">department_monthly.py (B)</span></div>
      <p><strong>Eight report types are the target; the POC delivers two</strong> (correction C6).</p>
      <h3>Rebuild the examples from live fact packs (correction C4)</h3>
      <div class="callout warn">
        <span class="co-t">A prompt example seeded with a wrong number teaches the model to produce it</span>
        G2 &sect;6 offered &ldquo;estate risk is 62&rdquo; as example <code>exec</code> output. <strong>Live max <code>fused_score</code> is 25.2, average 7.46, and the <code>critical</code> bucket is empty.</strong> Prompt examples and the eval set <strong>must be rebuilt from live fact packs before any quality claim is made</strong>.
      </div>
    `
  },

  aigen: {
    title: 'Layer 3 &middot; ai\\generate.py',
    badge: 'orchestrator &middot; NFR-AI-13 identity test',
    body: String.raw`
      <p>The orchestrator for the one layer that can fail open. It assembles the prompt, calls the gateway, runs the verifier, and decides between model text and the deterministic template.</p>
      <h3>The fallback is not a degraded path</h3>
      <div class="callout ok">
        <span class="co-t">Layers 1 + 2 with a template in place of Layer 3</span>
        It reads the <strong>identical fact view</strong>, so it cannot show different numbers. NFR-AI-13 asserts this by <strong>object identity</strong> &mdash; not by comparing two outputs, which would pass even if the fallback quietly computed something different.
      </div>
      <p><strong>NFR-AI-07</strong> (AI failure must not degrade any dashboard) rests on the same property, and is verified by fault injection at Phase A exit. Grafana is unaffected entirely &mdash; it stays numeric-only.</p>
      <h3>Order of operations</h3>
      <ol class="steps">
        <li>Gate 1 authorisation (Layer 1) &mdash; default-deny</li>
        <li>Fact assembly to a pure <code>fact_pack</code> + <code>fact_pack_hash</code> (Layer 2)</li>
        <li><strong>Redaction gate immediately before egress</strong> &mdash; not inside the gateway, so a gateway-provider swap cannot bypass it</li>
        <li>Gateway call with <code>CircuitBreaker</code>; token cap fixed day 1 on measured latency</li>
        <li>Four verification checks (Layer 4) &mdash; any failure discards the model text</li>
        <li>Write <code>ai.report</code> + an audit row in <strong>one atomic commit</strong>, then return the envelope</li>
      </ol>
      <h3>Disclosure classes applied</h3>
      <p>Reads <code>pack.serialise(allowed=claims)</code> from Layer 2 and the typed disclosure set, and passes both into the prompt &mdash; the claims list decides what survives serialisation, the disclosure classes decide what the prose must say about provenance.</p>
      <p><em>Correction C2 reminder: a tenant-scoped figure that consumes an estate-wide column must be declared <code>DERIVED_FROM_ESTATE_WIDE</code> &mdash; that is what check &#9315; tests.</em></p>
    `
  },

  ail4: {
    title: 'Layer 4 &middot; ai\\verify.py',
    badge: 'four checks &middot; NO MODEL &middot; S8',
    body: String.raw`
      <p>The verifier is the control. It runs <strong>after</strong> generation, is <strong>independent of the prompt</strong>, and on <strong>any failure returns a deterministic template</strong> &mdash; never model text.</p>
      <h3>The four checks</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>#</th><th>Check</th><th>Method</th><th>Fails on</th></tr></thead>
        <tbody>
          <tr><td>&#9312;</td><td><strong>Numeral fidelity</strong></td><td>Extract every number from the prose; assert membership in the fact pack</td><td>Any ungrounded figure &mdash; <strong>100%, no tolerance</strong> (NFR-AI-04)</td></tr>
          <tr><td>&#9313;</td><td><strong>Claim class</strong></td><td>Scan for unheld classes: <code>CVE-\d{4}-\d+</code>, alert UUIDs, owner names, rule ids</td><td>Any sentence holding a class the role does not hold &mdash; <strong>discard the sentence</strong> (S4)</td></tr>
          <tr><td>&#9314;</td><td><strong>Scope containment</strong></td><td>No entity outside <code>ReportScope</code> may be named</td><td>A scoped user naming another province; <code>expression.false()</code> must yield empty, <strong>never estate-wide</strong> (S3)</td></tr>
          <tr><td>&#9315;</td><td><strong>Attribution</strong></td><td>Estate-wide facts must be said to be estate-wide</td><td>Presenting <code>ESTATE_WIDE</code> or <code>DERIVED_FROM_ESTATE_WIDE</code> facts as department-scoped (R-AI-11)</td></tr>
        </tbody>
      </table></div>
      <p>Check &#9313; exists because of <strong>correction C7</strong>: G1 treated the verifier as numeral fidelity only. That is insufficient, because <strong>roles may request a report but not see everything in it</strong>. The claim filter is what makes role-aware prompting safe at all.</p>
      <h3>Why set-membership and regex, not a model critic</h3>
      <ul>
        <li><strong>Independent.</strong> A model-based critic shares the writer&rsquo;s blind spots and can be argued into the same error.</li>
        <li><strong>Provable without a model.</strong> Verification is testable with Ollama stopped &mdash; which is what makes NFR-AI-04 and NFR-AI-06 CI gates rather than aspirations.</li>
        <li><strong>Cheap.</strong> Four passes over a few hundred tokens. With <strong>no GPU</strong> (C1), latency is the binding constraint.</li>
      </ul>
      <h3>Failure is a feature</h3>
      <p>On failure the envelope returns <code>fallback_used: true</code> with a deterministic template over the same facts. The caller cannot tell whether a model wrote it &mdash; and <em>does not need to</em>, because the numbers are identical either way. That honesty is why the flag is part of the contract rather than a log line.</p>
      <div class="callout violet">
        <span class="co-t">A critic may be added &mdash; conditionally</span>
        Phase 2 may add one <strong>if</strong> a latency budget and a measured need appear. Not before.
      </div>
    `
  },

  aigw: {
    title: 'ai\\gateway.py',
    badge: '+ NEW &middot; Phase A &middot; Ollama + CircuitBreaker',
    body: String.raw`
      <p>The <strong>only</strong> path from the platform to a model. There is no second egress route &mdash; which is what makes &ldquo;no SaaS LLM&rdquo; an architectural fact rather than a policy statement.</p>
      <h3>Contents</h3>
      <ul>
        <li>HTTP client for <code>http://localhost:11434</code> &mdash; Ollama 0.35.1, PID 27452</li>
        <li><strong>Model registry pinned by digest</strong> &mdash; <code>qwen2.5:3b</code>, pulled day 1 (~2.0 GB)</li>
        <li><strong><code>CircuitBreaker</code> reuse</strong> from <code>app\ingestion\circuit_breaker.py:11</code> &mdash; the class that already protects OEM polling</li>
        <li>Prompt assembly for the one model layer</li>
        <li>Timing and token accounting for the <code>llm_*</code> Prometheus collectors</li>
      </ul>
      <h3>Why not vLLM (correction C1)</h3>
      <div class="callout ok">
        <span class="co-t">R-AI-7 CLOSED</span>
        G1 specified self-hosted vLLM on a 1&times;80 GB GPU with CAPEX. Verified 6 October: <strong>Ollama 0.35.1 is installed and running</strong>, and <code>qwen2.5:3b</code> fits the host &mdash; i5-11400H, 6-core, <strong>no GPU</strong>, 15.6 GB RAM, 84.3 GB free. <strong>Zero CAPEX, zero procurement lead time.</strong> GPU/vLLM is deferred to a <strong>Phase C scale decision</strong>, re-evaluated against the measured NFR-AI-02 latency.
      </div>
      <h3>NFR-AI-07 &mdash; availability</h3>
      <p>AI failure must not degrade any dashboard (M/M, R-AI-3), verified by fault injection at Phase A exit. Breaker opens &rarr; Layer 3 is skipped &rarr; template over the identical fact view. Grafana is unaffected entirely.</p>
      <h3>Configuration guard</h3>
      <p>Phase A promotes <code>llm_*</code> to <code>app\config.py</code> and extends <code>_guard_non_dev_defaults</code> so a non-dev environment with <code>llm_enabled=True</code> and no cluster-local <code>llm_base_url</code> plus a pinned digest <strong>fails at startup</strong>. Use <code>SecretStr</code>.</p>
    `
  },

  piredaction: {
    title: 'ai\\redaction.py',
    badge: '+ NEW &middot; Phase A &middot; mandatory pre-egress gate',
    body: String.raw`
      <p>A PII / OEM-payload scrubber sitting as a <strong>hard gate immediately before model egress</strong>. It is not a helper the caller may choose to invoke &mdash; no code path from Layer 3 to the gateway skips it.</p>
      <h3>Why it is positioned there</h3>
      <ul>
        <li><strong>Not inside the gateway.</strong> A gateway-provider swap (OD-11 being overturned) would then bypass it. Outside, the gate survives the swap.</li>
        <li><strong>Not inside accessors.</strong> Layers 1, 2 and 4 have no egress and need none.</li>
        <li><strong>Applied on the DR route too.</strong> R-AI-6 &mdash; sovereign DR must not become an egress path under pressure. <strong>Same gate, same policy, no exception for failover.</strong></li>
      </ul>
      <h3>It records what it stripped</h3>
      <p>Redaction emits a record of each removal. That proves nothing legitimate is being silently dropped &mdash; a corpus that only counts leaks cannot detect over-redaction &mdash; and makes NFR-AI-05 auditable after the fact, not only testable in CI.</p>
      <h3>Suite S10</h3>
      <p>A synthetic PII corpus through <code>redaction.py</code>; <strong>0 egress</strong> as a CI gate (NFR-AI-05). Deliberately synthetic rather than live <code>raw_data</code> &mdash; non-goal 5 states <strong>no raw <code>Finding.raw_data</code> to any model</strong>, so the corpus must not itself be real PII.</p>
      <h3>Also applied on the copilot path</h3>
      <p>Phase C runs redaction between aggregation and LLM&nbsp;#2, and Phase D redacts the <code>raw_data</code> excerpt before triage. One gate, three consumers &mdash; which is why it sits outside the gateway rather than inside it.</p>
    `
  },

  aiconf: {
    title: 'ai\\config.py',
    badge: '+ NEW &middot; Phase A &middot; prompt registry + digest pin',
    body: String.raw`
      <p>The promotion target for the POC&rsquo;s in-code prompt modules. Two responsibilities, both about <strong>making drift visible</strong>.</p>
      <h3>1. Prompt registry (NFR-AI-09)</h3>
      <p>Every prompt versioned and reviewed like code. <code>prompt_version</code> is an integer recorded in <code>ai.report</code> and the audit row, so a narrative traces to the exact prompt text that produced it.</p>
      <h3>2. Digest-pinned model registry (NFR-AI-08)</h3>
      <p>Model identity is a <strong>digest</strong>, not a tag. <code>qwen2.5:3b</code> can be re-pulled with different weights; a digest cannot drift silently.</p>
      <p>Together with the eval harness this closes <strong>two</strong> risks at once:</p>
      <ul>
        <li><strong>R-AI-8</strong> &mdash; prompt drift after a model upgrade silently degrades quality (High / M)</li>
        <li><strong>R-AI-12</strong> &mdash; a model upgrade changes behaviour with no regression signal (High / M)</li>
      </ul>
      <p>Both are answered by the same two controls: <strong>pin by digest</strong> and <strong>run the golden set in CI</strong>. Without the harness, NFR-AI-08 records what happened but does not prevent it.</p>
      <div class="callout violet">
        <span class="co-t">The kill switch is why routing lives in configuration</span>
        A Phase B exit criterion is &ldquo;a kill switch turns AI off for a tier <strong>without a deploy</strong>.&rdquo; That requirement is what forces model routing and the per-tier <code>llm_tier</code> flag to live in config rather than being hardcoded at the call site.
      </div>
    `
  },

  aicache: {
    title: 'ai\\cache.py',
    badge: '+ NEW &middot; Phase A &middot; S5 first',
    body: String.raw`
      <p>A Redis narrative cache keyed by <strong><code>(role, scope_hash, fact_pack_hash, prompt_version, model_digest)</code></strong> &mdash; five components, each closing a specific failure.</p>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Key component</th><th>Failure it prevents</th></tr></thead>
        <tbody>
          <tr><td><code>role</code></td><td>Serving a <code>soc</code>-permitted narrative (with CVEs and owner names) to an <code>exec</code></td></tr>
          <tr><td><code>scope_hash</code></td><td><strong>Serving one department&rsquo;s prose to another.</strong> Different scope &rarr; different hash &rarr; miss</td></tr>
          <tr><td><code>fact_pack_hash</code></td><td>Serving stale prose after the underlying facts changed</td></tr>
          <tr><td><code>prompt_version</code></td><td>Serving prose written by a superseded prompt</td></tr>
          <tr><td><code>model_digest</code></td><td>Serving prose from a different model than the audit row claims (NFR-AI-08)</td></tr>
        </tbody>
      </table></div>
      <div class="callout danger">
        <span class="co-t">An unscoped cache is a cross-tenant read path with better latency</span>
        <strong>Generate as a provincial user, replay the cache key as a national user.</strong> Different <code>scope_hash</code> must produce a <strong>cache miss, and no cross-serve</strong>. This is why the plan defers caching to Phase 2 &ldquo;after S5 cache-isolation is proven&rdquo; rather than shipping it with the POC.
      </div>
      <h3>Latency budget</h3>
      <p>NFR-AI-01 targets <strong>&le;8 s cached, &le;20 s cold</strong> (P95). The cache is what makes the cached target reachable on CPU-only inference, and is the mitigation for R-AI-9 alongside row/token caps and CPU-first sizing.</p>
    `
  },

  aisettings: {
    title: 'ai\\settings.py',
    badge: '+ NEW &middot; POC &middot; own BaseSettings',
    body: String.raw`
      <p>AI settings live in their own <code>Settings(BaseSettings)</code> during the POC. This is a <strong>non-interference decision</strong>, not a style preference: keeping them out of <code>app\config.py</code> is what holds the whole workstream to <strong>one added <code>include_router</code> line</strong> (ADR D-A8, correction C5).</p>
      <h3>POC settings</h3>
      <ul>
        <li><code>llm_enabled</code> &mdash; the kill-switch tier flag</li>
        <li><code>llm_base_url</code> &mdash; <code>http://localhost:11434</code></li>
        <li><code>llm_model</code> / <code>llm_model_digest</code></li>
        <li><code>llm_timeout</code>, <code>llm_max_tokens</code> &mdash; <strong>the token cap decided day 1 on measured latency</strong> (R21)</li>
        <li><code>llm_tier</code> &mdash; per-tier kill switch, Phase B</li>
      </ul>
      <h3>Phase A promotion</h3>
      <p>Promoted to <code>app\config.py</code> with <code>_guard_non_dev_defaults</code> extended, so a non-dev environment with <code>llm_enabled=True</code> and no cluster-local <code>llm_base_url</code> plus a pinned digest <strong>fails at startup</strong>. Use <code>SecretStr</code> &mdash; the existing plain-<code>str</code> secret fields are the root of the <code>.env</code>-handling problem.</p>
      <div class="callout ok">
        <span class="co-t">On the secret purge &mdash; closed as not-applicable</span>
        G1 listed purging <code>backend\.env</code>, <code>backend\certs\ag_signing_key.pem</code> and <code>backend\new_credentials.txt</code> as blocking gate items, claiming they were committed to the repository. Verified against the <strong>full git history of every branch</strong>: <code>git log --all</code> returns <em>never committed</em> for all three, <code>git ls-files</code> matching <code>.env|certs/|credentials|.pem</code> is empty, and all three are gitignored. <strong>No credential rotation is required on the evidence.</strong>
      </div>
    `
  },

  aicopilot: {
    title: 'ai\\copilot\\',
    badge: '+ NEW &middot; Phase C &middot; 6 weeks &middot; highest risk',
    body: String.raw`
      <p>The analyst copilot is the <strong>highest-risk</strong> capability in the programme (R-AI-1, likelihood M / impact <strong>Severe</strong>) because it is the one place a scoping defect becomes an <strong>interactive data leak</strong> rather than a report. It is also last, and it <strong>must not start before P0-4 lands</strong>.</p>
      <pre class="code">user question
    <span class="s">&#9660;</span>
LLM <span class="n">#1</span> &#8594; JSON-Schema-constrained intent       <span class="c">// no free-text output</span>
     { entity, filters{severity,source,app,category,status,date_range},
       agg{type,group_by,top_n} }
    <span class="s">&#9660;</span>
DETERMINISTIC COMPILER &#8594; SQLAlchemy Core
     &bull; fields map to an explicit <span class="k">ALLOWLIST</span> (no dynamic attrs)
     &bull; every enum validated against Severity / AlertStatus / RiskBucket
     &bull; date range &#8804; 400 days &middot; top_n &#8804; 50 &middot; hard row cap <span class="n">200</span>
    <span class="s">&#9660;</span>
scope = tenant_filter(claims, model)        <span class="c">&#9668;&#9472;&#9472; INJECTED BY CODE, NOT PROMPT</span>
    <span class="s">&#9660;</span>
compiled = scope.apply_to(constructed)     <span class="c">&#9668;&#9472;&#9472; scope cannot be omitted</span>
    <span class="s">&#9660;</span>
execute &#8594; aggregate (k-anonymity floor <span class="n">5</span>) &#8594; redact &#8594; LLM <span class="n">#2</span> &#8594; prose
                                          + cited finding IDs
                                          + the executed query plan shown to the user</pre>
      <p><strong>The model proposes <em>what to look for</em>; the code decides <em>what it may see</em>.</strong> <code>tenant_filter</code> is a straight-line statement in our code, not an instruction in a prompt.</p>
      <h3>Modules</h3>
      <div class="file-list"><span class="file-tag">intent.py &mdash; LLM #1, JSON-Schema constrained</span><span class="file-tag">compiler.py &mdash; ALLOWLIST to SQLAlchemy Core</span><span class="file-tag">router.py &mdash; streaming + query-plan display</span></div>
      <h3>Exit criteria</h3>
      <div class="callout ok">
        <span class="co-t">The exit test, stated as an attack</span>
        A <code>dept</code>-scoped user asking &ldquo;show findings in KwaZulu-Natal&rdquo; gets <strong>zero rows outside scope, with the query plan displayed</strong>. P0-4 self-test green. NFR-AI-02 P95 &le;15 s.
      </div>
      <h3>The streaming trap &mdash; why <code>nginx.conf</code> is in the tree</h3>
      <div class="callout danger">
        <span class="co-t">Works in dev, silently breaks in production</span>
        Vite&rsquo;s dev proxy <strong>does not buffer</strong>, so streaming appears to work during development. In production <code>nginx</code> buffers by default, so the stream arrives all at once or times out. <code>frontend\nginx.conf</code> needs <code>proxy_buffering off</code>, <code>proxy_cache off</code> and a raised <code>proxy_read_timeout</code>.
      </div>
      <h3>Dependencies</h3>
      <ul>
        <li><strong>P0-4 must be green</strong> &mdash; copilot is the capability that depends on scoping being provably correct</li>
        <li><strong>OD-6</strong> &mdash; the 0.5 FTE MLOps engineer. Unfunded, <strong>Phase C slips</strong> (R-AI-5)</li>
        <li><strong>OD-8</strong> &mdash; sovereign-cloud DR region/provider. Default: no DR endpoint</li>
        <li>GPU/vLLM re-evaluated here as a <strong>scale decision</strong>, not a prerequisite</li>
      </ul>
    `
  },

  aitriage: {
    title: 'ai\\triage\\',
    badge: '+ NEW &middot; Phase D &middot; advisory only',
    body: String.raw`
      <p>Finding triage assist runs <strong>out-of-band</strong>, after the normaliser and the warehouse write. A slow model must <strong>never stall <code>processing</code> consumers</strong> &mdash; which, with NFR-AI-03 (N03 &ge;200 findings/min sustained), is why this is a batch job rather than an inline call.</p>
      <h3>The model contract</h3>
      <pre class="code"><span class="c">// in: redacted raw_data excerpt, title, description, category, app tier + owner</span>
<span class="c">// JSON-schema output:</span>
{ suggested_severity, cwe_id, exploitability: low|med|high,
  confidence: 0..1, rationale, requires_human_review }</pre>
      <h3>Hard rules</h3>
      <ul>
        <li><strong>AI never mutates <code>warehouse.findings.severity</code>.</strong> For scores that are AG-audited, an autonomous severity change is indefensible.</li>
        <li><strong>Below the confidence floor (default 0.70) suggestions are not surfaced at all</strong> &mdash; not shown greyed out, not shown at all.</li>
        <li>Every suggestion <em>and</em> every accept/reject &rarr; <code>warehouse.finding_triage</code> <strong>and</strong> <code>audit.action_audit</code> (NFR-AI-10).</li>
        <li><strong>No raw <code>raw_data</code></strong> &mdash; redacted excerpt only, through the same mandatory gate.</li>
      </ul>
      <h3>Why a new table, not a new column</h3>
      <p><code>findings</code> already has row-width/TOAST bloat as an open risk; a JSON triage blob on the same row worsens it. <strong>A separate versioned table gives history and rollback for free</strong>, and lets tenancy columns be denormalised at write time exactly as <code>app\lake\writer.py:74-77</code> does for every other table.</p>
      <h3>Exit criteria</h3>
      <ul>
        <li>No suggestion below 0.70 rendered</li>
        <li>Every accept writes a triage row <strong>and</strong> an audit row with actor and model/prompt version</li>
        <li><strong>The labelled dataset accumulates toward the &ge;2&nbsp;000 decisions that make fine-tuning viable</strong> &mdash; which is also why non-goal 4 forbids fine-tuning before the eval harness <em>and</em> that dataset exist</li>
      </ul>
      <div class="callout warn">
        <span class="co-t">R-AI-4 rated High/High</span>
        Analysts over-trusting suggestions. Mitigation: floor 0.70, advisory-only, accept/reject logged <strong>and fed back</strong> &mdash; every decision becomes a labelled example that eventually calibrates the model. <strong>OD-7</strong> must also be answered: is a model trained on accepted decisions a &ldquo;decision&rdquo; requiring its own POPIA/AI-governance approval? Default: <strong>treat as yes</strong>.
      </div>
    `
  },

  airouter: {
    title: 'backend\\app\\api\\routers\\reports_ai.py',
    badge: '+ NEW &middot; the only new router &middot; POST-only',
    body: String.raw`
      <p>Added alongside the ten baseline routers. Mounted by <strong>one added line</strong> in <code>app\main.py:122-133</code> &mdash; the only router registration point in the codebase.</p>
      <h3>Routes</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Method</th><th>Path</th><th>Auth</th></tr></thead>
        <tbody>
          <tr><td><code>POST</code></td><td><code>/api/v1/reports-ai/generate</code></td><td>Gate 1 + Gate 2</td></tr>
          <tr><td><code>GET</code></td><td><code>/api/v1/reports-ai/available</code></td><td>Returns only the report types <strong>this caller</strong> may request</td></tr>
          <tr><td><code>GET</code></td><td><code>/api/v1/reports-ai/audit/{report_id}</code></td><td>Own reports only; <strong>reveals nothing about scope size</strong></td></tr>
          <tr><td><code>GET</code></td><td><code>/api/v1/reports-ai/grounding/{report_id}</code></td><td>Phase B &mdash; the exact fact pack the narrative was written from</td></tr>
        </tbody>
      </table></div>
      <h3>Why the path is <code>reports-ai</code> and not <code>reports</code></h3>
      <p>Supersedes G1 &sect;4A.4. Two reasons: separation from the existing report surface, and <strong>POST-only for all data routes</strong> because <code>frontend\src\api\demoInterceptor.ts:34-42</code> silently injects a demo tenant into any <code>GET</code> whose path contains <code>/findings|/metrics|/risks|/compliance|/dashboard|/public/summary</code>. A GET copilot route would be <strong>quietly hijacked in demo mode</strong>.</p>
      <h3>Gate 1 and Gate 2</h3>
      <ul>
        <li><strong>Gate 1</strong> (<code>require_report_permission</code>, default-deny) authorises the <strong>report type</strong></li>
        <li><strong>Gate 2</strong> is the per-fact path: <code>capability()</code> classification + typed disclosure + <code>pack.serialise(allowed=claims)</code></li>
      </ul>
      <p>Both are needed. Gate 1 alone would let an <code>exec</code> request an <code>exec</code> report and still be shown CVEs &mdash; which is exactly what the claim classes exist to prevent.</p>
      <h3>What the audit route deliberately does not reveal</h3>
      <p>Own reports only, and <strong>nothing about scope size</strong>. A caller who can learn &ldquo;your scope contains one department&rdquo; from the audit endpoint can use it as a tenancy oracle.</p>
      <h3>Phase B additions</h3>
      <p>CSV/PDF export, the <code>/grounding</code> traceability link, a per-tier kill switch without a deploy &mdash; and <strong>Grafana stays numeric-only</strong>: it must never be given a model endpoint.</p>
    `
  },

  ailedger: {
    title: 'ai.report &middot; audit.action_audit',
    badge: '+ NEW schema &middot; one atomic commit',
    body: String.raw`
      <p>Generation writes <strong>two</strong> rows in the <strong>same database</strong>, in <strong>one atomic commit</strong>: the narrative ledger row in the new <code>ai.report</code> table, and an audit row in the existing <code>audit.action_audit</code>.</p>
      <h3>Why not a separate reporting database (D1)</h3>
      <div class="callout violet">
        <span class="co-t">Atomicity is the whole reason</span>
        <code>audit.action_audit</code> is in the main database. Across two stores the generation row and the audit row stop being <strong>one atomic commit</strong> &mdash; which is precisely the property the audit design exists to protect. (OD-10, needed by POC day 1, default = <code>ai</code> schema in main DB.)
      </div>
      <p>See the <strong>Stage 3 ERD</strong> for the full column list and indexes.</p>
      <h3>Two integrity properties that must not be conflated</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Property</th><th>Meaning</th><th>Status in this file</th></tr></thead>
        <tbody>
          <tr><td><strong>Retention</strong></td><td>How long rows are kept</td><td class="yes">Same as <code>action_audit</code> (D5). Two periods across two audit stores is the kind of divergence an audit finding is written about</td></tr>
          <tr><td><strong>Immutability</strong></td><td>Rows cannot be altered after the fact</td><td class="cell-warn"><strong>Nominal only &mdash; Phase 0 P0-2.</strong> <code>init-db.sql:120-130</code> is <code>CREATE TABLE</code> plus two indexes: no trigger, no <code>RULE</code>, no <code>REVOKE</code></td></tr>
        </tbody>
      </table></div>
      <p>The DDL comment on <code>ai.report</code> reads <em>&ldquo;Append-only by convention. Immutability is Phase 0 P0-2.&rdquo;</em> That is the honest state of the system today, and P0-2 is what changes it.</p>
      <h3>What is in the row that matters</h3>
      <ul>
        <li><code>prompt_source</code> &mdash; <code>seed</code> or <code>freeform</code>, so a reviewer knows which disclosure surface produced the narrative</li>
        <li><code>prompt_text</code> &mdash; <strong>the redacted prompt actually used, including the user&rsquo;s edits</strong> &mdash; not the pristine template. Without it a narrative cannot be reproduced or reviewed</li>
        <li><code>claim_set</code> &mdash; the exact disclosure set in force, <strong>not the role name that implied it</strong></li>
        <li><code>fact_ids</code> &mdash; which facts selection chose, re-checkable against <code>folder_hash</code></li>
        <li><code>scope_hash</code> &mdash; <strong>byte-identical</strong> in the envelope, the cache key and the audit row</li>
        <li><code>model_digest</code> + <code>prompt_version</code> &mdash; NFR-AI-08 reproducibility</li>
        <li><code>fact_pack_hash</code> &mdash; the link to <code>/grounding</code></li>
        <li><code>verification</code> jsonb &mdash; the four checks&rsquo; actual counts, not a boolean</li>
        <li><code>fallback_used</code> &mdash; honest about which path produced the text</li>
        <li><code>narrative_html</code> &mdash; <strong>NULL on verifier failure</strong>, because the template is not model output</li>
        <li><code>report_type</code> &mdash; set for seeded requests, <strong>NULL for free-text</strong></li>
      </ul>
      <div class="callout violet">
        <span class="co-t">Redaction now covers input, not just output</span>
        The user prompt is untrusted text. It is scrubbed by <code>redaction.py</code> <strong>before it is persisted</strong> and before it is placed in any prompt, and the stored copy is the redacted one. That is why <code>prompt_text</code> is <code>TEXT</code> and not a raw echo of the request &mdash; and it is why S4 asserts the stored text matches the submission <em>modulo redactions</em>.
      </div>
      <h3>P0-3 makes this trail real</h3>
      <p>The only audit write in the baseline is inline at <code>exports_ag.py:209-221</code> &mdash; so alert ack/resolve, user CRUD and connector reset are <strong>unaudited</strong>. Phase 0 P0-3 introduces <code>app\audit.py::record_audit()</code> and calls it from every privileged mutation, because <strong>an unaudited trail is a shared defect, not an AI-only one</strong>, and the AI writes to the same trail.</p>
    `
  },

  aiaudit: {
    title: 'backend\\app\\audit.py',
    badge: '+ NEW &middot; Phase 0 P0-3 &middot; 0.5 PD',
    body: String.raw`
      <p>A reusable <code>record_audit()</code> helper, called from every privileged mutation. In the baseline the only audit write is <strong>inline</strong> at <code>app\api\routers\exports_ag.py:209-221</code>, which is why it is the only audited path.</p>
      <h3>Currently unaudited in the baseline</h3>
      <ul>
        <li>Alert acknowledge / resolve</li>
        <li>User CRUD (admin router)</li>
        <li>Connector reset</li>
      </ul>
      <h3>Why it gates the AI</h3>
      <p><strong>AI writes to the same trail.</strong> If <code>ai.report</code> inherits a trail where only some mutations are covered by nominal immutability, then the AI&rsquo;s auditability is only as good as the platform&rsquo;s. Phase 0 makes the trail real first; NFR-AI-10 &mdash; every AI recommendation traceable to a named decider &mdash; then has somewhere to point.</p>
      <div class="callout warn">
        <span class="co-t">P0-2 and P0-3 are a pair</span>
        P0-3 makes sure rows are <em>written</em>; P0-2 makes sure they cannot be <em>changed</em>. An auditable-looking narrative ledger is worse than an obviously unauditable one.
      </div>
    `
  },

  aitests: {
    title: 'backend\\tests\\test_ai_*',
    badge: '+ NEW &middot; S1&ndash;S10 + T33',
    body: String.raw`
      <p>Eleven new test files. <strong>Every claim in the plan is worth only as much as its test</strong> &mdash; which is why the architecture is layered around what is provable without a model.</p>
      <div class="file-list"><span class="file-tag">test_ai_roles.py</span><span class="file-tag">test_ai_scope_containment.py</span><span class="file-tag">test_ai_scope_escalation.py</span><span class="file-tag">test_ai_claims.py</span><span class="file-tag">test_ai_cache_isolation.py</span><span class="file-tag">test_ai_signature.py</span><span class="file-tag">test_ai_capability.py</span><span class="file-tag">test_ai_numerals.py</span><span class="file-tag">test_ai_adversarial.py</span><span class="file-tag">test_ai_redaction.py</span><span class="file-tag">test_ai_bucket_band.py</span></div>
      <h3>What each proves</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Suite</th><th>Pass criterion</th><th>Phase</th></tr></thead>
        <tbody>
          <tr><td><strong>S1</strong> role matrix</td><td>All <strong>14</strong> roles &times; 8 report types; unknown role &rarr; 403; <strong>a role-count change fails the suite</strong></td><td>POC&rarr;B</td></tr>
          <tr><td><strong>S2</strong> scope containment</td><td>Zero rows with <code>department_id</code> outside the province-expanded set</td><td>POC</td></tr>
          <tr><td><strong>S3</strong> scope non-escalation</td><td>Verifier rejects; <code>expression.false()</code> yields empty, <strong>never estate-wide</strong></td><td>POC</td></tr>
          <tr><td><strong>S4</strong> claim permission</td><td>Zero violations of unheld claim classes</td><td>POC</td></tr>
          <tr><td><strong>S5</strong> cache isolation</td><td>Different <code>scope_hash</code> &rarr; cache miss, no cross-serve</td><td>A</td></tr>
          <tr><td><strong>S6</strong> structural enforcement</td><td><code>scope: ReportScope</code> is the first positional parameter of <strong>every</strong> public function</td><td>POC</td></tr>
          <tr><td><strong>S7</strong> capability classification</td><td>No table escapes; <code>users</code> and <code>action_audit</code> raise</td><td>POC&rarr;A</td></tr>
          <tr><td><strong>S8</strong> numeral fidelity</td><td>100%; any failure discards the output</td><td>POC</td></tr>
          <tr><td><strong>S9</strong> adversarial</td><td>All rejected <strong>at the verifier even where the prompt permitted it</strong></td><td>POC</td></tr>
          <tr><td><strong>S10</strong> redaction</td><td>0 egress</td><td>A</td></tr>
          <tr><td><strong>T33</strong> bucket tripwire</td><td>0 rows with <code>30 &lt; fused_score &lt; 45</code> &mdash; the band where three bucket definitions disagree</td><td>POC&rarr;P0-5</td></tr>
        </tbody>
      </table></div>
      <h3>The three that carry the architecture</h3>
      <ul>
        <li><strong>S6</strong> is the regression preventer &mdash; a signature test, so it cannot be forgotten in review</li>
        <li><strong>S8</strong> carries NFR-AI-04 at <strong>100% with no tolerance</strong></li>
        <li><strong>S9</strong> requires rejection <strong>at the verifier</strong> rather than trusting the prompt to have prevented it</li>
      </ul>
      <h3>Baseline tests are untouched</h3>
      <p><code>test_tenancy.py</code> (84/84) and <code>test_exports_ag.py</code> (<code>:71-109</code>) are <span class="m-same">unchanged</span> &mdash; the AI path <strong>inherits</strong> the tenancy contract rather than reimplementing it. Note the gap that P0-4 closes: because <code>tenant_filter</code> is opt-in with no middleware, a passing tenant suite does not prove that <em>every</em> route is scoped.</p>
    `
  },

  aireportsTs: {
    title: 'frontend\\src\\api\\reportsAi.ts',
    badge: '+ NEW &middot; Phase B &middot; typed client',
    body: String.raw`
      <p>The typed API client for the AI path, mirroring the backend&rsquo;s Pydantic/OpenAPI schemas the same way the existing <code>src\api\</code> modules do &mdash; so a field rename surfaces as a <strong>compile error</strong>, not a runtime blank panel.</p>
      <h3><code>useReport&lt;T&gt;()</code></h3>
      <p>A hook wrapping <code>POST /reports-ai/generate</code>. Three things it deliberately exposes to the UI:</p>
      <ul>
        <li><code>fallback_used</code> &mdash; so the surface can honestly indicate a template was served</li>
        <li><code>verification</code> &mdash; the four checks&rsquo; actual counts, not a boolean</li>
        <li><code>disclosure</code> &mdash; the typed classes, rendered as an attribution marker</li>
      </ul>
      <h3>Why POST for everything</h3>
      <p><code>demoInterceptor.ts:34-42</code> silently injects a demo tenant into any <code>GET</code> whose path contains <code>/findings|/metrics|/risks|/compliance|/dashboard|/public/summary</code>. A GET copilot route would be <strong>quietly hijacked in demo mode</strong> &mdash; no error, no log, wrong data. POST for data routes removes the class of problem rather than relying on a path convention staying unchanged.</p>
      <p><em>Zero route changes required: the control mounts via the <code>DashHeader</code> <code>children</code> slot and inherits each dashboard&rsquo;s existing role gating.</em></p>
    `
  },

  aireportpanel: {
    title: 'frontend\\src\\components\\ReportPanel.tsx',
    badge: '+ NEW &middot; Phase B &middot; ExplainOverlay unchanged',
    body: String.raw`
      <p>Renders generated narrative through the <strong>existing <code>ExplainOverlay</code></strong> at <code>components\dashboard\ExplainOverlay.tsx</code>. That is the whole security argument for the UI: <code>DOMPurify</code> sanitisation is already in place at line 17, already shipped, already reviewed.</p>
      <h3>Why <code>ExplainOverlay</code> is reused unchanged</h3>
      <div class="callout ok">
        <span class="co-t">The injection surface already exists, and already works</span>
        Model output is <strong>untrusted text rendered as markup</strong>, and S9 injects through free-text warehouse fields specifically because those fields become part of a prompt. The renderer is the last line of defence &mdash; and it is <strong>already a sanitiser in production</strong> rather than something the AI workstream has to introduce and then trust. The Phase B exit criterion is literally &ldquo;<code>ExplainOverlay</code> unchanged&rdquo;.
      </div>
      <h3>What the panel must show</h3>
      <ul>
        <li><code>disclosure</code> markers &mdash; an estate-wide figure must <em>look</em> estate-wide (R-AI-11, High/Severe)</li>
        <li><code>fallback_used</code> when true</li>
        <li>A route to <code>GET /grounding/{report_id}</code> &mdash; the exact fact pack the narrative was written from</li>
        <li>The executed query plan for copilot answers &mdash; transparency as a control</li>
      </ul>
      <h3>Phase B exit criteria</h3>
      <p>All eight report types render, <strong>offline and online, with identical numbers</strong> &middot; every figure traceable to a fact pack &middot; <code>ExplainOverlay</code> unchanged &middot; a kill switch turns AI off for a tier <strong>without a deploy</strong>.</p>
      <p class="tbl-note">The frontend has <strong>no test runner</strong> &mdash; which is why these criteria are verified through the API contract and the backend suites rather than a frontend suite that does not exist yet.</p>
    `
  },

  pimetrics: {
    title: 'backend\\app\\monitoring\\metrics.py',
    badge: '~ CHANGED &middot; Phase A &middot; wiring a no-op stub',
    body: String.raw`
      <p><code>setup_metrics()</code> is <strong>currently a no-op stub</strong> in the baseline. Wiring it is part of Phase A, <strong>not an optional extra</strong> &mdash; because two NFRs are latency budgets, and a budget that is not measured is a wish.</p>
      <h3>Collectors added (1.5 PD)</h3>
      <ul>
        <li><code>llm_requests_total{model, capability, outcome}</code></li>
        <li><code>llm_request_duration_seconds</code> &mdash; <strong>NFR-AI-01 and NFR-AI-02 verification</strong></li>
        <li><code>llm_tokens_total</code></li>
        <li><code>llm_circuit_state</code> &mdash; R-AI-3</li>
      </ul>
      <h3>Latency budgets they verify</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>NFR</th><th>Target</th><th>Phase</th></tr></thead>
        <tbody>
          <tr><td>NFR-AI-01 narrative P95</td><td><strong>&le;8 s cached, &le;20 s cold</strong></td><td>A</td></tr>
          <tr><td>NFR-AI-02 copilot query P95</td><td><strong>&le;15 s</strong></td><td>C</td></tr>
          <tr><td>NFR-AI-03 triage throughput</td><td><strong>&ge;200 findings/min sustained</strong></td><td>D</td></tr>
        </tbody>
      </table></div>
      <h3>The CPU constraint makes these numbers architectural</h3>
      <p>There is <strong>no GPU</strong> (correction C1), so latency is the binding constraint, not capability. R21 is mitigated by deciding the token cap <strong>day 1 on measured latency</strong> rather than rehearsal day &mdash; which is only actionable if the histogram exists from day 1.</p>
      <div class="callout info">
        <span class="co-t">Grafana remains numeric-only</span>
        These collectors appear in the existing Grafana dashboard as <strong>metrics</strong>. <strong>No generated narrative ever reaches it</strong> &mdash; monitoring has exactly one property that prose does not: the number on the panel is the number in the metric.
      </div>
    `
  },

  aievals: {
    title: 'Eval harness &middot; CI release gate',
    badge: '~ CHANGED &middot; Phase A &middot; 2.5 PD',
    body: String.raw`
      <p>Golden fact packs act as a release gate in <code>.github\workflows\ci.yml</code>. This is the control that closes <strong>two</strong> risks at once.</p>
      <ul>
        <li><strong>R-AI-8</strong> &mdash; prompt drift after a model upgrade silently degrades quality (High / M)</li>
        <li><strong>R-AI-12</strong> &mdash; a model upgrade changes behaviour with no regression signal (High / M)</li>
      </ul>
      <p>Both are answered by the same two controls: <strong>pin the model by digest</strong> and <strong>run the golden set in CI</strong>. Without the harness, NFR-AI-08 records what happened but does not prevent it.</p>
      <h3>Why the golden set must be rebuilt from live data</h3>
      <div class="callout danger">
        <span class="co-t">Correction C4</span>
        G2 &sect;6 offered &ldquo;estate risk is 62&rdquo; as example <code>exec</code> output. <strong>Live max <code>fused_score</code> is 25.2, average 7.46, all 15&nbsp;283 rows bucket <code>safe</code>, and the <code>critical</code> bucket is empty.</strong> An eval set seeded with 62 tests the wrong system. The golden packs are generated from live fact packs, not from the prior plan&rsquo;s illustration.
      </div>
      <h3>CI gates added across the programme</h3>
      <div class="tbl-scroll"><table class="table">
        <thead><tr><th>Gate</th><th>Phase</th><th>What fails the build</th></tr></thead>
        <tbody>
          <tr><td>Egress rule</td><td>0 / P0-1</td><td>Any route that can issue an outbound call <strong>without an auth dependency</strong></td></tr>
          <tr><td>Eval harness</td><td>A</td><td>A model change that fails the golden fact packs</td></tr>
          <tr><td>Redaction corpus</td><td>A</td><td>Any PII egress from <code>redaction.py</code> (S10)</td></tr>
          <tr><td>Scope-escape suite</td><td>POC&rarr;A</td><td>Any cross-tenant row in any report (S2/S3)</td></tr>
          <tr><td>Role matrix</td><td>POC&rarr;B</td><td>A matrix cell that drifts, or a <code>ROLES_HIERARCHY</code> count change</td></tr>
          <tr><td>Signature test</td><td>POC</td><td>Any accessor whose first parameter is not <code>scope: ReportScope</code> (S6)</td></tr>
        </tbody>
      </table></div>
      <h3>Startup guard, extended</h3>
      <p>Phase A extends <code>_guard_non_dev_defaults</code> so a non-dev environment with <code>llm_enabled=True</code> and no cluster-local <code>llm_base_url</code> and pinned model digest <strong>fails at startup</strong> rather than at first inference.</p>
    `
  },

  gog: {
    title: 'infrastructure\\monitoring &mdash; Grafana',
    badge: '= UNCHANGED &middot; numeric only',
    body: String.raw`
      <p>Unchanged in the baseline, and intended to stay that way. This is the one place the AI workstream is explicitly forbidden from adding capability.</p>
      <div class="callout ok">
        <span class="co-t">Grafana stays numeric-only &mdash; it must never be given a model endpoint</span>
        A hard Phase B rule. Infrastructure monitoring reads Prometheus. Generated prose does not belong in an alerting surface, because monitoring has exactly one property that prose does not: <strong>the number on the panel is the number in the metric</strong>.
      </div>
      <h3>What it does receive</h3>
      <ul>
        <li><code>llm_requests_total{model, capability, outcome}</code></li>
        <li><code>llm_request_duration_seconds</code></li>
        <li><code>llm_tokens_total</code></li>
        <li><code>llm_circuit_state</code></li>
      </ul>
      <p>All four as <strong>metrics</strong>. The existing pipeline dashboards, connector health and Prometheus scrape config are <span class="m-same">untouched</span>.</p>
      <h3>Files &mdash; unchanged</h3>
      <div class="file-list"><span class="file-tag">monitoring\grafana-dashboards\sita-pipeline.json</span><span class="file-tag">monitoring\prometheus.yml</span></div>
    `
  }
};

const detailEl = document.getElementById('detail');

const STAGES = ['oem', 'connectors', 'staging', 'normaliser', 'findings', 'engines', 'warehouse', 'ingest', 'process', 'store', 'api', 'ui', 'reports',
  'ai', 'airouter', 'ail1', 'ail2', 'ail3', 'ail4', 'ailedger', 'aigw', 'piredaction', 'aicache', 'pimetrics', 'aievals', 'gog',
  'canonical', 'select', 'claims', 'seeds', 'promptmode', 'freeform'];

const FLOW_STAGE = {
  oem: 'ingest',
  connectors: 'ingest',
  staging: 'ingest',
  normaliser: 'process',
  findings: 'process',
  engines: 'process',
  warehouse: 'store',
  api: 'api',
  ui: 'ui',
  reports: 'reports',
  ai: 'ai',
  airouter: 'ai',
  ail1: 'ai',
  ail2: 'ai',
  ail3: 'ai',
  ail4: 'ai',
  ailedger: 'ai',
  aigw: 'ai',
  piredaction: 'ai',
  aicache: 'ai',
  pimetrics: 'ai',
  aievals: 'ai',
  gog: 'reports',
  canonical: 'ai',
  select: 'ai',
  claims: 'ai',
  seeds: 'ai',
  promptmode: 'ai',
  freeform: 'ai'
};

const STAGE_PATHS = {
  oem: [
    'backend\\app\\connectors\\appscan.py',
    'backend\\app\\connectors\\imperva.py',
    'backend\\app\\connectors\\apisec.py',
    'backend\\app\\connectors\\compliance.py'
  ],
  connectors: ['backend\\app\\connectors'],
  staging: [
    'backend\\app\\ingestion',
    'backend\\app\\lake',
    'backend\\app\\bus',
    'backend\\app\\entrypoints\\ingestion.py'
  ],
  normaliser: [
    'backend\\app\\processing\\normaliser.py',
    'backend\\app\\processing\\field_mapper.yaml',
    'backend\\app\\processing\\alert_dedup.py',
    'backend\\app\\processing\\alert_enricher.py'
  ],
  findings: [
    'backend\\app\\processing\\normaliser.py',
    'backend\\app\\models\\finding.py',
    'backend\\app\\api\\routers\\findings.py',
    'backend\\app\\processing\\field_mapper.yaml'
  ],
  engines: [
    'backend\\app\\processing\\alert_engine.py',
    'backend\\app\\processing\\alert_rules.yaml',
    'backend\\app\\processing\\alert_dedup.py',
    'backend\\app\\processing\\alert_enricher.py',
    'backend\\app\\processing\\risk_engine.py',
    'backend\\app\\processing\\risk_aggregator.py',
    'backend\\app\\processing\\compliance.py'
  ],
  warehouse: [
    'backend\\app\\models',
    'backend\\app\\db.py',
    'infrastructure\\scripts\\init-db.sql',
    'infrastructure\\scripts\\seed-demo.sql',
    'backend\\app\\api\\routers'
  ],
  ingest: [
    'backend\\app\\connectors',
    'backend\\app\\ingestion',
    'backend\\app\\lake',
    'backend\\app\\bus',
    'backend\\app\\entrypoints\\ingestion.py'
  ],
  process: [
    'backend\\app\\processing',
    'backend\\app\\dispatch',
    'backend\\app\\entrypoints\\processing.py',
    'backend\\app\\entrypoints\\dispatch.py',
    'backend\\app\\entrypoints\\analytics.py'
  ],
  store: [
    'infrastructure\\scripts\\init-db.sql',
    'infrastructure\\scripts\\seed-demo.sql',
    'backend\\migrations',
    'backend\\app\\models',
    'backend\\app\\db.py',
    'infrastructure\\docker-compose'
  ],
  api: [
    'backend\\app\\api',
    'backend\\app\\main.py',
    'backend\\app\\config.py',
    'backend\\app\\tenant.py',
    'backend\\app\\models\\tenant.py',
    'infrastructure\\nginx',
    'backend\\app\\ai',
    'reports_ai.py',
    'backend\\app\\audit.py'
  ],
  ui: ['frontend\\', 'reportsAi.ts', 'ReportPanel.tsx'],
  reports: [
    'frontend\\src\\pages',
    'frontend\\src\\hooks',
    'frontend\\src\\api',
    'frontend\\src\\data',
    'frontend\\src\\components',
    'frontend\\src\\context',
    'frontend\\src\\utils\\jwt.ts',
    'backend\\app\\api\\routers\\dashboard.py',
    'backend\\app\\dispatch',
    'infrastructure\\monitoring',
    'reportsAi.ts',
    'ReportPanel.tsx',
    'nginx.conf'
  ],
  ai: ['backend\\app\\ai', 'reports_ai.py', 'backend\\app\\audit.py', 'backend\\tests\\test_ai_'],
  airouter: ['reports_ai.py', 'backend\\app\\ai'],
  ail1: ['ai\\scope.py', 'api\\auth.py'],
  ail2: ['ai\\accessors.py', 'ai\\capability.py', 'ai\\disclosure.py'],
  ail3: ['ai\\prompts', 'ai\\generate.py'],
  ail4: ['ai\\verify.py'],
  ailedger: ['ai\\generate.py', 'init-db.sql', 'backend\\app\\audit.py'],
  aigw: ['ai\\gateway.py', 'circuit_breaker.py'],
  piredaction: ['ai\\redaction.py'],
  aicache: ['ai\\cache.py'],
  pimetrics: ['monitoring\\metrics.py'],
  aievals: ['ci.yml', 'backend\\tests\\test_ai_'],
  gog: ['grafana-dashboards', 'prometheus.yml'],
  canonical: ['ai\\canonical.py'],
  select: ['ai\\select.py'],
  claims: ['ai\\claims.py'],
  seeds: ['ai\\prompts', 'reports_ai.py'],
  promptmode: ['reports_ai.py', 'frontend\\src\\api\\reportsAi.ts'],
  freeform: ['ai\\select.py', 'ai\\claims.py', 'redaction.py'],
  ail2b: ['ai\\capability.py'],
  ail2c: ['ai\\disclosure.py'],
  aiprompts: ['ai\\prompts'],
  aigen: ['ai\\prompts', 'ai\\generate.py'],
  aiconf: ['ai\\config.py'],
  aisettings: ['ai\\settings.py'],
  aicopilot: ['ai\\copilot'],
  aitriage: ['ai\\triage'],
  aiaudit: ['backend\\app\\audit.py'],
  aitests: ['backend\\tests\\test_ai_'],
  aireportsTs: ['reportsAi.ts'],
  aireportpanel: ['ReportPanel.tsx'],
  aimaster: ['AI_INTEGRATION_PLAN_MASTER'],
  aidocs: ['\\docs\\'],
  aisuperseded: ['G1_AI_Integration_Plan']
};

function highlightStage(stage) {
  const prefixes = STAGE_PATHS[stage] || [];
  document.querySelectorAll('.tree .dir, .tree .file, .tree .root').forEach(el => {
    if (el.getAttribute('data-key') === 'root') return;
    const path = (el.textContent || '').replace(/\s+/g, ' ').trim();
    const isReportingNode = stage === 'reports' && el.getAttribute('data-key') === 'reporting';
    const hit = isReportingNode || prefixes.some(p => path.indexOf(p) !== -1);
    el.classList.toggle('hl', hit);
    el.classList.toggle('dim', !hit);
  });
  const linkedStage = FLOW_STAGE[stage] || stage;
  document.querySelectorAll('.stage-btn').forEach(b => {
    const s = b.getAttribute('data-stage');
    b.classList.toggle('hl', s === linkedStage);
  });
}

function clearStageHighlight() {
  document.querySelectorAll('.tree .hl, .tree .dim, .stage-btn.hl, .stage-flow .flow-node.hl, .stage-flow .flow-node.dim').forEach(el => {
    el.classList.remove('hl');
    el.classList.remove('dim');
  });
}

// ---- Stage 3: PostgreSQL ER diagram (built from the same DDL as init-db.sql) ----
const ERD_SCHEMAS = ['identity', 'staging', 'warehouse', 'archive', 'audit', 'ai'];
const ERD_BOX_W = 300, ERD_ROW_H = 15, ERD_HEAD_H = 30, ERD_PAD = 8, ERD_GAP_X = 26, ERD_GAP_Y = 48, ERD_SCHEMA_H = 30, ERD_MAX_W = 990;
const ERD_TABLES = [
  { schema: 'audit', name: 'action_audit', aiFlag: '~ P0-2 IMMUTABILITY', note: 'Audit sink \u2014 write only, NEVER_READ by the agent. Exists in init-db.sql:120-130 but was not previously drawn; Phase 0 P0-2 adds the trigger/RULE/REVOKE that make it genuinely immutable rather than nominal', uq: [], cols: [
    ['id', 'UUID', 'PK DF'],
    ['actor', 'VARCHAR(255)', 'NN'],
    ['action', 'VARCHAR(80)', 'NN'],
    ['resource_type', 'VARCHAR(60)', ''],
    ['resource_id', 'VARCHAR(80)', ''],
    ['detail', 'JSONB', ''],
    ['ip_address', 'INET', ''],
    ['created_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'ai', name: 'report', aiFlag: '+ NEW SCHEMA', note: 'AI narrative ledger \u2014 main DB (D1); retention = action_audit; immutability pending Phase 0 P0-2. prompt_text is REDACTED and stores the user prompt verbatim so any narrative can be reproduced and reviewed', uq: [], cols: [
    ['id', 'UUID', 'PK DF'],
    ['report_type', 'VARCHAR(40)', ''],
    ['prompt_source', 'VARCHAR(20)', 'DF NN'],
    ['prompt_text', 'TEXT', ''],
    ['actor', 'VARCHAR(255)', 'NN'],
    ['scope_hash', 'VARCHAR(80)', 'NN'],
    ['scope_class', 'VARCHAR(20)', 'NN'],
    ['claim_set', 'JSONB', 'NN'],
    ['fact_ids', 'JSONB', 'NN'],
    ['department_ids', 'JSONB', 'NN'],
    ['branch_ids', 'JSONB', 'NN'],
    ['prompt_version', 'INTEGER', 'NN'],
    ['model_id', 'VARCHAR(100)', 'NN'],
    ['model_digest', 'VARCHAR(80)', ''],
    ['fact_pack_hash', 'VARCHAR(80)', 'NN'],
    ['narrative_html', 'TEXT', ''],
    ['verification', 'JSONB', ''],
    ['disclosure', 'JSONB', ''],
    ['fallback_used', 'BOOLEAN', 'DF NN'],
    ['latency_ms', 'INTEGER', ''],
    ['created_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'finding_triage', aiFlag: '+ NEW PHASE D', note: 'Advisory triage suggestions \u2014 new versioned table, tenancy denormalised at write time; AI never mutates findings.severity', uq: [], cols: [
    ['id', 'UUID', 'PK DF'],
    ['finding_id', 'VARCHAR(36)', 'NN'],
    ['suggested_severity', 'VARCHAR(20)', ''],
    ['cwe_id', 'VARCHAR(20)', ''],
    ['exploitability', 'VARCHAR(10)', ''],
    ['confidence', 'NUMERIC(3,2)', 'NN'],
    ['rationale', 'TEXT', ''],
    ['requires_human_review', 'BOOLEAN', 'DF NN'],
    ['actor', 'VARCHAR(255)', 'NN'],
    ['model_digest', 'VARCHAR(80)', 'NN'],
    ['created_at', 'TIMESTAMPTZ', 'DF NN']
  ]},

  { schema: 'identity', name: 'users', note: 'RBAC users / JWT auth identities (tenant scope lists) \u2014 AI: NEVER_READ, zero agent read paths (NFR-AI-11); capability() raises', aiFlag: 'NEVER READ', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['email', 'VARCHAR(255)', 'UQ NN'],
    ['password_hash', 'VARCHAR(255)', 'NN'],
    ['display_name', 'VARCHAR(100)', ''],
    ['roles', 'JSONB', 'DF NN'],
    ['department_ids', 'JSONB', 'DF NN'],
    ['branch_ids', 'JSONB', 'DF NN'],
    ['is_active', 'BOOLEAN', 'DF NN'],
    ['created_at', 'TIMESTAMPTZ', 'DF NN'],
    ['updated_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'departments', note: 'Tenant: government departments (Department -> Branch -> App)', uq: ['UNIQUE (code)'], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['name', 'VARCHAR(120)', 'NN'],
    ['code', 'VARCHAR(60)', 'UQ NN']
  ]},
  { schema: 'warehouse', name: 'branches', note: 'Tenant branches: DDG-led units within each department', uq: ['UNIQUE (code)'], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['name', 'VARCHAR(120)', 'NN'],
    ['code', 'VARCHAR(60)', 'UQ NN'],
    ['department_id', 'VARCHAR(36)', 'NN']
  ]},
  { schema: 'staging', name: 'batch_runs', note: 'Poll-run traceability (provenance)', uq: [], cols: [
    ['id', 'UUID', 'PK DF'],
    ['connector', 'VARCHAR(50)', 'NN'],
    ['source', 'VARCHAR(100)', 'NN'],
    ['started_at', 'TIMESTAMPTZ', 'DF NN'],
    ['finished_at', 'TIMESTAMPTZ', ''],
    ['records_fetched', 'INTEGER', 'DF NN'],
    ['records_valid', 'INTEGER', 'DF NN'],
    ['records_rejected', 'INTEGER', 'DF NN'],
    ['status', 'VARCHAR(20)', 'DF NN'],
    ['error_message', 'TEXT', '']
  ]},
  { schema: 'staging', name: 'raw_records', note: 'Verbatim OEM payloads (7-day TTL)', uq: [], cols: [
    ['id', 'UUID', 'PK DF'],
    ['batch_id', 'UUID', 'FK NN'],
    ['source', 'VARCHAR(100)', 'NN'],
    ['external_id', 'VARCHAR(255)', ''],
    ['raw_payload', 'JSONB', 'NN'],
    ['received_at', 'TIMESTAMPTZ', 'DF NN'],
    ['ttl_expires_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'staging', name: 'rejected_records', note: 'Dead-letter queue for reprocessing (30-day TTL)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['batch_id', 'UUID', 'FK NN'],
    ['source', 'VARCHAR(100)', 'NN'],
    ['raw_payload', 'JSONB', 'NN'],
    ['rejection_reason', 'TEXT', 'NN'],
    ['rejection_code', 'VARCHAR(20)', 'NN'],
    ['rejected_at', 'TIMESTAMPTZ', 'DF NN'],
    ['reprocessed', 'BOOLEAN', 'DF NN'],
    ['reprocessed_at', 'TIMESTAMPTZ', ''],
    ['ttl_expires_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'connector_health', note: 'SRE: connector heartbeat / circuit-breaker state', uq: [], cols: [
    ['name', 'VARCHAR(50)', 'PK'],
    ['source', 'VARCHAR(100)', 'NN'],
    ['status', 'VARCHAR(20)', 'DF NN'],
    ['last_poll_at', 'TIMESTAMPTZ', ''],
    ['last_success_at', 'TIMESTAMPTZ', ''],
    ['latency_ms', 'INTEGER', ''],
    ['events_per_hour', 'INTEGER', ''],
    ['error_count', 'INTEGER', 'DF NN'],
    ['circuit_state', 'VARCHAR(20)', 'DF'],
    ['updated_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'findings', note: 'Canonical OEM findings, deduplicated per (source, external_id)', uq: ['UNIQUE (source, external_id)'], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['source', 'VARCHAR(100)', 'NN'],
    ['external_id', 'VARCHAR(255)', 'NN'],
    ['app_name', 'VARCHAR(255)', 'DF NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['severity', 'VARCHAR(20)', 'NN'],
    ['title', 'VARCHAR(500)', 'NN'],
    ['description', 'TEXT', ''],
    ['category', 'VARCHAR(200)', ''],
    ['raw_data', 'JSONB', ''],
    ['first_seen', 'TIMESTAMPTZ', 'NN'],
    ['last_seen', 'TIMESTAMPTZ', 'NN'],
    ['status', 'VARCHAR(50)', 'DF NN'],
    ['version', 'INTEGER', 'DF NN'],
    ['ingested_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'risk_scores', note: 'Daily fused risk score per application (tenant-scoped)', uq: ['UNIQUE (app_name, score_date)'], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['app_name', 'VARCHAR(255)', 'NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['score_date', 'DATE', 'NN'],
    ['fused_score', 'NUMERIC(5,1)', 'NN'],
    ['signal_appscan', 'NUMERIC(5,1)', ''],
    ['signal_imperva', 'NUMERIC(5,1)', ''],
    ['signal_api_exposure', 'NUMERIC(5,1)', ''],
    ['signal_compliance_penalty', 'NUMERIC(5,1)', ''],
    ['bucket', 'VARCHAR(20)', ''],
    ['computed_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'alerts', note: 'Unified alert feed with dedup counters (SOC, tenant-scoped)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['rule_id', 'VARCHAR(50)', 'NN'],
    ['title', 'VARCHAR(500)', 'NN'],
    ['description', 'TEXT', ''],
    ['severity', 'VARCHAR(20)', 'NN'],
    ['source', 'VARCHAR(100)', ''],
    ['target_id', 'VARCHAR(255)', ''],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['status', 'VARCHAR(20)', 'DF NN'],
    ['acknowledged_by', 'VARCHAR(100)', ''],
    ['acknowledged_at', 'TIMESTAMPTZ', ''],
    ['enriched_data', 'JSONB', ''],
    ['dedup_key', 'VARCHAR(64)', ''],
    ['dedup_count', 'INTEGER', 'DF NN'],
    ['first_triggered', 'TIMESTAMPTZ', 'NN'],
    ['last_triggered', 'TIMESTAMPTZ', 'NN'],
    ['resolved_at', 'TIMESTAMPTZ', ''],
    ['created_at', 'TIMESTAMPTZ', 'DF NN'],
    ['updated_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'dispatch_log', note: 'Out-of-band alert dispatch (email/PagerDuty/Teams, tenant-scoped)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['alert_id', 'VARCHAR(64)', 'NN'],
    ['channel', 'VARCHAR(20)', 'NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['status', 'VARCHAR(20)', 'DF NN'],
    ['error', 'TEXT', ''],
    ['attempted_at', 'TIMESTAMPTZ', 'NN'],
    ['created_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'compliance_snapshots', note: 'Compliance framework snapshots (12-week trend)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['framework', 'VARCHAR(50)', 'NN'],
    ['snapshot_date', 'DATE', 'NN'],
    ['overall_score', 'NUMERIC(5,1)', 'NN'],
    ['details', 'JSONB', ''],
    ['total_controls', 'INTEGER', 'NN'],
    ['passed_controls', 'INTEGER', 'NN'],
    ['computed_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'compliance_gaps', note: 'POPIA / ISO 27001 gaps & evidence tracking', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['framework', 'VARCHAR(50)', 'NN'],
    ['control_id', 'VARCHAR(50)', 'NN'],
    ['domain', 'VARCHAR(100)', ''],
    ['description', 'TEXT', 'NN'],
    ['owner', 'VARCHAR(100)', ''],
    ['severity', 'VARCHAR(20)', ''],
    ['due_date', 'DATE', ''],
    ['status', 'VARCHAR(30)', 'DF NN'],
    ['evidence_count', 'INTEGER', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'api_endpoints', note: 'API exposure inventory (AppSec, tenant-scoped)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['app_name', 'VARCHAR(255)', 'NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['endpoint', 'TEXT', 'NN'],
    ['method', 'VARCHAR(10)', 'DF NN'],
    ['is_shadow', 'BOOLEAN', 'DF NN'],
    ['exposure_score', 'NUMERIC(5,1)', 'DF NN'],
    ['discovered_at', 'TIMESTAMPTZ', 'DF NN'],
    ['last_seen', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'waf_blocks', note: 'Imperva WAF block telemetry (AppSec, tenant-scoped)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['app_name', 'VARCHAR(255)', 'NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['attack_type', 'VARCHAR(100)', ''],
    ['request_uri', 'TEXT', ''],
    ['action', 'VARCHAR(20)', 'DF NN'],
    ['src_ip', 'VARCHAR(45)', ''],
    ['block_time', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'system_metrics', note: 'SRE: CPU / memory / disk I/O / queue depth / uptime', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['metric', 'VARCHAR(50)', 'NN'],
    ['value', 'NUMERIC(8,2)', 'NN'],
    ['unit', 'VARCHAR(20)', 'DF NN'],
    ['recorded_at', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'agents', note: 'DAM / WAF agents and ingestion workers (SRE)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['name', 'VARCHAR(100)', 'NN'],
    ['role', 'VARCHAR(50)', 'NN'],
    ['version', 'VARCHAR(30)', 'NN'],
    ['status', 'VARCHAR(20)', 'DF NN'],
    ['host', 'VARCHAR(100)', ''],
    ['last_seen', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'warehouse', name: 'slo_metrics', note: 'SOC weekly MTTD / MTTR (SLO)', uq: ['UNIQUE (metric, week_start)'], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['metric', 'VARCHAR(20)', 'NN'],
    ['week_start', 'DATE', 'NN'],
    ['value_hours', 'NUMERIC(6,2)', 'NN']
  ]},
  { schema: 'warehouse', name: 'database_inventory', note: 'DBSec monitored databases & coverage (tenant-scoped)', uq: [], cols: [
    ['id', 'VARCHAR(36)', 'PK'],
    ['name', 'VARCHAR(100)', 'NN'],
    ['department_id', 'VARCHAR(36)', ''],
    ['branch_id', 'VARCHAR(36)', ''],
    ['engine', 'VARCHAR(50)', ''],
    ['monitored', 'BOOLEAN', 'DF NN'],
    ['agent_version', 'VARCHAR(30)', ''],
    ['last_heartbeat', 'TIMESTAMPTZ', 'DF NN']
  ]},
  { schema: 'archive', name: 'risk_scores', note: 'Historical retention: LIKE copy of warehouse.risk_scores', uq: ['LIKE warehouse.risk_scores INCLUDING ALL'], cols: [
    ['*all columns*', 'inherited from warehouse', '']
  ]},
  { schema: 'archive', name: 'alerts', note: 'Historical retention: LIKE copy of warehouse.alerts', uq: ['LIKE warehouse.alerts INCLUDING ALL'], cols: [
    ['*all columns*', 'inherited from warehouse', '']
  ]},
  { schema: 'archive', name: 'compliance_snapshots', note: 'Historical retention: LIKE copy of warehouse.compliance_snapshots', uq: ['LIKE warehouse.compliance_snapshots INCLUDING ALL'], cols: [
    ['*all columns*', 'inherited from warehouse', '']
  ]},
  { schema: 'archive', name: 'findings', note: 'Historical retention: LIKE copy of warehouse.findings', uq: ['LIKE warehouse.findings INCLUDING ALL'], cols: [
    ['*all columns*', 'inherited from warehouse', '']
  ]}
];

const ERD_LINKS = [
  ['staging::raw_records', 'batch_id', 'staging::batch_runs', 'id'],
  ['staging::rejected_records', 'batch_id', 'staging::batch_runs', 'id'],
  ['warehouse::branches', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::findings', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::findings', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::risk_scores', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::risk_scores', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::alerts', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::alerts', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::dispatch_log', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::dispatch_log', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::api_endpoints', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::api_endpoints', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::waf_blocks', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::waf_blocks', 'branch_id', 'warehouse::branches', 'id'],
  ['warehouse::database_inventory', 'department_id', 'warehouse::departments', 'id'],
  ['warehouse::database_inventory', 'branch_id', 'warehouse::branches', 'id']
];
const ERD_ROTATE = [
  ['warehouse::risk_scores', 'archive::risk_scores'],
  ['warehouse::alerts', 'archive::alerts'],
  ['warehouse::compliance_snapshots', 'archive::compliance_snapshots'],
  ['warehouse::findings', 'archive::findings']
];

function erdFlags(f) { return (f || '').split(' ').filter(Boolean); }
function erdTableH(t) { return ERD_HEAD_H + t.cols.length * ERD_ROW_H + (t.uq ? t.uq.length * ERD_ROW_H : 0) + ERD_PAD; }

function buildErd() {
  const host = document.getElementById('erdStore');
  if (!host) return;
  const pos = {};
  const schemaTop = {};
  let cursorY = 24, svgW = 0;
  ERD_SCHEMAS.forEach(schema => {
    const tables = ERD_TABLES.filter(t => t.schema === schema);
    if (!tables.length) return;
    schemaTop[schema] = cursorY + 8;
    cursorY += ERD_SCHEMA_H;
    let x = 30, rowY = cursorY, rowH = 0, rowCount = 0, rowMaxW = 0;
    tables.forEach(t => {
      const h = erdTableH(t);
      if (rowCount > 0 && x + ERD_BOX_W > ERD_MAX_W) {
        cursorY = rowY + rowH + ERD_GAP_Y;
        x = 30; rowY = cursorY; rowH = 0; rowCount = 0; rowMaxW = 0;
      }
      t.x = x; t.y = rowY; t.h = h; t.w = ERD_BOX_W;
      pos[schema + '::' + t.name] = t;
      rowH = Math.max(rowH, h);
      rowMaxW = Math.max(rowMaxW, x + ERD_BOX_W);
      rowCount++;
      x += ERD_BOX_W + ERD_GAP_X;
    });
    cursorY = rowY + rowH + ERD_GAP_Y;
    svgW = Math.max(svgW, rowMaxW + 24);
  });
  const svgH = cursorY + 8;

  function colY(t, colName) {
    const idx = t.cols.findIndex(c => c[0] === colName);
    const baseIdx = idx === -1 ? 0 : idx;
    return t.y + ERD_HEAD_H + baseIdx * ERD_ROW_H + ERD_ROW_H / 2;
  }

  const parts = [];
  parts.push('<svg viewBox="0 0 ' + svgW + ' ' + svgH + '" width="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="PostgreSQL warehouse ER diagram">');
  parts.push('<defs>'
    + '<marker id="erdArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="erd-arrow-h"/></marker>'
    + '<marker id="erdArrowRot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="erd-arrow-h-rot"/></marker>'
    + '</defs>');

  ERD_SCHEMAS.forEach(schema => {
    const tables = ERD_TABLES.filter(t => t.schema === schema);
    if (!tables.length) return;
    const y = schemaTop[schema];
    const xEnd = Math.max.apply(null, tables.map(t => t.x + t.w));
    parts.push('<text class="erd-schema-label" x="30" y="' + (y + 11) + '">' + schema.toUpperCase() + '</text>');
    parts.push('<line class="erd-line" x1="30" y1="' + (y + 15) + '" x2="' + xEnd + '" y2="' + (y + 15) + '" />');
  });

  ERD_TABLES.forEach(t => {
    const bx = t.x, by = t.y, bw = t.w, bh = t.h;
    parts.push('<g class="erd-box">');
    parts.push('<title>' + t.note + '</title>');
    parts.push('<rect x="' + bx + '" y="' + by + '" width="' + bw + '" height="' + bh + '" rx="9" class="erd-boxbg" + (t.aiFlag ? " erd-box-ai" : "") + " />');
    parts.push('<path d="M' + bx + ',' + (by + 9) + ' Q' + bx + ',' + by + ' ' + (bx + 9) + ',' + by + ' L' + (bx + bw - 9) + ',' + by + ' Q' + (bx + bw) + ',' + by + ' ' + (bx + bw) + ',' + (by + 9) + ' L' + (bx + bw) + ',' + (by + ERD_HEAD_H) + ' L' + bx + ',' + (by + ERD_HEAD_H) + ' Z" class="erd-head' + (t.aiFlag ? ' erd-head-ai' : '') + '" />');
    parts.push('<text class="erd-head-name" x="' + (bx + 12) + '" y="' + (by + ERD_HEAD_H - 9) + '">' + t.name + '</text>');
    if (t.aiFlag) parts.push('<text class="erd-flag-ai" x="' + (bx + bw - 10) + '" y="' + (by + ERD_HEAD_H - 18) + '" text-anchor="end">' + t.aiFlag + '</text>');
    parts.push('<text class="erd-head-schema" x="' + (bx + bw - 10) + '" y="' + (by + ERD_HEAD_H - 9) + '" text-anchor="end">' + t.schema + '.*</text>');
    t.cols.forEach((c, i) => {
      const ry = by + ERD_HEAD_H + i * ERD_ROW_H;
      const f = erdFlags(c[2]);
      parts.push('<line class="erd-line" x1="' + (bx + 8) + '" y1="' + ry + '" x2="' + (bx + bw - 8) + '" y2="' + ry + '" />');
      ['PK', 'UQ', 'FK'].forEach((b, bi) => {
        if (f.indexOf(b) === -1) return;
        const bxp = bx + 10 + bi * 28;
        parts.push('<rect x="' + bxp + '" y="' + (ry + 2.5) + '" width="24" height="10" rx="2" class="erd-badge-' + b.toLowerCase() + '" />');
        parts.push('<text class="erd-badge-' + b.toLowerCase() + '-t" x="' + (bxp + 12) + '" y="' + (ry + 10.5) + '" text-anchor="middle">' + b + '</text>');
      });
      const nn = f.indexOf('NN') !== -1;
      parts.push('<text class="' + (nn ? 'erd-col-name nn' : 'erd-col-name null') + '" x="' + (bx + 70) + '" y="' + (ry + 11) + '">' + c[0] + '</text>');
      parts.push('<text class="erd-col-type" x="' + (bx + bw - 10) + '" y="' + (ry + 11) + '" text-anchor="end">' + c[1] + '</text>');
    });
    (t.uq || []).forEach((u, i) => {
      const ry = by + ERD_HEAD_H + (t.cols.length + i) * ERD_ROW_H;
      parts.push('<line class="erd-line-dashed" x1="' + (bx + 8) + '" y1="' + ry + '" x2="' + (bx + bw - 8) + '" y2="' + ry + '" />');
      parts.push('<text class="erd-uq" x="' + (bx + 12) + '" y="' + (ry + 11) + '">' + u + '</text>');
    });
    parts.push('</g>');
  });

  ERD_LINKS.forEach(lk => {
    const s = pos[lk[0]], tt = pos[lk[2]];
    if (!s || !tt) return;
    const sy = colY(s, lk[1]), ty = colY(tt, lk[3]);
    const sx = s.x, tx = tt.x + tt.w, mid = (sx + tx) / 2;
    parts.push('<path class="erd-arrow" d="M' + sx + ',' + sy + ' C' + mid + ',' + sy + ' ' + mid + ',' + ty + ' ' + tx + ',' + ty + '" marker-end="url(#erdArrow)" />');
    parts.push('<text class="erd-link-label" x="' + mid + '" y="' + ((sy + ty) / 2 - 3) + '" text-anchor="middle">FK</text>');
  });

  ERD_ROTATE.forEach(lk => {
    const s = pos[lk[0]], tt = pos[lk[1]];
    if (!s || !tt) return;
    const sy = s.y + s.h / 2, ty = tt.y + tt.h / 2;
    const sx = s.x + s.w, tx = tt.x, mid = (sx + tx) / 2;
    parts.push('<path class="erd-arrow-rot" d="M' + sx + ',' + sy + ' C' + mid + ',' + sy + ' ' + mid + ',' + ty + ' ' + tx + ',' + ty + '" marker-end="url(#erdArrowRot)" />');
    parts.push('<text class="erd-link-label" x="' + mid + '" y="' + ((sy + ty) / 2 - 3) + '" text-anchor="middle">rotation</text>');
  });

  parts.push('</svg>');
  ERD_SVG_HTML = parts.join('');
  host.innerHTML = ERD_SVG_HTML;
  host.classList.add('erd-clickable');
  host.insertAdjacentHTML('beforeend', '<span class="erd-expand-hint">click to expand</span>');
  host.onclick = openErdModal;
}

// ---- ER diagram zoom modal (full-page overlay) ----
let ERD_SVG_HTML = '';
let ERD_SCALE = 1;
let erdDrag = null;

function erdViewBox() {
  const host = document.getElementById('erdZoomHost');
  const svg = host.querySelector('svg');
  if (!svg) return [0, 0, 1006, 1890];
  return (svg.getAttribute('viewBox') || '0 0 1006 1890').split(/\s+/).map(Number);
}

function erdApplyZoom(center) {
  const host = document.getElementById('erdZoomHost');
  const svg = host.querySelector('svg');
  const vp = document.getElementById('erdViewport');
  if (!svg || !vp) return;
  const vb = erdViewBox();
  const w = Math.round(vb[2] * ERD_SCALE), h = Math.round(vb[3] * ERD_SCALE);
  host.style.width = w + 'px';
  host.style.height = h + 'px';
  svg.setAttribute('width', w + 'px');
  svg.setAttribute('height', h + 'px');
  svg.style.width = w + 'px';
  svg.style.height = h + 'px';
  if (center) {
    vp.scrollLeft = Math.max(0, (w - vp.clientWidth) / 2);
    vp.scrollTop = Math.max(0, (h - vp.clientHeight) / 2);
  }
}

function erdSetZoom(k, center) {
  ERD_SCALE = Math.min(8, Math.max(0.2, k));
  erdApplyZoom(!!center);
}

function erdZoomFit() {
  const vb = erdViewBox();
  const pad = 40;
  const availW = window.innerWidth * 0.96 - pad;
  const availH = window.innerHeight * 0.92 - 64 - pad;
  ERD_SCALE = Math.min(availW / vb[2], availH / vb[3]);
  ERD_SCALE = Math.min(2.5, Math.max(0.15, ERD_SCALE));
  erdApplyZoom(true);
}

function openErdModal() {
  if (!ERD_SVG_HTML) return;
  const host = document.getElementById('erdZoomHost');
  host.innerHTML = ERD_SVG_HTML;
  ERD_SCALE = 1;
  erdApplyZoom(false);
  openModal(erdModal);
  erdZoomFit();
}

const erdModal = document.getElementById('erdModal');
const erdModalClose = document.getElementById('erdModalClose');
const erdViewport = document.getElementById('erdViewport');

if (erdModalClose) erdModalClose.addEventListener('click', () => closeModal(erdModal));
if (erdModal) erdModal.addEventListener('click', (e) => { if (e.target === erdModal) closeModal(erdModal); });
document.getElementById('erdZoomIn').addEventListener('click', () => erdSetZoom(ERD_SCALE * 1.25, true));
document.getElementById('erdZoomOut').addEventListener('click', () => erdSetZoom(ERD_SCALE / 1.25, true));
document.getElementById('erdZoomReset').addEventListener('click', () => erdSetZoom(1, true));
document.getElementById('erdZoomFit').addEventListener('click', erdZoomFit);

if (erdViewport) {
  erdViewport.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    erdSetZoom(ERD_SCALE * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
  }, { passive: false });

  erdViewport.addEventListener('pointerdown', (e) => {
    if (e.target.closest('button')) return;
    erdDrag = { x: e.clientX, y: e.clientY, sl: erdViewport.scrollLeft, st: erdViewport.scrollTop };
    erdViewport.classList.add('panning');
    try { erdViewport.setPointerCapture(e.pointerId); } catch (err) {}
  });
  erdViewport.addEventListener('pointermove', (e) => {
    if (!erdDrag) return;
    erdViewport.scrollLeft = erdDrag.sl - (e.clientX - erdDrag.x);
    erdViewport.scrollTop = erdDrag.st - (e.clientY - erdDrag.y);
  });
  const endErdDrag = () => { erdDrag = null; erdViewport.classList.remove('panning'); };
  erdViewport.addEventListener('pointerup', endErdDrag);
  erdViewport.addEventListener('pointercancel', endErdDrag);
}

function render(key) {
  document.querySelectorAll('[data-key]').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.stage-btn').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.flow-node').forEach(x => x.classList.remove('active'));
  const linkedStage = FLOW_STAGE[key] || key;
  const treeEl = document.querySelector('[data-key="' + key + '"]');
  const stageEl = document.querySelector('[data-stage="' + linkedStage + '"]');
  const flowEl = document.querySelector('[data-flow="' + key + '"]');
  if (treeEl) treeEl.classList.add('active');
  if (stageEl) stageEl.classList.add('active');
  if (flowEl) flowEl.classList.add('active');
  highlightFramework(key);
  const data = details[key];
  if (!data) return;
  detailEl.innerHTML = `
    <h2>&#128194; ${data.title} <span class="badge">${data.badge}</span></h2>
    ${data.body}
  `;
  if (key === 'store' && typeof buildErd === 'function') buildErd();
  if (STAGES.indexOf(key) !== -1) {
    highlightStage(key);
  } else {
    clearStageHighlight();
  }
}

function highlightFramework(key) {
  const BACKEND_STAGES = ['oem', 'connectors', 'staging', 'normaliser', 'findings', 'engines', 'warehouse', 'ingest', 'process', 'store', 'api'];
  const FRONTEND_STAGES = ['ui', 'reports'];
  const TENANCY_STAGES = ['tenancy'];
  const AI_KEYS = ['ai','airouter','ail1','ail2','ail2b','ail2c','ail3','ail4','ailedger','aigw','piredaction','aicache','pimetrics','aievals','gog',
    'aiprompts','aigen','aiconf','aisettings','aicopilot','aitriage','aiaudit','aitests','aireportsTs','aireportpanel','aimaster','aidocs','aisuperseded',
    'canonical','select','claims','seeds','promptmode','freeform'];
  const backendBtn = document.getElementById('backendFwBtn');
  const frontendBtn = document.getElementById('frontendFwBtn');
  const tenancyBtn = document.getElementById('tenancyBtn');
  const aiBtn = document.getElementById('aiIntegBtn');
  const diffBtn = document.getElementById('aiDiffBtn');
  const backend = BACKEND_STAGES.indexOf(key) !== -1;
  const frontend = FRONTEND_STAGES.indexOf(key) !== -1;
  const tenancy = TENANCY_STAGES.indexOf(key) !== -1;
  backendBtn.classList.toggle('active', backend);
  frontendBtn.classList.toggle('active', frontend);
  if (tenancyBtn) tenancyBtn.classList.toggle('active', tenancy);
  const ai = AI_KEYS.indexOf(key) !== -1;
  if (aiBtn) aiBtn.classList.toggle('active', ai);
  if (diffBtn) diffBtn.classList.toggle('active', ai);
  document.querySelectorAll('.stage-flow .flow-node').forEach(n => {
    const fw = n.getAttribute('data-fw');
    n.classList.toggle('dim', false);
    if (key === n.getAttribute('data-flow')) return;
    if (backend && fw === 'bk') n.classList.add('hl');
    else if (frontend && fw === 'fe') n.classList.add('hl');
    else n.classList.remove('hl');
  });
}

document.querySelectorAll('[data-key]').forEach(el => {
  el.addEventListener('click', () => render(el.getAttribute('data-key')));
});

document.querySelectorAll('.stage-btn').forEach(el => {
  el.addEventListener('click', () => render(el.getAttribute('data-stage')));
});

document.querySelectorAll('[data-flow]').forEach(el => {
  el.addEventListener('click', () => render(el.getAttribute('data-flow')));
});

// ---- OEM data approach modal ----
const oemModal = document.getElementById('oemModal');
const oemBtn = document.getElementById('oemApproachBtn');
const oemClose = document.getElementById('oemModalClose');

// ---- framework rationale modals ----
const backendFwModal = document.getElementById('backendFwModal');
const backendFwBtn = document.getElementById('backendFwBtn');
const backendFwClose = document.getElementById('backendFwClose');
const frontendFwModal = document.getElementById('frontendFwModal');
const frontendFwBtn = document.getElementById('frontendFwBtn');
const frontendFwClose = document.getElementById('frontendFwClose');

function openModal(modal) {
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  const closeBtn = modal.querySelector('.modal-close');
  if (closeBtn) closeBtn.focus();
}
function closeModal(modal) {
  modal.classList.remove('open');
  if (!document.querySelector('.modal-overlay.open')) {
    document.body.style.overflow = '';
  }
}
function closeAllModals() {
  document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  document.body.style.overflow = '';
}

function openOemModal() {
  openModal(oemModal);
}
function closeOemModal() {
  closeModal(oemModal);
}

oemBtn.addEventListener('click', openOemModal);
oemClose.addEventListener('click', closeOemModal);
oemModal.addEventListener('click', (e) => {
  if (e.target === oemModal) closeOemModal();
});

backendFwBtn.addEventListener('click', () => openModal(backendFwModal));
backendFwClose.addEventListener('click', () => closeModal(backendFwModal));
backendFwModal.addEventListener('click', (e) => {
  if (e.target === backendFwModal) closeModal(backendFwModal);
});

frontendFwBtn.addEventListener('click', () => openModal(frontendFwModal));
frontendFwClose.addEventListener('click', () => closeModal(frontendFwModal));
frontendFwModal.addEventListener('click', (e) => {
  if (e.target === frontendFwModal) closeModal(frontendFwModal);
});

// ---- tenancy deep-dive modal ----
const tenancyModal = document.getElementById('tenancyModal');
const tenancyBtn = document.getElementById('tenancyBtn');
const tenancyClose = document.getElementById('tenancyModalClose');
if (tenancyBtn && tenancyModal) {
  tenancyBtn.addEventListener('click', () => openModal(tenancyModal));
  tenancyClose.addEventListener('click', () => closeModal(tenancyModal));
  tenancyModal.addEventListener('click', (e) => {
    if (e.target === tenancyModal) closeModal(tenancyModal);
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeAllModals();
});

// ---- AI integration + change ledger + 4-layer modals ----
const aiIntegModal = document.getElementById('aiIntegModal');
const aiIntegBtn = document.getElementById('aiIntegBtn');
const aiIntegClose = document.getElementById('aiIntegClose');
const aiDiffModal = document.getElementById('aiDiffModal');
const aiDiffBtn = document.getElementById('aiDiffBtn');
const aiDiffClose = document.getElementById('aiDiffClose');
const aiLayerModal = document.getElementById('aiLayerModal');
const aiLayerBtn = document.getElementById('aiLayerBtn');
const aiLayerClose = document.getElementById('aiLayerClose');
const promptModal = document.getElementById('promptModal');
const promptBtn = document.getElementById('promptBtn');
const promptClose = document.getElementById('promptClose');

if (aiIntegBtn && aiIntegModal) {
  aiIntegBtn.addEventListener('click', () => openModal(aiIntegModal));
  aiIntegClose.addEventListener('click', () => closeModal(aiIntegModal));
  aiIntegModal.addEventListener('click', (e) => { if (e.target === aiIntegModal) closeModal(aiIntegModal); });
}
if (aiDiffBtn && aiDiffModal) {
  aiDiffBtn.addEventListener('click', () => openModal(aiDiffModal));
  aiDiffClose.addEventListener('click', () => closeModal(aiDiffModal));
  aiDiffModal.addEventListener('click', (e) => { if (e.target === aiDiffModal) closeModal(aiDiffModal); });
}
if (aiLayerBtn && aiLayerModal) {
  aiLayerBtn.addEventListener('click', () => openModal(aiLayerModal));
  aiLayerClose.addEventListener('click', () => closeModal(aiLayerModal));
  aiLayerModal.addEventListener('click', (e) => { if (e.target === aiLayerModal) closeModal(aiLayerModal); });
}
if (promptBtn && promptModal) {
  promptBtn.addEventListener('click', () => openModal(promptModal));
  promptClose.addEventListener('click', () => closeModal(promptModal));
  promptModal.addEventListener('click', (e) => { if (e.target === promptModal) closeModal(promptModal); });
}

// ---- theme toggle ----
const themeToggleBtn = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
function setThemeIcon(theme) {
  if (!themeIcon) return;
  themeIcon.innerHTML = theme === 'dark' ? '&#127769;' : '&#9728;&#65039;';
}
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('sita-tree-theme', theme); } catch (e) {}
  setThemeIcon(theme);
}
if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });
}
setThemeIcon(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');

