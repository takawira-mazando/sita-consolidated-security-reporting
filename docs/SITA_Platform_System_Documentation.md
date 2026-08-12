# SITA Consolidated Security Reporting — System Documentation

Full technical documentation for the SITA platform: architecture, multi-tenancy, security, data pipeline, API reference, frontend, infrastructure, deployment and operations.

---

## Table of contents

1. [System overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Multi-tenancy model](#3-multi-tenancy-model)
4. [Authentication & authorization](#4-authentication--authorization)
5. [Data pipeline](#5-data-pipeline)
6. [Database schema](#6-database-schema)
7. [REST API reference](#7-rest-api-reference)
8. [Frontend application](#8-frontend-application)
9. [Infrastructure & deployment](#9-infrastructure--deployment)
10. [Monitoring & observability](#10-monitoring--observability)
11. [CI/CD](#11-cicd)
12. [Security model](#12-security-model)
13. [Operations runbook](#13-operations-runbook)
14. [Testing](#14-testing)
15. [Demo accounts & getting started](#15-demo-accounts--getting-started)
16. [Configuration reference](#16-configuration-reference)

---

## 1. System overview

SITA Consolidated Security Reporting is a full-stack security intelligence platform that unifies application security, database security, SOC operations, compliance and executive reporting into a single experience. It is built to run as a **multi-tenant government platform** on SITA's real mandate: **43 national departments and 113 provincial departments across South Africa's 9 provinces (156 public clients)**.

The platform:

- Ingests findings from four OEM security sources (HCL AppScan, Imperva DAM/WAF, an API Security platform, and compliance CSV feeds)
- Normalises and correlates the data into a PostgreSQL warehouse
- Runs alert, risk and compliance engines over the warehouse
- Dispatches alerts out-of-band (email, Microsoft Teams, PagerDuty)
- Serves role-gated, tenant-scoped dashboards through a FastAPI REST API and a React SPA
- Isolates every tenant's data and delegates administration along the tenancy tree
- Supports tenant-safe provincial benchmarking and Auditor-General attestation exports

### Key capabilities

- **Multi-role dashboards** for executive, SOC, AppSec, DBsec, Compliance, SRE and provincial personas
- **Government multi-tenancy** — Province → Department → Branch → App, with `tenant_filter` scoping on every query
- **Delegated administration** — four admin tiers whose authority is exactly their node's subtree
- **Tenant-safe analytics** — anonymised provincial peer benchmarks, raw data never exposed
- **AG export attestation** — aggregation-only exports with SHA-256 integrity hash bound to actor + tenant scope
- **OEM ingestion** — async connectors with circuit breaker, token bucket, retry and dead-letter queue
- **Alert dispatch** — email (Jinja2), Teams Adaptive Cards, PagerDuty Events v2, per-channel rate limiting
- **Compliance** — POPIA (8 conditions) and ISO 27001 (A.5–A.16) weighted scoring
- **Risk engine** — 4-signal multiplicative fusion to a 0–100 score with safe/monitored/critical buckets

### Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router, Recharts, Axios, Auth0 SDK |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic v2, pandas |
| Data | PostgreSQL 16 (asyncpg), Redis 7 |
| Auth | JWT (HS256 dev / RS256 Auth0), python-jose |
| Dispatch | SMTP, Teams webhook, PagerDuty Events v2 |
| Monitoring | Prometheus, Grafana, structlog |
| Infra | Docker Compose, nginx, GHCR, GitHub Actions |

---

## 2. Architecture

### 2.1 Layer overview

```text
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND (React SPA)  ── role-gated pages, consume /api/v1 │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS (nginx)
┌──────────────────────────────▼──────────────────────────────┐
│  BACKEND (FastAPI) — routers, RBAC, tenant_filter scoping   │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────┐     ┌───────────────┐    ┌─────────────┐
│ Redis    │     │ PostgreSQL    │    │ SMTP/Teams  │
│ (bus,    │     │ warehouse +   │    │ /PagerDuty  │
│ dedup)   │     │ audit + ids   │    │ (dispatch)  │
└──────────┘     └───────────────┘    └─────────────┘
```

### 2.2 Runtime services (Docker Compose)

| Service | Command | Role |
|---|---|---|
| `postgres` | postgres:16-alpine | Primary data store (staging / warehouse / archive / audit / identity schemas) |
| `redis` | redis:7-alpine | Message bus, alert dedup, rate limiting |
| `backend` | `uvicorn app.main:app` | REST API (port 8000) |
| `ingestion` | `python -m app.entrypoints.ingestion` | Polls OEM connectors, writes staging |
| `processing` | `python -m app.entrypoints.processing` | Consumes raw records → normaliser → warehouse + engines |
| `dispatch` | `python -m app.entrypoints.dispatch` | Alert out-of-band dispatch worker |
| `analytics` | `python -m app.entrypoints.analytics` | Periodic aggregate/risk scoring |
| `frontend` | nginx serving built SPA | UI (port 3000) |

### 2.3 Repository structure

```text
backend/
  app/
    api/            # FastAPI app, routers, auth, schemas, errors
    bus/            # Redis bus abstractions
    connectors/     # OEM connectors (appscan, imperva, apisec, compliance, base)
    dispatch/       # email / teams / pagerduty adapters + worker
    entrypoints/    # ingestion, processing, analytics, dispatch, seed_simulated
    ingestion/      # scheduler, circuit_breaker, token_bucket, retry, dlq
    lake/           # warehouse writer
    models/         # SQLAlchemy ORM models
    monitoring/     # metrics (Prometheus), logging (structlog)
    processing/     # normaliser, alert engine, risk engine, compliance, enricher
    synthetic/      # deterministic synthetic OEM feed generator
    tenant.py       # tenancy catalogs, provinces, roles, admin tiers
  tests/
  requirements.txt
frontend/
  src/
    api/            # typed API clients
    components/     # layout + dashboard widget kit
    context/        # AuthContext
    hooks/          # per-dashboard data hooks
    pages/          # dashboard + auth pages
    types.ts
  package.json
infrastructure/
  docker-compose.yml
  monitoring/       # prometheus.yml, grafana dashboard
  nginx/sita.conf
  scripts/          # init-db.sql, seed-demo.sql, maintenance.sql, backup.sh, deploy.sh
docs/               # this documentation set
.github/workflows/  # ci.yml, publish-ghcr.yml
```

### 2.4 End-to-end data flow

```text
OEM sources (AppScan / Imperva / API-Security / Compliance)
        │  (live connectors, or SyntheticOEMFeed until live access)
        ▼
staging.raw_records  ── normaliser (field_mapper.yaml) ──▶ warehouse.findings
        │                                                    │
        ▼                                                    ▼
   alert_engine ──▶ warehouse.alerts ──▶ dispatch ──▶ email/Teams/PagerDuty
   risk_engine  ──▶ warehouse.risk_scores
   compliance   ──▶ warehouse.compliance_snapshots / compliance_gaps
        │
        ▼
   REST API (/api/v1) ──▶ React dashboards (tenant-scoped)
```

---

## 3. Multi-tenancy model

Tenancy is the core security property of the platform: **a tenant is a government department**, and every user only ever sees data inside their assigned scope.

> The complete stakeholder explainer lives in `docs/Tenancy_Stakeholder_Overview.docx`.

### 3.1 Tenant tree

```text
Province → Department → Branch → App / Database
```

- **System identity (Tenant)** — national department or provincial administration
- **Sub-tenant (Department)** — e.g. Department of Home Affairs, Gauteng Department of Health
- **Asset (Application / Database)** — the app/database records belonging to a department
- **Branch** — national departments only; DDG-led organisational units (e.g. DHA Information Services/CIO)

Provincial departments are **branchless**; province scope expands automatically to the province's full department set.

### 3.2 Tenancy catalogs (`backend/app/tenant.py`)

| Catalog | Contents |
|---|---|
| `PROVINCES` | 9 provinces (ec, fs, gp, kzn, lp, mp, nw, nc, wc) |
| `PROVINCIAL_DEPARTMENTS` | 113 departments, slugs `<province>-<function>` |
| `DEPARTMENTS` | national + provincial departments (~156 total) |
| `BRANCHES` | per-department DDG-led units (national only) |
| `APP_DEPARTMENTS` / `DB_TO_DEPARTMENT` | app/database → department ownership |
| `MINISTRIES` / `CLUSTERS` | reporting rollups (32 ministries → 5 clusters) |
| `ADMIN_TIERS` / `GRANTABLE_ROLES` | delegation model |

Identifiers are **stable slugs**, so resolution requires no DB lookup.

### 3.3 Scoping rules

- **Nationwide roles** (exec, compliance, sre, admin, transversal-admin) see the whole estate (empty scope = whole estate)
- **Department roles** (soc, appsec, dbsec) scoped to `department_ids`/`branch_ids` on the JWT
- **Province roles** (province-soc-lead, province-dept-admin, local-appsec) scoped by `province_ids`; expands to the province's departments
- Every warehouse row denormalises `department_id`/`branch_id` at write time, so scoping needs **no joins**
- **Fail-closed**: a department-scoped user with no assigned scope sees nothing until an admin assigns one

### 3.4 Enforcement

`tenant_filter(claims, model)` in `backend/app/api/auth.py` adds the WHERE clause to every read. Scoped parameters can only narrow a scope, never widen it. Enforced on **every** data endpoint: risks, findings, alerts, dashboard, exports, metrics, benchmark, AG exports, admin.

### 3.5 Delegated administration

| Tier | Role | Authority |
|---|---|---|
| 4 | system `admin` | Estate root — national superadmin, grants anything |
| 3 | `transversal-admin` | Transversal superadmin — grants operational roles + dept/branch-admin across scope |
| 2 | `dept-admin` / `province-dept-admin` | Department or province node — operational roles (+ branch-admin nationally) |
| 1 | `branch-admin` | Branch node — operational roles only |

Delegation is **strictly one-way down**: `can_manage` blocks granting a tier at or above the caller's own; `_tenant_consistent` rejects branches not under the caller's departments.

---

## 4. Authentication & authorization

### 4.1 Token flow

- `POST /api/v1/auth/login` or `/api/v1/auth/demo-login` → JWT (HS256 with `jwt_secret` in dev; RS256 via Auth0 when `auth0_domain` is configured)
- `verify_token` (dependency) decodes and validates the JWT, returns `JWTClaims`
- `require_roles(*perms)` checks the role permission matrix

### 4.2 Role permission matrix (`backend/app/api/auth.py`)

| Role | Permissions |
|---|---|
| `admin` | `*` (everything) |
| `exec` | risks, compliance, alerts, alerts_read, alerts_write, findings, dashboard |
| `soc` | findings, alerts_read, alerts_write, dashboard |
| `appsec` | risks, findings |
| `dbsec` | risks, findings, alerts_read |
| `compliance` | compliance |
| `sre` | admin_read, admin_write, alerts_read, dashboard |
| `transversal-admin` | admin_read, admin_write |
| `dept-admin` | admin_read, admin_write |
| `branch-admin` | admin_read, admin_write |
| `province-soc-lead` | findings, alerts_read, alerts_write, dashboard |
| `province-dept-admin` | admin_read, admin_write |
| `local-appsec` | risks, findings |

### 4.3 JWT claims

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "roles": ["province-soc-lead"],
  "department_ids": [],
  "branch_ids": [],
  "province_ids": ["gp"],
  "exp": 1750000000
}
```

### 4.4 Start-of-day identity bootstrap

On startup (`app/main.py` lifespan):

1. `bootstrap_superadmin` — creates `admin@example.com` if absent
2. `seed_demo_users` — seeds the demo accounts (see §15)
3. Startup failures are logged but do not block the server

---

## 5. Data pipeline

### 5.1 Connectors (`backend/app/connectors/`)

`BaseConnector` defines `authenticate() → poll() → parse() → validate()`, orchestrated by `run()`.

| Connector | Source | Notes |
|---|---|---|
| `appscan.py` | HCL AppScan | vulnerability findings |
| `imperva.py` | Imperva DAM/WAF | database activity + web attack events |
| `apisec.py` | API Security platform | API endpoint exposure inventory |
| `compliance.py` | compliance CSV feeds | control snapshots |

**Ingestion hardening** (`backend/app/ingestion/`): APScheduler-driven polling, circuit breaker state machine, token-bucket rate limiter, retry with backoff, and a dead-letter queue (`staging.rejected_records`).

### 5.2 Synthetic feed (`backend/app/synthetic/generator.py`)

Because live OEM credentials are not yet available, a **deterministic synthetic feed** (`SyntheticOEMFeed`, seed=42) emits payloads shaped exactly like each real connector's `poll()` output. Everything downstream (staging → normaliser → warehouse → engines → API → dashboards) runs and is tested before live access exists. Cutover is a source swap at the ingestion boundary — no downstream changes.

### 5.3 Normaliser (`backend/app/processing/normaliser.py` + `field_mapper.yaml`)

- JSONPath field maps + severity maps per source
- Severity normalisation, UTC timestamp coercion, field flatten/cast
- Dedup by `source` + `external_id`
- Parse/validation failures route to the DLQ

### 5.4 Alert engine (`backend/app/processing/alert_engine.py` + `alert_rules.yaml`)

Six rules:

1. `risk_critical` — fused risk crosses critical threshold
2. `new_critical_cve` — new critical CVE appears
3. `shadow_api_detected` — unapproved API endpoint found
4. `compliance_drop` — compliance score drops
5. `imperva_violation_spike` — WAF/DAM violation spike
6. `connector_auth_failure` — connector can't authenticate

Redis + MD5 throttle suppression (`alert_dedup.py`) prevents alert storms. `alert_enricher.py` adds owner/team/priority/URL from `app_catalog.yaml`.

### 5.5 Risk engine (`backend/app/processing/risk_engine.py`)

4-signal multiplicative fusion, per-app daily score [0–100]:

```text
R = (w1·Sa + w2·Si + w3·E + w4·C) / Σw
weights: 0.35 (appsec) · 0.25 (imperva) · 0.20 (exposure) · 0.20 (compliance)
```

Buckets: `safe` (<45) · `monitored` (45–69) · `critical` (≥70).

### 5.6 Compliance (`backend/app/processing/compliance.py`)

- **POPIA** — 8 conditions weighted scoring, security safeguards weight 0.30
- **ISO 27001** — Annex A themes A.5–A.16 weighted scoring

### 5.7 Dispatch (`backend/app/dispatch/`)

- `email_adapter.py` — SMTP + Jinja2 template
- `teams_adapter.py` — Adaptive Cards
- `pagerduty_adapter.py` — PagerDuty Events v2
- `worker.py` — async worker with per-channel rate limit; writes `warehouse.dispatch_log` + `alerts.last_dispatched_at`

---

## 6. Database schema

Six schemas, 24 tables (20 canonical + 4 archive `LIKE` copies).

### Schemas

| Schema | Purpose |
|---|---|
| `staging` | batch runs, raw records, rejected records (DLQ) |
| `warehouse` | canonical processed data + tenant reference tables |
| `archive` | LIKE-copy rotation tables for maintenance TTL |
| `audit` | `action_audit` — immutable AG export trail |
| `identity` | `users`, `persons` |

### Tables

**identity**
- `users` — RBAC identities, JWT scope lists (`province_ids`/`department_ids`/`branch_ids` JSONB)
- `persons` — HR person records for user↔person linking

**audit**
- `action_audit` — actor, action, target, tenant_scope (JSONB), payload_hash, created_at

**staging**
- `batch_runs`, `raw_records`, `rejected_records`

**warehouse**
- `provinces`, `departments` (incl. `province_id`), `branches`
- `findings` (tenant-scoped via department_id/branch_id)
- `risk_scores` (daily fused score per app, tenant-scoped)
- `alerts` (unified feed, dedup counters, dispatch channels)
- `dispatch_log` (out-of-band dispatch trail)
- `compliance_snapshots`, `compliance_gaps`
- `api_endpoints` (AppSec exposure inventory)
- `waf_blocks` (Imperva WAF block telemetry)
- `system_metrics`, `agents`, `slo_metrics`, `database_inventory`, `connector_health`

**archive**
- `risk_scores`, `alerts`, `compliance_snapshots`, `findings` (LIKE copies)

**Tenancy note:** every app/db-scoped warehouse row denormalises `department_id`/`branch_id`, so `tenant_filter` scoping needs no joins. Provincial departments resolve via `departments.province_id → warehouse.provinces`.

The full DDL is in `infrastructure/scripts/init-db.sql`; the interactive ER diagram is rendered in `tree.html`.

---

## 7. REST API reference

Base prefixes: `/api/v1` (core), `/admin` (admin), `/health`.

### Auth
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/login` | public | Password login |
| POST | `/api/v1/auth/demo-login` | public | Demo login with tenancy-scope override |
| GET | `/api/v1/auth/demo-accounts` | public | List demo accounts |
| GET | `/api/v1/auth/tenancy` | public | Tenancy options (provinces, etc.) |
| GET | `/api/v1/auth/me` | any | Current user + scope |

### Risks
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/risks` | risks | Paginated risk scores |
| GET | `/api/v1/risks/by-cluster` | risks | Cluster rollups |
| GET | `/api/v1/risks/by-ministry` | risks | Ministry rollups |
| GET | `/api/v1/risks/{app_name}/trend` | risks | Per-app trend |

### Findings
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/findings` | findings | Paginated findings |
| GET | `/api/v1/findings/{finding_id}` | findings | Finding detail |

### Compliance
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/compliance` | compliance | Compliance summary |
| GET | `/api/v1/compliance/gaps` | compliance | Gap list |
| GET | `/api/v1/compliance/evidence` | compliance | Evidence |

### Alerts
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/alerts` | alerts_read | Paginated alerts |
| GET | `/api/v1/alerts/{alert_id}/dispatch` | alerts_read | Dispatch history |
| PATCH | `/api/v1/alerts/{alert_id}/acknowledge` | alerts_write | Acknowledge |
| PATCH | `/api/v1/alerts/{alert_id}/resolve` | alerts_write | Resolve |

### Dashboard
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | dashboard | Cross-domain summary |

### Metrics
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/metrics/appsec/waf` | findings | WAF blocks |
| GET | `/api/v1/metrics/appsec/api-exposure` | findings | API exposure |
| GET | `/api/v1/metrics/appsec/fix-rate` | findings | Fix rate |
| GET | `/api/v1/metrics/soc/slo` | alerts_read | SOC SLO |
| GET | `/api/v1/metrics/sre/system` | dashboard | System metrics |
| GET | `/api/v1/metrics/sre/agents` | dashboard | Agent status |
| GET | `/api/v1/metrics/dbsec/inventory` | findings | DB inventory |
| GET | `/api/v1/metrics/compliance/trend` | compliance | Compliance trend |
| GET | `/api/v1/metrics/compliance/calendar` | compliance | Compliance calendar |

### Exports
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/exports/findings.csv` | findings | CSV export |
| GET | `/api/v1/exports/risk-scores.csv` | risks | CSV export |
| GET | `/api/v1/exports/alerts.csv` | alerts_read | CSV export |
| POST | `/api/v1/exports/ag-compliance` | compliance, admin_write | AG attestation export (hash-bound) |
| GET | `/api/v1/exports/ag-compliance/verify/{hash}` | compliance, admin_write | Verify attestation |

### Benchmark
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/api/v1/benchmark/province` | dashboard | Anonymised provincial peer benchmark |

### Admin
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/admin/departments` | admin_read | Department catalog |
| GET | `/admin/branches` | admin_read | Branch catalog |
| GET | `/admin/connectors` | admin_read | Connector health |
| GET | `/admin/dead-letter` | admin_read | DLQ overview |
| POST | `/admin/connectors/{name}/reset` | admin_write | Circuit reset |
| POST | `/admin/dead-letter/reprocess/{record_id}` | admin_write | Reprocess DLQ record |
| GET | `/admin/users` | admin_read | User list |
| POST | `/admin/users` | admin_write | Create user (scope-validated) |
| PATCH | `/admin/users/{user_id}` | admin_write | Update user |
| DELETE | `/admin/users/{user_id}` | admin_write | Delete user |
| GET | `/admin/persons` | admin_read | Person registry |
| POST | `/admin/hr/sync` | admin_write | HR sync |

### Health
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + uptime |

Interactive OpenAPI docs are available at `http://localhost:8000/docs` when running.

---

## 8. Frontend application

### 8.1 Pages & roles

| Page | Roles | Feeds |
|---|---|---|
| `HomePage` | any (authed) | Landing |
| `LoginPage` | public | Login + tenancy-scope override |
| `ExecDashboard` | exec | risks, compliance, alerts, findings, dashboard |
| `SocDashboard` | soc, province-soc-lead | findings, alerts, dispatch |
| `AppSecDashboard` | appsec, local-appsec | risks, findings, metrics/appsec |
| `DbSecDashboard` | dbsec | risks, findings, metrics/dbsec |
| `ComplianceDashboard` | compliance | compliance + metrics/compliance |
| `SreDashboard` | sre | admin_read, system metrics, agents |
| `AdminUsersPage` | admin tiers | user CRUD with province/department/branch scope pickers |

### 8.2 Component kit (`frontend/src/components/dashboard/`)

`StatCard`, `Panel`, `Gauge`, `MiniBarChart`, `BarRow`, `Chip`, `OemTag`, `DashHeader`, `ExplainOverlay`. `RoleNav` (layout) drives role-aware navigation.

### 8.3 Data layer

- `src/api/` — typed clients: admin, alerts, auth, client, compliance, dashboard, findings, metrics, risks
- `src/hooks/` — `useApi`, `usePolling` + per-dashboard hooks (`useExecData`, `useSocData`, …)
- `src/data/explanations.ts` — builds "Explain this dashboard" / layman's narratives from **live** API data (no hardcoded figures)

### 8.4 Routing & guards

`App.tsx` + `AuthContext` guard routes by role; unauthenticated users redirect to `/login`.

---

## 9. Infrastructure & deployment

### 9.1 Docker Compose

See §2.2 for the service matrix. Backend/ingestion/processing/dispatch/analytics share the backend image; frontend is served by nginx.

### 9.2 nginx (`infrastructure/nginx/sita.conf`)

- HTTPS-only (TLS 1.3), HSTS, CSP/X-Frame-Options/X-Content-Type-Options headers
- Rate limit on `/api/v1/auth/` (5 r/s) to blunt credential stuffing
- Proxies `/api/`, `/api/v1/auth/`, `/admin/` → backend; `/` → frontend

### 9.3 Scripts (`infrastructure/scripts/`)

| Script | Purpose |
|---|---|
| `init-db.sql` | Full schema (all 6 schemas / 24 tables), mounted as Postgres init |
| `seed-demo.sql` | Demo tenants/apps/databases + demo scope data |
| `maintenance.sql` | Archive rotation + TTL maintenance |
| `backup.sh` | pg_dump -Fc daily with retention |
| `deploy.sh` | Deployment helper |

### 9.4 Backups & DR

- Daily `pg_dump -Fc` with retention (see `backup.sh`)
- WAL/PITR recovery path documented for RTO < 15 min target
- Restore drills intended as part of the DR runbook

---

## 10. Monitoring & observability

- **Prometheus** scrapes the backend `/metrics` (prometheus-client), Postgres (9187) and Redis (9121) — see `infrastructure/monitoring/prometheus.yml`
- **Grafana** dashboard `sita-pipeline.json` visualises the pipeline
- **structlog** structured logging through `app/monitoring/logging.py`
- `/health` liveness endpoint returns uptime

---

## 11. CI/CD

### `ci.yml` (push to `main`/`develop`, PR to `main`)

| Job | Steps |
|---|---|
| `lint` | ruff check backend/ · eslint frontend |
| `test` | postgres 16 + redis 7 services · pytest backend/tests · frontend build |
| `build` | docker build backend + frontend |

### `publish-ghcr.yml`

Builds and publishes `sita-backend` / `sita-frontend` images to GitHub Container Registry on `main`.

---

## 12. Security model

- **Data isolation**: `tenant_filter` on every query — server-side, not UI-only; fail-closed defaults
- **Delegated admin**: one-way-down grant rules; scope cannot exceed caller's subtree
- **JWT auth**: HS256 dev secret (config-guarded for non-dev), RS256/Auth0 path for production; config guards reject default dev secret in non-dev environments
- **AG exports**: PII stripped, aggregation-only, SHA-256 integrity hash bound to actor + tenant scope in `audit.action_audit` (tamper-evident)
- **Blinded benchmarking**: peer provinces shown as anonymous aggregates only
- **Startup guards** (`config.py`): non-dev environments must set a strong JWT secret + bootstrap password and disable demo seeding
- **Follow-ups tracked**: Auth0/Okta RS256 + token rotation, secrets vault, OWASP scan, pen test (project item)

---

## 13. Operations runbook

### Start the stack

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

### Start backend + frontend locally

```bash
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev -- --host 0.0.0.0 --port 3000
```

### Apply tenancy migration (fresh/legacy DBs)

```bash
cd backend && python _migrate_tenancy.py
cd backend && python _migrate_province.py     # adds province_ids, provinces, action_audit
```

### Seed simulated data

```bash
cd backend && python -m app.entrypoints.seed_simulated
```

### Health check

```bash
curl http://localhost:8000/health
```

### Common ops actions

| Action | Where |
|---|---|
| Reset a connector circuit breaker | `POST /admin/connectors/{name}/reset` |
| Reprocess a DLQ record | `POST /admin/dead-letter/reprocess/{record_id}` |
| View DLQ | `GET /admin/dead-letter` |
| Backup | `infrastructure/scripts/backup.sh` |

---

## 14. Testing

| Suite | Coverage |
|---|---|
| `test_normaliser.py` | field mapping, flatten/cast, dedup, DLQ routing |
| `test_alert_engine.py` | 6 alert rules, throttling |
| `test_risk_engine.py` | fusion, buckets, aggregator |
| `test_tenancy.py` | `tenant_filter` scoping, scope validation, delegation, ministry/cluster derivation |
| `test_benchmark.py` | benchmark bucketing |
| `test_exports_ag.py` | attestation, canonical JSON, hashing |
| `test_exports.py` | CSV export endpoints |
| `test_new_endpoints.py` | benchmark + AG endpoints, province scoping, audit row |

Run:

```bash
cd backend && python -m pytest tests -v
```

CI runs the suite against postgres + redis services.

---

## 15. Demo accounts & getting started

| Email | Password | Role / scope |
|---|---|---|
| `exec@example.com` | `pass123` | exec — whole estate |
| `soc@example.com` | `pass123` | soc |
| `appsec@example.com` | `pass123` | appsec |
| `dbsec@example.com` | `pass123` | dbsec |
| `compliance@example.com` | `pass123` | compliance |
| `transversal@example.com` | `pass123` | transversal-admin — whole estate |
| `provincesoc@example.com` | `pass123` | province-soc-lead — Gauteng |
| `admin@example.com` | `admin123` | admin — superadmin |

The login page supports a **tenancy-scope override**: pick a province/department/branch to sign in under that scope (province expands to all its departments).

---

## 16. Configuration reference

Environment variables (`.env` at `backend/` — see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://sita:password@localhost:5432/sita` | Async Postgres DSN |
| `REDIS_URL` | `redis://:password@localhost:6379/0` | Redis DSN |
| `ENVIRONMENT` | `dev` | Guards non-dev defaults |
| `JWT_SECRET` | dev-only default | HS256 signing secret |
| `AUTH0_DOMAIN` / `AUTH0_AUDIENCE` | empty | Enables RS256/Auth0 |
| `SEED_DEMO_USERS_ENABLED` | `true` | Demo account seeding |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | `admin@example.com` / `admin123` | Superadmin bootstrap |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | localhost:587 | Email dispatch |
| `TEAMS_WEBHOOK_URL` | empty | Teams dispatch |
| `PAGERDUTY_ROUTING_KEY` | empty | PagerDuty dispatch |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT` | 20 / 40 / 30 | Connection pool |
| `PROCESSING_BATCH_SIZE` / `PROCESSING_CONSUMERS` | 100 / 4 | Processing tuning |
| `DISPATCH_MAX_WORKERS` / `DISPATCH_CONSUMERS` | 10 / 2 | Dispatch tuning |
| `ANALYTICS_AGGREGATE_RULES_INTERVAL` / `ANALYTICS_RISK_INTERVAL` | 60 / 300 | Analytics cadence (s) |

---

## Appendix A — Related deliverables

| Asset | Location |
|---|---|
| Stakeholder tenancy explainer (Word) | `docs/Tenancy_Stakeholder_Overview.docx` |
| Alert messaging design (Word) | `docs/SITA_Alert_Messaging.docx` |
| Database schema reference | `docs/database-schema.md` |
| Interactive architecture tree + ER diagram | `tree.html` |

---

*Generated from the repository at commit `a53f829` — multi-tenancy release.*
