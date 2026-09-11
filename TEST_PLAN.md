# SITA Unified Intelligence Platform — Test Plan

**Version:** 1.0
**Date:** August 2026
**Target Release:** v1.0 (Go-Live September 2026)
**Environment:** Local Dev (http://localhost:3000) → Staging → Production

---

## 1. Scope & Objectives

### In Scope
- **API Endpoints** (backend FastAPI):
  - `GET /api/v1/auth/demo-accounts` — list seeded demo personas for login page
  - `GET /api/v1/public/summary` — aggregate estate summary (pre-login landing page)
  - `POST /api/v1/auth/demo-login` — sign in as demo persona with optional tenancy scope
  - `POST /api/v1/auth/login` — regular email/password login
  - `GET /api/v1/auth/tenancy` — national hierarchy for tenancy picker
- **Frontend Flows** (React + Vite, port 3000):
  - Login overlay: persona chips, tenancy scope picker, sign-in
  - Demo login flow with scope override (province/department/branch)
  - Account default scope fallback
- **Tenancy & RBAC**: demo account entitlements, scope_covers enforcement, nationwide vs. scoped personas
- **Security**: JWT issuance, role claims, tenancy scope in token

### Out of Scope
- Authenticated dashboard pages (Risks, Findings, Alerts, Compliance, Admin)
- Alert dispatch (Email/Teams/PagerDuty)
- Ingestion pipeline, normaliser, risk engine
- Backend SAST/bandit, frontend SAST/semgrep (already done)

---

## 2. Test Environment

### Local Development (Laptop → VPN Tunnel)

| Component | Tunnel URL | Remote Server (LAN only) |
|-----------|------------|---------------------------|
| Frontend (Vite) | http://localhost:8802 | http://192.168.101.20:8088/ |
| Backend API base | http://localhost:8801/api/v1 | http://192.168.101.20:8000/api/v1 |
| Health check | http://localhost:8801/health | http://192.168.101.20:8000/health |
| Swagger UI | http://localhost:8801/docs | http://192.168.101.20:8000/docs |
| OpenAPI schema | http://localhost:8801/openapi.json | http://192.168.101.20:8000/openapi.json |

> **Note:** Over VPN only SSH is permitted. Use the tunnel URLs (localhost:8801/8802) from your laptop. The remote server URLs (192.168.101.20) work only from the server itself or machines on its LAN (192.168.101.x), unless your network team opens ports 8088/8000 in the FortiGate policy for 192.168.101.20.

### Local Development (Direct — Optional)

| Component | URL / Command |
|-----------|---------------|
| Frontend (Vite) | `cd frontend && npm run dev` → http://localhost:3000 |
| Backend (FastAPI) | `cd backend && uvicorn app.main:app --reload` → http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Prerequisites (Remote Server)
```bash
# On remote server (192.168.101.20)
cd /path/to/sita-platform/backend
pip install -r requirements.txt
alembic upgrade head
python seed_admin_accounts.py  # seeds demo users + admin

# Frontend built and served on :8088 (nginx/static)
cd /path/to/sita-platform/frontend
npm install
npm run build
# nginx serves dist/ on port 8088
```

### SSH Tunnel Setup (from Laptop)
```bash
# Terminal 1: Backend API tunnel (8000 → 8801)
ssh -L 8801:localhost:8000 user@remote-vpn-host

# Terminal 2: Frontend tunnel (8088 → 8802)  
ssh -L 8802:localhost:8088 user@remote-vpn-host

# Then use http://localhost:8801 and http://localhost:8802 from browser/curl
```

---

## 3. Test Data — Seeded Demo Accounts (DEMO_ACCOUNTS)

| Email | Role | Label | Scope (department_ids / province_ids) | Nationwide |
|-------|------|-------|----------------------------------------|------------|
| exec@example.com | exec | Executive | [] | ✅ |
| soc@example.com | soc | SOC Analyst | [home-affairs-digital] | ❌ |
| appsec@example.com | appsec | AppSec | [treasury] | ❌ |
| dbsec@example.com | dbsec | DB Security | [dpsa-hr] | ❌ |
| compliance@example.com | compliance | Compliance | [] | ✅ |
| sre@example.com | sre | Service Ops | [] | ✅ |
| deptadmin@example.com | dept-admin | Dept Admin | [treasury] | ❌ |
| branchadmin@example.com | branch-admin | Branch Admin | [treasury] | ❌ |
| transversal@example.com | transversal-admin | Transversal Admin | [] | ✅ |
| provincesoc@example.com | province-soc-lead | Provincial SOC Lead | province_ids=[gp] | ❌ |
| admin@example.com | admin (ALL_ROLES) | Admin | [] | ✅ |
| operator@example.com | operator | Platform Operator | [] | ✅ |

**Passwords:** `pass123` (all except admin=admin123, operator=operator123)

---

## 4. Tests Completed During Development (Regression Baseline)

These unit/integration tests **already pass** in CI (commit a53f829, 128 tests). Do not re-run manually unless code changed.

| Test File | Coverage | Key Assertions |
|-----------|----------|----------------|
| `tests/test_public_summary.py` | `/public/summary` | populated + empty graceful; all JSON fields validated |
| `tests/test_new_endpoints.py` | `/benchmark/province`, `/exports/ag-compliance` | scoped vs national blinding, audit row with SHA-256, auth required |
| `tests/test_tenancy.py` (490 lines, 8 classes) | Tenancy filter SQL, province expansion, demo scopes, delegated-admin matrix, tier ordering, tenancy consistency, ministry lookups, person identity + HR sync | 128 tests passing |
| `tests/test_benchmark.py` | Benchmark leaderboard | peer blinding, scope enforcement |
| `tests/test_exports_ag.py` | AG export + verify endpoint | integrity hash, attestation scope |
| `tests/test_admin_logins.py` | Tier 1-4 admin logins | all roles authenticate |

**Run command:** `cd backend && python -m pytest tests/ -v`

---

## 5. Manual Test Cases — Tester Execution

### 5.1 API Smoke Tests (curl / Postman)

| ID | Endpoint | Method | Expected | Notes |
|----|----------|--------|----------|-------|
| API-01 | `/api/v1/auth/demo-accounts` | GET | 200, array of 11 DemoAccount objects | `is_nationwide` true for exec, compliance, sre, transversal, admin, operator |
| API-02 | `/api/v1/public/summary` | GET | 200, JSON with findings, assets, risk, connectors, latest_ingest, tenancy counts | No auth required; aggregate only, no PII |
| API-03 | `/api/v1/auth/tenancy` | GET | 200, provinces (9), departments (156), branches (347) | Public hierarchy for login picker |
| API-04 | `/api/v1/auth/demo-login` | POST `{ "role": "exec" }` | 200, `{ token, user }` | JWT with empty scope (nationwide) |
| API-05 | `/api/v1/auth/demo-login` | POST `{ "role": "soc", "department_id": "home-affairs-digital" }` | 200, JWT scoped to that dept | Scope override within entitlement |
| API-06 | `/api/v1/auth/demo-login` | POST `{ "role": "soc", "department_id": "treasury" }` | 403, "Requested tenancy scope is outside this demo account's scope" | scope_covers enforcement |
| API-07 | `/api/v1/auth/demo-login` | POST `{ "role": "provincesoc", "province_id": "gp" }` | 200, JWT scoped to Gauteng | Province-scoped persona |
| API-08 | `/api/v1/auth/demo-login` | POST `{ "role": "provincesoc", "province_id": "wc" }` | 403 | Outside GP entitlement |
| API-09 | `/api/v1/auth/login` | POST `{ "email": "admin@example.com", "password": "admin123" }` | 200, JWT with all roles | Admin all-roles token |
| API-10 | `/api/v1/auth/login` | POST wrong password | 401 | Auth failure |

**Sample curl (via SSH Tunnel — localhost:8801):**
```bash
# Demo accounts list
curl -s http://localhost:8801/api/v1/auth/demo-accounts | jq .

# Public summary
curl -s http://localhost:8801/api/v1/public/summary | jq .

# Demo login as exec (nationwide)
curl -s -X POST http://localhost:8801/api/v1/auth/demo-login \
  -H "Content-Type: application/json" \
  -d '{"role": "exec"}' | jq .

# Demo login as SOC with dept override
curl -s -X POST http://localhost:8801/api/v1/auth/demo-login \
  -H "Content-Type: application/json" \
  -d '{"role": "soc", "department_id": "home-affairs-digital"}' | jq .
```

**Sample curl (Direct on Remote Server LAN — 192.168.101.20):**
```bash
# Demo accounts list
curl -s http://192.168.101.20:8000/api/v1/auth/demo-accounts | jq .

# Public summary
curl -s http://192.168.101.20:8000/api/v1/public/summary | jq .

# Demo login as exec (nationwide)
curl -s -X POST http://192.168.101.20:8000/api/v1/auth/demo-login \
  -H "Content-Type: application/json" \
  -d '{"role": "exec"}' | jq .
```

---

### 5.2 Frontend — Login Page (`http://localhost:8802` / `http://192.168.101.20:8088/`)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| FE-01 | Page loads | Open http://localhost:8802 (tunnel) or http://192.168.101.20:8088/ (LAN) | Login overlay visible; SITA logo, title, subtitle |
| FE-02 | Demo accounts fetch | Page load triggers `GET /auth/demo-accounts` | 11 persona chips render in 3 groups: National (6), Provincial (1), Administration (4) |
| FE-03 | Select persona chip | Click "exec@" chip | Chip highlighted; tenancy scope section appears; "Account default — whole estate" |
| FE-04 | Select provincial persona | Click "provincesoc@" chip | Province dropdown enabled; shows "Gauteng (X depts)"; dept dropdown disabled |
| FE-05 | Select dept-scoped persona | Click "soc@" chip | Province dropdown shows "Account default — whole estate"; dept dropdown enabled with filtered list |
| FE-06 | Search departments | Type "treasury" in search | Dept list filters to matching names/IDs |
| FE-07 | Scope override — valid | Select "soc@", pick "Treasury" dept, click "Sign in as soc@ SOC Analyst" | POST `/demo-login` with dept_id; JWT stored; redirect to dashboard |
| FE-08 | Scope override — invalid | Select "soc@", pick "Home Affairs" dept (outside entitlement), click sign in | 403 error toast: "Requested tenancy scope is outside this demo account's scope" |
| FE-09 | Account default fallback | Select "exec@", leave scope as "Account default — whole estate", click sign in | POST `/demo-login` with no override; JWT issued with empty scope |
| FE-10 | Regular login | Enter `admin@example.com` / `admin123`, click "Sign In to Dashboard" | POST `/auth/login`; JWT stored; redirect |
| FE-11 | Regular login — wrong password | Enter valid email, wrong password | 401 error toast: "Invalid credentials" |
| FE-12 | Tenancy hierarchy fetch | Page load triggers `GET /auth/tenancy` | Province dropdown populates with 9 provinces + dept counts |
| FE-13 | Network error handling | Stop backend, click any sign-in button | Graceful error toast: "Network error" or similar |
| FE-14 | Keyboard navigation | Tab through chips, dropdowns, buttons | All interactive elements reachable; Enter activates |
| FE-15 | Close overlay (modal mode) | Click ✕ or backdrop | Overlay closes; `onClose` callback fired |

---

### 5.3 Post-Login Sanity (after any successful login)

| ID | Check | How to Verify |
|----|-------|---------------|
| PL-01 | JWT stored | DevTools → Application → LocalStorage → `auth_token` present |
| PL-02 | Token payload | Decode JWT (jwt.io): `roles`, `department_ids`, `province_ids`, `branch_ids` match persona |
| PL-03 | Dashboard loads | Redirect to `/dashboard` (or `/`) shows overview cards |
| PL-04 | Role-based sidebar | Sidebar shows only permitted nav items for role |
| PL-05 | Tenancy badge | Top bar shows active scope (e.g., "Gauteng" or "Whole Estate") |

---

### 5.4 Tenancy Switching (without re-auth)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| TS-01 | Switch within entitlement | Login as `deptadmin` (Treasury), click tenancy badge → switch to another permitted dept | POST `/api/v1/auth/switch-tenant` → new JWT issued; badge updates |
| TS-02 | Switch outside entitlement | Login as `soc` (Home Affairs), try switch to Treasury | 403 from backend; toast error |
| TS-03 | Reset to account default | After switch, click "Reset to default" | Empty body POST → JWT re-issued with original seeded scope |

---

### 5.5 Security & Edge Cases

| ID | Test | Expected |
|----|------|----------|
| SEC-01 | Expired token | Wait 8h (or mock exp), request protected endpoint → 401, redirect login |
| SEC-02 | Refresh token | Use refresh endpoint → new access token issued |
| SEC-03 | CORS | Frontend (3000) → Backend (8000) requests succeed; no CORS errors |
| SEC-04 | Rate limiting | Rapid demo-login calls → 429 after threshold |
| SEC-05 | SQL injection in scope params | Send `department_id': "treasury'; DROP TABLE users;--` | 422 validation error, no DB execution |
| SEC-06 | XSS in demo account label | Seed user with `<script>alert(1)</script>` label → rendered safely (no execution) |
| SEC-07 | HTTPS enforcement | Production: all cookies Secure, SameSite=Lax |

---

### 5.6 Cross-Browser / Responsive

| Browser | Viewport | Test IDs |
|---------|----------|----------|
| Chrome 128+ | Desktop (1920x1080) | All FE-XX |
| Firefox 129+ | Desktop | FE-01 to FE-15 |
| Safari 17+ | Desktop | FE-01 to FE-15 |
| Chrome Mobile | 375x667 (iPhone SE) | FE-01, FE-02, FE-03, FE-06, FE-07, FE-10 |
| Chrome Tablet | 768x1024 (iPad) | FE-01 to FE-10 |

---

## 6. Test Execution Checklist

### Pre-Test Setup
- [ ] Backend running on :8000 (check `/docs`)
- [ ] Frontend running on :3000 (check console for errors)
- [ ] Database migrated (`alembic upgrade head`)
- [ ] Demo users seeded (`python seed_admin_accounts.py`)
- [ ] `test_admin_logins.py` passes (verifies all tiers)

### API Smoke (5 min)
- [ ] API-01 through API-10

### Frontend Login Flow (15 min)
- [ ] FE-01 through FE-15

### Post-Login & Tenancy (10 min)
- [ ] PL-01 through PL-05
- [ ] TS-01 through TS-03

### Security & Edge (10 min)
- [ ] SEC-01 through SEC-07

### Cross-Browser (20 min)
- [ ] Desktop Chrome/Firefox/Safari
- [ ] Mobile/Tablet Chrome

---

## 7. Defect Reporting Template

| Field | Description |
|-------|-------------|
| **ID** | Auto (Jira/GitHub) |
| **Title** | `[FE/API/SEC] Short description` |
| **Environment** | Local / Staging / Prod |
| **Steps to Reproduce** | Numbered, exact |
| **Expected** | What should happen |
| **Actual** | What happened (screenshot, curl output, console error) |
| **Severity** | Critical / High / Medium / Low |
| **Related Test ID** | e.g., FE-07, API-06 |

---

## 8. Sign-Off Criteria

| Gate | Criteria |
|------|----------|
| **Dev Complete** | All unit tests pass (128/128); API smoke passes |
| **QA Pass** | All manual test cases (FE-01–15, PL-01–05, TS-01–03, SEC-01–07) pass |
| **Security** | No Critical/High vulns; SAST clean (bandit 0 issues, semgrep 0 issues) |
| **UAT Ready** | Stakeholder demo script validated; training materials reviewed |

---

## 9. Traceability Matrix

| Requirement | Source | Test Coverage |
|-------------|--------|---------------|
| Demo accounts list for login | Flight Plan Phase 11 (Aug 13-14) | API-01, FE-02 |
| Public estate summary (pre-login) | Flight Plan Phase 11 (Aug 13) | API-02 |
| Tenancy-aware demo login | Flight Plan Phase 11 (Aug 13-14) | API-04–08, FE-03–09 |
| Scope override enforcement (`scope_covers`) | Flight Plan Phase 11 (Aug 13) | API-06, API-08, FE-08 |
| Tenancy hierarchy for picker | Flight Plan Phase 11 (Aug 13) | API-03, FE-12 |
| Tenant switch without re-auth | Flight Plan Phase 11 (Aug 13) | TS-01–03 |
| Admin credentials generation | Flight Plan Phase 11 (Aug 13) | `test_admin_logins.py` |
| HR-only provisioning | Flight Plan Phase 11 (Aug 14) | `test_tenancy.py::TestResolveScope` |

---

## 10. Appendix — Quick Reference

### Demo Account Quick-Pick
| Persona | Use For Testing |
|---------|-----------------|
| `exec@example.com` | Whole estate, all dashboards, nationwide |
| `soc@example.com` | Dept-scoped (Home Affairs), SOC dashboard |
| `provincesoc@example.com` | Province-scoped (Gauteng), peer leaderboard blinding |
| `admin@example.com` | All roles, admin users page, tenant management |
| `operator@example.com` | Platform operator: create admin, peer rotation only |

### Common URLs

**Via SSH Tunnel (from Laptop over VPN):**
```
Frontend:           http://localhost:8802
Backend API:        http://localhost:8801
Swagger UI:         http://localhost:8801/docs
ReDoc:              http://localhost:8801/redoc
Demo accounts:      GET  http://localhost:8801/api/v1/auth/demo-accounts
Public summary:     GET  http://localhost:8801/api/v1/public/summary
Tenancy hierarchy:  GET  http://localhost:8801/api/v1/auth/tenancy
Demo login:         POST http://localhost:8801/api/v1/auth/demo-login
Regular login:      POST http://localhost:8801/api/v1/auth/login
Switch tenant:      POST http://localhost:8801/api/v1/auth/switch-tenant
```

**Direct on Remote Server LAN (192.168.101.x):**
```
Frontend:           http://192.168.101.20:8088/
Backend API:        http://192.168.101.20:8000
Swagger UI:         http://192.168.101.20:8000/docs
ReDoc:              http://192.168.101.20:8000/redoc
Demo accounts:      GET  http://192.168.101.20:8000/api/v1/auth/demo-accounts
Public summary:     GET  http://192.168.101.20:8000/api/v1/public/summary
Tenancy hierarchy:  GET  http://192.168.101.20:8000/api/v1/auth/tenancy
Demo login:         POST http://192.168.101.20:8000/api/v1/auth/demo-login
Regular login:      POST http://192.168.101.20:8000/api/v1/auth/login
Switch tenant:      POST http://192.168.101.20:8000/api/v1/auth/switch-tenant
```

**Local Dev (Optional):**
```
Frontend:           http://localhost:3000
Backend API:        http://localhost:8000
Swagger UI:         http://localhost:8000/docs
```

### Run All Backend Tests
```bash
cd backend
python -m pytest tests/ -v --tb=short
# Expected: 128 passed
```

### Run Frontend Lint/Typecheck
```bash
cd frontend
npm run lint
npm run typecheck
```

---

**Prepared by:** Takawira Mazando (Bantu InfoTech)
**Reviewed by:** _________________ **Date:** ___________
**Approved by:** _________________ **Date:** ___________