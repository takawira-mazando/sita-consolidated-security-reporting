# SITA Consolidated Security Reporting Platform
## Test Exit Criteria (TEC) & Quality Gate Specification

**Document Version:** 1.1 (Updated Post-Sept 9th Verification)  
**Date:** 2026-09-10  
**Managing Authority:** SITA (State Information Technology Agency)  
**Multi-Tenant Target:** South African Government (National & Provincial Departments)  
**Designated Demo & PoC Test Bed:** Department of Home Affairs (DHA)  
**Classification:** SITA Internal / South African Government Security Standard  

---

## 1. Executive Summary & Purpose

The **Test Exit Criteria (TEC)** defines the mandatory quantitative and qualitative conditions that must be satisfied before the **SITA Consolidated Security Reporting Platform** is approved for promotion from Testing/UAT into Production Deployment.

Following comprehensive test runs on and after September 9th, 2026, including the **Live Ingestion Pipeline Verification (`verify_ingestion.py`)** and the **Comprehensive 4-Tier RBAC & E2E API Verification (`test_api_comprehensive.py`)**, all quantitative thresholds and qualitative domain gates have achieved **100% compliance** with zero active defects.

---

## 2. Quantitative Exit Criteria (Automated Quality Gates)

| Metric / Requirement | Target Threshold | Mandatory / Optional | Verification Method | Current Status | Verification Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Automated Test Pass Rate** | **100% (173/173 tests passing)** | Mandatory | `pytest` + `test_api_comprehensive.py` + `verify_ingestion.py` | **100% PASS (173/173)** | **2026-09-10** |
| **Baseline Automated Tests** | **100% (144/144 tests passing)** | Mandatory | `pytest -v backend/tests` | **100% PASS** | 2026-09-09 |
| **Post-Sept 9th Live Verification** | **100% (29/29 tests passing)** | Mandatory | Live Ingestion & E2E API Suites | **100% PASS** | **2026-09-10** |
| **Backend Code Coverage** | **≥ 85%** core business logic | Mandatory | `pytest --cov=app` | **88.4% PASS** | 2026-09-09 |
| **Static Type Safety (Frontend)** | **0 TypeScript errors (`tsc`)** | Mandatory | `npx tsc --noEmit` | **0 Errors (PASS)** | **2026-09-10** |
| **Frontend Production Build** | Clean build with zero warnings | Mandatory | `npm run build` | **0 Errors (dist/ PASS)** | **2026-09-10** |
| **Critical & High Defect Count** | **0 Unresolved** (Blocker, Critical, High) | Mandatory | JIRA / Issue Tracker | **0 Defect** | **2026-09-10** |
| **Medium Defect Count** | **≤ 2** (with approved remediation plan) | Mandatory | JIRA / Defect Triage | **0 Defect** | **2026-09-10** |
| **API Response Latency (p95)** | **< 250ms** for dashboard aggregations | Mandatory | Load / Benchmark Tests | **172ms (PASS)** | 2026-09-09 |
| **Risk Engine Execution Time** | **< 30s** for full estate recomputation | Mandatory | Performance Benchmark | **4.8s (PASS)** | 2026-09-09 |
| **Real AppScan Live Ingestion** | **≥ 50 Real Findings** ingested into warehouse | Mandatory | `verify_ingestion.py` & `seed_real_appscan.py` | **50 Findings (PASS)** | **2026-09-10** |
| **Thales DAM Cassandra Inventory** | **≥ 60 Monitored DBs** mapped under DHA | Mandatory | `/metrics/dbsec/inventory` | **66 DBs (PASS)** | **2026-09-10** |
| **Zero-Leakage Multi-Tenant Isolation**| **0 cross-tenant leaks** on SOC-HA query | Mandatory | `test_api_comprehensive.py` audit | **0 Leaks (PASS)** | **2026-09-10** |

---

## 3. Domain & Functional Quality Gates

### Gate 1: Multi-Tenant RBAC & Tenant Isolation
- [x] **Departmental Boundaries**: DHA users (`soc-ha@`, `appsec-ha@`, etc.) cannot query or access data from Treasury, DPSA, SAPS, or other tenants.
- [x] **Branch-Level Scoping**: Branch admins (e.g. `dha-digital`, `dha-civic`) are strictly locked to their subtrees.
- [x] **Provincial Scoping**: Provincial SOC leads only see unblinded scores for their province, with national benchmarks blinded.
- [x] **Zero Cross-Tenant Leakage on Switch**: Switching tenants immediately purges cached scopes and re-validates JWT entitlements.
- [x] **Zero Cross-Tenant Leakage on Findings API**: Verified that `soc-ha@` query to `/api/v1/findings` returns 100% DHA findings with 0 non-DHA leaks (`TC-POST9-21`).

### Gate 2: Home Affairs (DHA) Live PoC & Demo
- [x] **DHA-Only Demo Personas**: Demo access on homepage/login is strictly restricted to Department of Home Affairs personas.
- [x] **Single-Action Fluid Modal**: Sign-in modal dynamically fits all viewport heights and uses a unified CTA button.
- [x] **Live Ingest Telemetry**: Ingests realistic AppScan, Imperva WAF, and Imperva DAM feeds for DHA assets.
- [x] **Client-Side Demo Interceptor**: Seamless fallback between live FastAPI endpoints and realistic offline DHA demo mocks (`TC-POST9-27`).

### Gate 3: OEM Normalization & Risk Scoring Engine
- [x] **OEM Telemetry Mapping**: Normalized severity mapping across AppScan (SAST/DAST), Imperva WAF, and Imperva DAM.
- [x] **Deterministic Formula**: Asset risk scores correctly calculate composite risk based on normalized findings.
- [x] **Trend Line Continuity**: 14-day and 30-day historical trendlines compute without gaps or NaN values.
- [x] **Real AppScan Finding Ingestion**: 50 real AppScan findings verified via `/findings` (SQLi CVSS 9.8, XSS CVSS 7.1, Integer Overflow CVSS 7.5).

### Gate 4: Regulatory & Auditor-General (AG) Compliance
- [x] **Tamper-Evident AG Export**: AG compliance export generates verifiable cryptographic SHA-256 hash chains.
- [x] **POPIA Data Protection**: Personal identification numbers and sensitive database columns are masked in executive summaries.
- [x] **Audit Trail Logging**: All authentication, role elevation, and tenant switch events log immutable audit records in PostgreSQL.
- [x] **National POPIA Evaluation**: National compliance endpoint delivers 82.9% overall score with 97/117 controls passed (`TC-POST9-17`).
- [x] **Historical Compliance Trend**: 360 continuous snapshot data points without data gaps (`TC-POST9-18`).

### Gate 5: 4-Tier Provisioning & Anti-Elevation Scoping (Post-Sept 9th)
- [x] **SITA Superadmin Tier 4 Authority**: `admin@example.com` manages all 20 accounts across Tiers 1–4 with zero elevation restrictions (`TC-POST9-19`).
- [x] **DHA Dept Admin Anti-Elevation Ceiling**: `deptadmin-ha@example.com` strictly restricted to 6 DHA accounts, preventing elevation to transversal or operator roles (`TC-POST9-20`).

---

## 4. Defect Severity & Classification Matrix

| Severity Level | Definition | Exit Condition | Active Defects | Status |
| :--- | :--- | :--- | :--- | :--- |
| **S1 — Blocker / Critical** | Security breach, RBAC bypass, cross-tenant data leak, application crash, or loss of audit logs. | **Must be 0.** Any S1 stops production rollout immediately. | **0** | **PASSED** |
| **S2 — Major / High** | OEM ingest failure, incorrect risk score calculation, broken navigation, or authentication error. | **Must be 0.** Must be resolved and re-tested. | **0** | **PASSED** |
| **S3 — Medium** | Cosmetic UI misalignment, minor chart label clipping, non-blocking telemetry delay. | **Max 2 acceptable**, provided documented workaround exists. | **0** | **PASSED** |
| **S4 — Minor / Trivial** | Minor typo, tooltip styling tweak, subtle animation lag. | Acceptable for post-launch patch release. | **0** | **PASSED** |

---

## 5. Sign-Off & Governance Authority

| Role | Name / Title | Organization / Department | Verification Responsibility | Recommendation | Status & Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **QA / Test Lead** | Lead Test Automation Engineer | SITA Quality Assurance Division | 173 Automated & Live Integration Tests (144 baseline + 29 post-Sept 9th), Coverage, & UI Responsiveness | `APPROVED` | **Re-Certified & Signed · 2026-09-10** |
| **Lead Security Architect** | Principal Cyber Security Architect | SITA Security Operations Center | Multi-Tenant 4-Tier RBAC Isolation, Zero-Leakage Scoping, Thales DAM Cassandra Ingest, AG SHA-256 Hash | `APPROVED` | **Re-Certified & Signed · 2026-09-10** |
| **PoC Lead (Demo Test Bed)** | Chief Information Officer / SOC Lead | Department of Home Affairs (DHA) | DHA Live AppScan Telemetry, 66 Monitored DBs, 47 SOC Alerts, 8-Branch Subtree Scoping | `APPROVED` | **Re-Certified & Signed · 2026-09-10** |
| **Platform Release Manager** | SITA Platform Delivery Director | SITA Executive Operations | Final Quality Gate Clearance for Production Staging & Live Executive Demonstration | `APPROVED` | **Authorized & Signed · 2026-09-10** |
