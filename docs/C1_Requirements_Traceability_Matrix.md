# SITA Consolidated Security Reporting Platform
# Deliverable C1: Requirements Traceability Matrix (RTM) (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Technical Lead:** SITA Platform Engineering  
**Coordinating Lead:** Peter (Business Analyst & Governance Lead)  
**Source Specifications:** `TEST_PLAN.md §9.9` (Traceability Matrix) & SITA Platform Flight Plan  
**Target Milestone:** Whole-of-Government Rollout & DHA Demonstration

---

## 1. Traceability Architecture

The **Requirements Traceability Matrix (RTM)** bridges high-level government requirements, architectural components, backend implementation modules, and empirical test coverage across the platform. Every functional requirement is mapped to its exact code artifacts, API contracts, and automated/manual test cases.

---

## 2. Requirements Traceability Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                REQUIREMENTS TRACEABILITY MATRIX (RTM)                                           │
├────┬─────────────────────────────┬──────────────────────────┬─────────────────────────────┬─────────────────────┤
│ REQ│ Functional Requirement      │ Architecture / Component │ Implementation Code         │ Test Coverage IDs   │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-01│ Demo Accounts Discovery     │ Auth Gateway / Login     │ `app/api/routers/auth.py`   │ API-01, FE-02,      │
│    │ for landing page modal      │ `GET /auth/demo-accounts`│ `frontend/src/LoginPage.tsx`│ TC-POST9-24         │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-02│ Public Estate Macro Summary │ Public Landing Dashboard │ `app/api/routers/`          │ API-02, POST9-01,   │
│    │ (zero PII exposure)         │ `GET /public/summary`    │ `public_summary.py`         │ test_public_summary │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-03│ Tenancy-Aware Demo Auth     │ JWT Auth Dispatcher      │ `app/api/routers/auth.py`   │ API-04, API-05,     │
│    │ with scoped entitlements    │ `POST /auth/demo-login`  │ `frontend/demoInterceptor`  │ FE-03 to FE-09      │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-04│ Scope Override Enforcement  │ Tenancy Guard Middleware │ `app/api/auth.py`           │ API-06, API-08,     │
│    │ via `scope_covers` algorithm│ Token Scope Validator    │ (`scope_covers`)            │ FE-08, TC-RBAC-01   │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-05│ National Tenancy Hierarchy  │ Geographic Hierarchy     │ `app/tenant.py`             │ API-03, FE-12,      │
│    │ (9 provs, 173 depts, 347 br)│ `GET /auth/tenancy`      │ `app/api/routers/auth.py`   │ POST9-13            │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-06│ Dynamic Tenant Switch       │ In-Memory Token Refresh  │ `app/api/routers/auth.py`   │ TS-01, TS-02, TS-03,│
│    │ without credential re-entry │ `POST /switch-tenant`    │ `frontend/src/TenancyBadge` │ TC-RBAC-07          │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-07│ 4-Tier Provisioning Matrix  │ User Administration API  │ `app/api/routers/admin.py`  │ test_admin_logins,  │
│    │ & anti-elevation ceiling    │ `GET /admin/users`       │ `app/api/auth.py`           │ POST9-19, POST9-20  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-08│ HR-Only Identity Binding    │ DPSA HR Sync Service     │ `app/tenant.py`             │ `test_tenancy.py::` │
│    │ and branch assignment       │ SQL Seeding Pipeline     │ `seed-hr-system-branches`   │ `TestResolveScope`  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-09│ AppScan SAST/DAST Ingestion │ Telemetry Normalizer     │ `app/lake/normalizer.py`    │ TC-OEM-01, POST9-02,│
│    │ and CWE de-duplication      │ Lake Ingestion Pipeline  │ `scripts/verify_ingestion`  │ test_normaliser.py  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-10│ Imperva WAF Edge Telemetry  │ Edge Telemetry Consumer  │ `app/connectors/waf.py`     │ TC-OEM-04, POST9-05,│
│    │ and DDoS / SQLi blocks      │ `/metrics/waf-summary`   │ `app/api/routers/metrics.py`│ test_normaliser.py  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-11│ Thales DAM Query Audit      │ Database Security Engine │ `app/connectors/dam.py`     │ TC-OEM-03, POST9-15,│
│    │ & Cassandra monitoring      │ `/metrics/dbsec`         │ `app/api/routers/metrics.py`│ test_normaliser.py  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-12│ Deterministic Risk Scoring  │ Risk Computation Worker  │ `app/processing/`           │ TC-RSK-01, TC-RSK-02│
│    │ & 14/30-day trend continuity│ `GET /risks`             │ `risk_engine.py`            │ test_risk_engine.py │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-13│ Alert Engine & SLA Escalation│ Alert Dispatch Service   │ `app/dispatch/`             │ TC-ALT-01, TC-ALT-02│
│    │ (< 60s for Critical breach) │ Teams/Email Webhooks     │ `alert_engine.py`           │ test_alert_engine.py│
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-14│ Auditor-General Export Pack │ AG Compliance Exporter   │ `app/api/routers/`          │ TC-AG-01, POST9-17, │
│    │ with SHA-256 hash chaining  │ `POST /exports/ag`       │ `exports_ag.py`             │ test_exports_ag.py  │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-15│ Blinded Provincial Benchmark│ Benchmark Anonymizer     │ `app/api/routers/`          │ TC-RBAC-05,         │
│    │ for cooperative governance  │ `GET /benchmark/province`│ `benchmark.py`              │ test_benchmark.py   │
├────┼─────────────────────────────┼──────────────────────────┼─────────────────────────────┼─────────────────────┤
│R-16│ Fluid Viewport & WCAG AA    │ High-Contrast UI System  │ `frontend/src/index.css`    │ TC-UI-01, TC-UI-02, │
│    │ accessibility compliance    │ Responsive Layout Clamp  │ `frontend/src/global.css`   │ POST9-28            │
└────┴─────────────────────────────┴──────────────────────────┴─────────────────────────────┴─────────────────────┘
```

---

## 3. Bidirectional Traceability Sign-Off

This matrix confirms 100% test coverage across all specified flight plan and architecture capabilities, with zero orphan requirements or untested features.
