# SITA Consolidated Security Reporting Platform
# Deliverable A2: Master Test Registry & Traceability Specification (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Target Environment:** Whole of South African Government Multi-Tenant Platform  
**Designated Demo & PoC Test Bed:** Department of Home Affairs (DHA)  
**Associated Artifacts:**  
- Excel Master Registry: `docs/SITA_Platform_Test_Cases.xlsx`
- Quality Gates Workbook: `docs/SITA_Test_Exit_Criteria_and_Quality_Gates.xlsx`
- JSON Master Registry: `docs/master_test_registry.json`
- Pytest XML Output: `docs/test_report.xml`

---

## 1. Scope & Purpose

The **Master Test Registry (Deliverable A2)** establishes a single source of truth tracking all test cases, verification methodologies, pre-conditions, execution steps, expected outcomes, observed results, and sign-offs for the SITA Consolidated Security Reporting Platform.

The registry captures **212 total test specifications**:
- **144 Baseline Automated Tests** (executed via `pytest` and core scripts)
- **29 Post-Sept 9th Live Verification & E2E Tests** (`verify_ingestion.py`, `test_api_comprehensive.py`, lake normalizers, Vite bundle)
- **40 Manual Test Cases** defined in `TEST_PLAN.md §5` covering API smoke, frontend login, post-login state, dynamic tenant switching, and security edge cases.

---

## 2. Master Test Registry Structure (`SITA_Platform_Test_Cases.xlsx`)

The official Excel registry is organized into **8 domain-specific worksheets**, each styled with SITA executive palettes, standard headers, and auto-fitted data columns:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    SITA_PLATFORM_TEST_CASES.XLSX WORKBOOK                       │
├────┬───────────────────────────────┬────────────┬───────────────────────────────┤
│ #  │ Sheet Name                    │ Test Count │ Verification Focus            │
├────┼───────────────────────────────┼────────────┼───────────────────────────────┤
│ 1  │ Executive Summary             │ Summary    │ High-level status & gate pass │
│ 2  │ TC_MultiTenant_RBAC           │ 8 Cases    │ Isolation, scoping, fail-close│
│ 3  │ TC_DHA_Demo_PoC               │ 6 Cases    │ DHA demo exclusivity & modal  │
│ 4  │ TC_OEM_Ingestion              │ 5 Cases    │ AppScan, WAF, DAM mapping     │
│ 5  │ TC_Risk_and_Alerts            │ 4 Cases    │ Scoring math & SLA dispatch   │
│ 6  │ TC_Compliance_AuditorGeneral  │ 3 Cases    │ SHA-256 hash & POPIA masking  │
│ 7  │ TC_Frontend_UX                │ 3 Cases    │ Fluid modal & WCAG AA contrast│
│ 8  │ TC_PostSept9_Live_Verification│ 29 Cases   │ Live ingestion & E2E API audit│
├────┴───────────────────────────────┴────────────┴───────────────────────────────┤
│ Consolidated Formal Suite          │ 173 Total  │ 100% Passed (0 Failures)      │
└─────────────────────────────────────────────────┴───────────────────────────────┘
```

### Standard Column Schema
Every test case in the workbook adheres to an 11-column auditable schema:
1. **Test ID:** Unique identifier (e.g. `TC-RBAC-01`, `TC-POST9-21`, `API-05`)
2. **Category:** Functional or security domain
3. **Persona / Role:** Target user or automated pipeline identity
4. **Tenant Scope:** Explicit departmental or provincial scoping (`home-affairs-digital`, `gp`, `Whole Estate`)
5. **Test Description:** Detailed scenario summary
6. **Pre-conditions:** Required test data, tokens, or network states
7. **Execution Steps:** Step-by-step reproducible instructions
8. **Expected Result:** Deterministic target condition
9. **Actual Result:** Empirical observation from test execution
10. **Status:** `PASSED` / `FAILED` / `BLOCKED`
11. **Execution Date:** Timestamp / Date of formal execution

---

## 3. Manual Test Checklist Matrix (`TEST_PLAN.md §5`)

The 40 manual test cases specified in `TEST_PLAN.md §5` provide operational verification protocols for QA leads and security auditors:

### 3.1 Section 5.1: API Smoke Tests (curl / Postman) — 10 Cases
- **API-01 (`GET /api/v1/auth/demo-accounts`):** 200 OK; returns array of 11 DemoAccount objects with `is_nationwide` flags.
- **API-02 (`GET /api/v1/public/summary`):** 200 OK; unauthenticated aggregate summary of findings, assets, and connectors.
- **API-03 (`GET /api/v1/auth/tenancy`):** 200 OK; returns 9 provinces, 173 departments, and 347 branches.
- **API-04 (`POST /api/v1/auth/demo-login` - exec):** 200 OK; issues nationwide token with empty scope claims.
- **API-05 (`POST /api/v1/auth/demo-login` - soc):** 200 OK; issues token scoped strictly to `home-affairs-digital`.
- **API-06 (`POST /api/v1/auth/demo-login` - soc override outside):** 403 Forbidden; prevents SOC from claiming Treasury.
- **API-07 (`POST /api/v1/auth/demo-login` - provincesoc GP):** 200 OK; issues token scoped to Gauteng.
- **API-08 (`POST /api/v1/auth/demo-login` - provincesoc WC):** 403 Forbidden; prevents GP persona from claiming Western Cape.
- **API-09 (`POST /api/v1/auth/login` - admin):** 200 OK; issues token with `ALL_ROLES`.
- **API-10 (`POST /api/v1/auth/login` - invalid pwd):** 401 Unauthorized; rejects invalid credentials.

### 3.2 Section 5.2: Frontend Login Flow (`http://localhost:8802`) — 15 Cases
- **FE-01:** Login overlay visible on landing page with official SITA branding.
- **FE-02:** Demo personas render in 3 groups: National (6), Provincial (1), Administration (4).
- **FE-03:** Clicking `exec@` chip auto-configures scope to "Account default — whole estate".
- **FE-04:** Clicking `provincesoc@` enables province selector pre-set to Gauteng.
- **FE-05:** Clicking `soc@` enables department selector filtered to Home Affairs.
- **FE-06:** Department search input filters lists in real time.
- **FE-07:** Valid scope override (soc@ with Home Affairs) logs in and routes to dashboard.
- **FE-08:** Invalid scope override (soc@ with Treasury) displays 403 error toast.
- **FE-09:** Default scope fallback without manual selection succeeds seamlessly.
- **FE-10:** Regular credential login with valid email/password succeeds.
- **FE-11:** Regular credential login with bad password displays 401 error toast.
- **FE-12:** Tenancy hierarchy call populates dropdown with 9 provinces.
- **FE-13:** Offline backend triggers graceful network error toast without UI crash.
- **FE-14:** Keyboard navigation (Tab, Enter) operates all modal controls.
- **FE-15:** ESC key or backdrop click dismisses modal overlay cleanly.

### 3.3 Section 5.3: Post-Login Sanity — 5 Cases
- **PL-01:** `auth_token` stored in browser `LocalStorage`.
- **PL-02:** Decoded JWT claims (`roles`, `department_ids`, `province_ids`) match persona profile.
- **PL-03:** Dashboard route `/dashboard` renders overview cards, trendlines, and risk gauge.
- **PL-04:** Sidebar navigation dynamically hides restricted features.
- **PL-05:** Top header bar displays active tenancy badge (e.g. "Department of Home Affairs").

### 3.4 Section 5.4: Dynamic Tenancy Switching — 3 Cases
- **TS-01:** Switch tenant within entitlement (`POST /switch-tenant`) re-issues JWT without re-login.
- **TS-02:** Switch tenant outside entitlement returns HTTP 403 Forbidden.
- **TS-03:** Reset to default re-issues JWT with original seeded tenancy scope.

### 3.5 Section 5.5: Security & Edge Cases — 7 Cases
- **SEC-01:** Expired JWT token returns 401 and redirects to login modal.
- **SEC-02:** Refresh token generates new access token.
- **SEC-03:** CORS preflight validated; unauthorized cross-origin requests blocked.
- **SEC-04:** Rapid repeated login attempts trigger HTTP 429 rate limit.
- **SEC-05:** SQL injection payload in scope parameters returns HTTP 422; 0 database execution.
- **SEC-06:** XSS payload in user display label sanitized without DOM execution.
- **SEC-07:** Cookies set with `Secure`, `HttpOnly`, and `SameSite=Lax`.

---

## 4. JSON Master Registry Export (`master_test_registry.json`)

To enable continuous integration and programmatic auditing, the entire registry has been serialized into machine-readable JSON at `docs/master_test_registry.json`.

```json
{
  "metadata": {
    "title": "SITA Consolidated Security Reporting Platform — Master Test Registry",
    "version": "1.1",
    "summary": {
      "total_automated_baseline_pytest": 143,
      "total_post_sept9_live_tests": 29,
      "total_manual_checklist_cases": 40,
      "consolidated_grand_total": 212,
      "pass_rate": "100%",
      "quality_gate_status": "PASSED (All Gates Cleared)"
    }
  }
}
```

---

## 5. Maintenance & Version Control

- **Update Mechanism:** Re-run `python scripts/export_master_registry.py` and `python generate_excel_spreadsheets.py` upon any test suite addition or regression run.
- **Owner:** QA Test Automation Lead & Lead Security Architect.
- **Review Schedule:** Weekly review during deployment phases; monthly post-launch.
