# SITA Consolidated Security Reporting — Project Requirements

This document defines the functional and non-functional requirements for the SITA Consolidated Security Reporting platform. It is derived from the implemented system and serves as the reference specification for development, testing, and acceptance.

## 1. Purpose and scope

The platform is a full-stack security intelligence solution that unifies application security, database security, SOC operations, compliance, and executive reporting into a single experience. It provides:

- Multi-domain alert and finding ingestion and correlation
- Risk scoring, compliance assessment, and executive-level summaries
- Role-based dashboards for executive, SOC, appsec, DBsec, and compliance stakeholders
- Automated dispatch and notification to downstream systems
- Multi-tenant scoping by province, department, and branch
- Provincial peer benchmarking and Auditor-General (AG) compliance export

## 2. Functional requirements

### 2.1 Authentication and identity (FR-AUTH)

- FR-AUTH-01: The platform MUST support JWT-based authentication with configurable token TTL (default 12 hours).
- FR-AUTH-02: A bootstrap superadmin account MUST be created on first startup and its default password MUST be overridable via environment configuration.
- FR-AUTH-03: Demo role accounts MUST be seedable for local exploration (exec, soc, appsec, dbsec, compliance, transversal, province soc, admin).
- FR-AUTH-04: Demo users MUST be disabled by default in non-development environments.
- FR-AUTH-05: The system MUST support Auth0 integration (domain, audience, RS256 algorithms) when configured.
- FR-AUTH-06: Login MUST support a tenancy-scope override (province, department, or branch) so users can sign in under a specific scope.

### 2.2 Role-based access (FR-RBAC)

- FR-RBAC-01: The system MUST expose role-aware navigation and dashboards for executive, SOC, appsec, DBsec, compliance, transversal, and provincial SOC personas.
- FR-RBAC-02: A transversal superadmin role MUST span all-department reports and multiple departments.
- FR-RBAC-03: A provincial SOC lead role MUST be scoped to a province's departments (e.g., Gauteng).
- FR-RBAC-04: Tenancy scoping MUST filter data access to the selected province, department, or branch; province scope expands to every department in the province.

### 2.3 Data ingestion and processing (FR-INGEST)

- FR-INGEST-01: The system MUST ingest alerts and findings from multiple security domains.
- FR-INGEST-02: Ingestion MUST support rate limiting (token bucket), scheduling, retries, a dead-letter queue, and a circuit breaker.
- FR-INGEST-03: Incoming data MUST be normalised into a common structure for downstream analysis.
- FR-INGEST-04: Ingested findings MUST feed the processing pipeline (risk engine, compliance, alert engine, alert enrichment, alert dedup).

### 2.4 Risk and compliance (FR-RISK)

- FR-RISK-01: The system MUST compute risk scores per finding and aggregate them (risk aggregation).
- FR-RISK-02: Compliance posture MUST be assessed against configured compliance rules.
- FR-RISK-03: Alert generation MUST support deduplication and enrichment.
- FR-RISK-04: Risk and aggregate calculations MUST run on scheduled intervals (configurable, defaults: aggregate rules 60s, risk 300s).

### 2.5 Dashboards and reporting (FR-DASH)

- FR-DASH-01: The platform MUST provide role-specific dashboards (executive, SOC, appsec, DBsec, compliance).
- FR-DASH-02: The system MUST expose a public summary endpoint and metrics for monitoring.
- FR-DASH-03: Dashboards MUST present findings, risks, alerts, and compliance posture through a modern web interface.

### 2.6 Dispatch and notifications (FR-DISPATCH)

- FR-DISPATCH-01: Alerts MUST be dispatchable to downstream channels via adapters: email (SMTP), Microsoft Teams (webhook), and PagerDuty (routing key).
- FR-DISPATCH-02: Dispatch MUST support configurable worker and consumer counts.
- FR-DISPATCH-03: Dispatch failures MUST NOT silently drop alerts (retry / dead-letter handling).

### 2.7 Exports and benchmarking (FR-EXPORT)

- FR-EXPORT-01: The platform MUST provide a provincial peer benchmark endpoint (`/api/v1/benchmark/province`) that anonymises peer provinces and exposes only aggregated fused risk for peers.
- FR-EXPORT-02: Peers MUST never expose raw vulnerability counts, findings, or logs.
- FR-EXPORT-03: An Auditor-General aggregation-only compliance attestation export MUST be provided (`/api/v1/exports/ag-compliance`).
- FR-EXPORT-04: AG exports MUST strip raw findings and PII, bind a SHA-256 integrity hash to the actor and tenant scope in the audit trail, and support hash verification (`/api/v1/exports/ag-compliance/verify/{hash}`).

### 2.8 Connectors (FR-CONN)

- FR-CONN-01: The system MUST support pluggable connectors to third-party security tooling (e.g., Imperva, AppScan, APIsec, compliance).
- FR-CONN-02: Connector status MUST be tracked (connector status model).

### 2.9 Administration (FR-ADMIN)

- FR-ADMIN-01: Admin routes MUST be available under the `/admin` base path.
- FR-ADMIN-02: All sensitive operations MUST be written to an audit trail (audit action log).

## 3. Non-functional requirements

### 3.1 Architecture (NFR-ARCH)

- NFR-ARCH-01: The system MUST use a service-oriented architecture with a FastAPI backend, React/Vite frontend, PostgreSQL, and Redis.
- NFR-ARCH-02: The backend MUST expose API routes under `/api/v1`, admin routes under `/admin`, and health at `/health`.
- NFR-ARCH-03: Database schema evolution MUST be managed with Alembic migrations.
- NFR-ARCH-04: Deployment MUST be supported via Docker Compose (local, remote, and production configurations).

### 3.2 Performance and scalability (NFR-PERF)

- NFR-PERF-01: The API MUST be asynchronous (asyncpg + SQLAlchemy asyncio) to support concurrent load.
- NFR-PERF-02: Database connection pooling MUST be configurable (defaults: pool size 20, max overflow 40, pool timeout 30s).
- NFR-PERF-03: Processing MUST support configurable batch sizes (default 100) and consumer counts (default 4).

### 3.3 Security (NFR-SEC)

- NFR-SEC-01: The default development JWT secret and bootstrap password MUST be rejected in non-dev environments.
- NFR-SEC-02: Demo user seeding MUST be disabled in non-dev environments.
- NFR-SEC-03: CORS MUST be configured for the frontend origin.
- NFR-SEC-04: Secrets MUST be supplied via environment configuration (`.env`) and never committed.

### 3.4 Observability (NFR-OBS)

- NFR-OBS-01: The system MUST expose Prometheus metrics and integrate with Grafana dashboards.
- NFR-OBS-02: Structured logging MUST be used (structlog).
- NFR-OBS-03: The `/health` endpoint MUST report service status, database status, and uptime.

### 3.5 Reliability (NFR-REL)

- NFR-REL-01: Ingestion MUST tolerate transient failures via retry and dead-letter queues.
- NFR-REL-02: Dispatch adapters MUST be isolated so a single channel failure does not block others.

## 4. Technology stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), Pydantic v2, Alembic |
| Frontend | React 18, TypeScript, Vite, React Router, Recharts |
| Database | PostgreSQL |
| Cache / messaging | Redis |
| Monitoring | Prometheus, Grafana |
| Packaging | Docker Compose, Nginx |
| Auth | JWT (native) with optional Auth0 integration |

## 5. Acceptance criteria

- All demo role accounts can log in and see role-appropriate dashboards.
- Provincial SOC lead sees only their province's departments; transversal superadmin sees all departments.
- Ingested findings produce normalised records, risk scores, and alerts with deduplication.
- Alerts dispatch correctly to configured email/Teams/PagerDuty targets.
- Provincial benchmark anonymises peers and AG export strips PII with a verifiable integrity hash.
- `/health` returns healthy with database connectivity.
- Backend unit tests pass (`pytest`), frontend passes lint and typecheck (`npm run lint`, `npm run typecheck`).