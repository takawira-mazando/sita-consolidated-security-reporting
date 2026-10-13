# SITA Unified Intelligence Platform — Manual Testing Execution Plan

**Version:** 1.0  
**Date:** August 2026  
**Target:** QA Tester — Day-to-Day Execution  
**Environment:** VPN Tunnel (localhost:8801/8802) or Remote LAN (192.168.101.20:8000/8088)

---

## 0. Quick Start — One-Time Setup

### SSH Tunnels (Run in Two Terminals)
```bash
# Terminal 1 — Backend API (8000 → 8801)
ssh -L 8801:localhost:8000 user@vpn-host

# Terminal 2 — Frontend (8088 → 8802)
ssh -L 8802:localhost:8088 user@vpn-host
```

### Verify Access
| Check | URL | Expected |
|-------|-----|----------|
| Backend Health | http://localhost:8801/health | `{"status":"ok"}` |
| Swagger UI | http://localhost:8801/docs | FastAPI docs load |
| Frontend | http://localhost:8802 | Login overlay appears |

---

## 1. Daily Pre-Test Checklist (5 min)

| # | Action | Pass/Fail | Notes |
|---|--------|-----------|-------|
| 1 | Backend health endpoint returns 200 | ☐ | |
| 2 | Swagger UI loads at `/docs` | ☐ | |
| 3 | Frontend loads at `:8802` — no console errors | ☐ | |
| 4 | Demo accounts endpoint returns 11 accounts | ☐ | `curl -s localhost:8801/api/v1/auth/demo-accounts \| jq '. \| length'` |
| 5 | Public summary returns data | ☐ | `curl -s localhost:8801/api/v1/public/summary \| jq '.findings.total'` |
| 6 | Database migrated (`alembic current` shows head) | ☐ | Run on remote if needed |

**STOP if any ❌ — escalate to dev before proceeding.**

---

## 2. Test Execution Sessions

### Session A: API Smoke (10 min) — Run Every Build

| Step | Action | Command | Expected | Pass/Fail | Defect ID |
|------|--------|---------|----------|-----------|-----------|
| A1 | List demo accounts | `curl -s localhost:8801/api/v1/auth/demo-accounts \| jq .` | 200, 11 accounts, `is_nationwide` for exec/compliance/sre/transversal/admin/operator | ☐ | |
| A2 | Public summary | `curl -s localhost:8801/api/v1/public/summary \| jq .` | 200, findings/assets/risk/connectors/tenancy populated | ☐ | |
| A3 | Tenancy hierarchy | `curl -s localhost:8801/api/v1/auth/tenancy \| jq '.provinces \| length'` | 200, 9 provinces, 156 depts, 347 branches | ☐ | |
| A4 | Demo login — exec (nationwide) | `curl -s -X POST localhost:8801/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"exec"}' \| jq .` | 200, token + user, empty scope in JWT | ☐ | |
| A5 | Demo login — SOC with valid dept | `curl -s -X POST localhost:8801/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"soc","department_id":"home-affairs-digital"}' \| jq .` | 200, token scoped to Home Affairs Digital | ☐ | |
| A6 | Demo login — SOC with INVALID dept | `curl -s -X POST localhost:8801/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"soc","department_id":"treasury"}' \| jq .` | 403, "Requested tenancy scope is outside this demo account's scope" | ☐ | |
| A7 | Demo login — Provincial SOC (GP) | `curl -s -X POST localhost:8801/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"provincesoc","province_id":"gp"}' \| jq .` | 200, token scoped to Gauteng | ☐ | |
| A8 | Demo login — Provincial SOC (WC invalid) | `curl -s -X POST localhost:8801/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"provincesoc","province_id":"wc"}' \| jq .` | 403 | ☐ | |
| A9 | Regular login — admin | `curl -s -X POST localhost:8801/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"admin123"}' \| jq .` | 200, token with ALL_ROLES | ☐ | |
| A10 | Regular login — wrong password | `curl -s -X POST localhost:8801/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"wrong"}' \| jq .` | 401 | ☐ | |

---

### Session B: Frontend Login Flow (20 min) — Run Every Build

**Open:** http://localhost:8802

| Step | Action | Expected | Pass/Fail | Defect ID |
|------|--------|----------|-----------|-----------|
| B1 | Page loads — SITA logo, title, subtitle visible | Login overlay renders | ☐ | |
| B2 | Demo accounts fetch — 11 chips in 3 groups | National (6), Provincial (1), Administration (4) | ☐ | |
| B3 | Click "exec@" chip | Chip highlights, scope section shows "Account default — whole estate" | ☐ | |
| B4 | Click "provincesoc@" chip | Province dropdown enabled (Gauteng), dept dropdown disabled | ☐ | |
| B5 | Click "soc@" chip | Province dropdown shows "Account default", dept dropdown enabled with filtered list | ☐ | |
| B6 | Type "treasury" in search box | Dept list filters to Treasury only | ☐ | |
| B7 | **Valid scope override** — Select "soc@", pick "Treasury", click "Sign in as soc@ SOC Analyst" | Redirect to dashboard, JWT in localStorage | ☐ | |
| B8 | **Invalid scope override** — Select "soc@", pick "Home Affairs", click sign in | Toast: "Requested tenancy scope is outside this demo account's scope" | ☐ | |
| B9 | **Account default** — Select "exec@", leave default, click sign in | Redirect, JWT with empty scope | ☐ | |
| B10 | **Regular login** — admin@example.com / admin123 | Redirect, JWT stored | ☐ | |
| B11 | **Wrong password** — admin@example.com / wrong | Toast: "Invalid credentials" | ☐ | |
| B12 | Province dropdown populates 9 provinces + dept counts | Verify Gauteng shows (X depts) | ☐ | |
| B13 | Stop backend, click sign in | Graceful error toast | ☐ | |
| B14 | Tab through all chips, dropdowns, buttons | All reachable, Enter activates | ☐ | |
| B15 | Click ✕ / backdrop close | Overlay closes | ☐ | |

---

### Session C: Post-Login Verification (5 min) — After Any Successful Login

| Step | Action | How to Verify | Pass/Fail | Defect ID |
|------|--------|---------------|-----------|-----------|
| C1 | JWT in localStorage | DevTools → Application → LocalStorage → `auth_token` exists | ☐ | |
| C2 | JWT payload correct | Copy token → jwt.io → check `roles`, `department_ids`, `province_ids`, `branch_ids` match persona | ☐ | |
| C3 | Dashboard loads | Overview cards render (KPIs, charts) | ☐ | |
| C4 | Role-based sidebar | Only permitted nav items visible | ☐ | |
| C5 | Tenancy badge | Top bar shows scope (e.g., "Gauteng" / "Whole Estate") | ☐ | |

---

### Session D: Tenancy Switching (5 min) — Requires Logged-In State

| Step | Persona | Action | Expected | Pass/Fail | Defect ID |
|------|---------|--------|----------|-----------|-----------|
| D1 | deptadmin (Treasury) | Click tenancy badge → switch to another permitted dept | New JWT issued, badge updates | ☐ | |
| D2 | soc (Home Affairs) | Try switch to Treasury | 403, toast error | ☐ | |
| D3 | Any | Click "Reset to default" | JWT re-issued with original seeded scope | ☐ | |

---

### Session E: Security & Edge (10 min) — Run Weekly or Pre-Release

| Step | Action | Expected | Pass/Fail | Defect ID |
|------|--------|----------|-----------|-----------|
| E1 | Expired token | Mock `exp` in JWT → call protected endpoint | 401, redirect login | ☐ | |
| E2 | Refresh token | Call `/auth/refresh` (if implemented) | New access token | ☐ | |
| E3 | CORS | Frontend (8802) → Backend (8801) requests succeed | No CORS errors in console | ☐ | |
| E4 | Rate limiting | Rapid demo-login calls (20+/sec) | 429 after threshold | ☐ | |
| E5 | SQLi in scope | `department_id": "treasury'; DROP TABLE users;--` | 422 validation error | ☐ | |
| E6 | XSS in label | Seed user with `<script>alert(1)</script>` label | Rendered safely, no execution | ☐ | |
| E7 | HTTPS cookies | Production only: check `Secure`, `SameSite=Lax` | Flags set | ☐ | |

---

### Session F: Cross-Browser (20 min) — Run Pre-Release

| Browser | Viewport | Session B Steps | Pass/Fail | Defect ID |
|---------|----------|-----------------|-----------|-----------|
| Chrome 128+ | 1920x1080 | B1–B15 | ☐ | |
| Firefox 129+ | 1920x1080 | B1–B15 | ☐ | |
| Safari 17+ | 1920x1080 | B1–B15 | ☐ | |
| Chrome Mobile | 375x667 | B1–B3, B6, B7, B10 | ☐ | |
| Chrome Tablet | 768x1024 | B1–B10 | ☐ | |

---

## 3. Defect Logging — On the Spot

| Field | Fill In |
|-------|---------|
| **Test ID** | e.g., B7, A6, D2 |
| **Title** | `[FE/API/SEC] One-line summary` |
| **Environment** | `VPN Tunnel (localhost:8801/8802)` |
| **Steps** | 1. ... 2. ... 3. ... |
| **Expected** | What should happen |
| **Actual** | What happened (screenshot, curl output, console error) |
| **Severity** | 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low |
| **Build/Commit** | `git rev-parse --short HEAD` |

---

## 4. Sign-Off Per Session

| Session | Tester | Date | All Pass? | Blockers |
|---------|--------|------|-----------|----------|
| A — API Smoke | | | ☐ Yes / ☐ No | |
| B — Frontend Login | | | ☐ Yes / ☐ No | |
| C — Post-Login | | | ☐ Yes / ☐ No | |
| D — Tenancy Switch | | | ☐ Yes / ☐ No | |
| E — Security | | | ☐ Yes / ☐ No | |
| F — Cross-Browser | | | ☐ Yes / ☐ No | |

**Overall Release Ready:** ☐ Yes ☐ No  
**Tester Signature:** _______________ **Date:** ___________

---

## 5. Quick Reference — Demo Accounts

| Email | Role | Scope | Password | Use For |
|-------|------|-------|----------|---------|
| exec@example.com | exec | Nationwide | pass123 | Full estate, all dashboards |
| soc@example.com | soc | Home Affairs Digital | pass123 | Dept-scoped SOC |
| appsec@example.com | appsec | Treasury | pass123 | AppSec dashboard |
| dbsec@example.com | dbsec | DPSA HR | pass123 | DB Security |
| compliance@example.com | compliance | Nationwide | pass123 | Compliance, AG export |
| sre@example.com | sre | Nationwide | pass123 | Service Ops, connectors |
| deptadmin@example.com | dept-admin | Treasury | pass123 | Admin users, tenant mgmt |
| branchadmin@example.com | branch-admin | Treasury | pass123 | Branch-level admin |
| transversal@example.com | transversal-admin | Nationwide | pass123 | Cross-dept admin |
| provincesoc@example.com | province-soc-lead | Gauteng | pass123 | Province-scoped, peer blinding |
| admin@example.com | admin (ALL) | Nationwide | admin123 | Everything, create users |
| operator@example.com | operator | Nationwide | operator123 | Create admin, peer rotation |

---

## 6. Common Commands Cheat Sheet

```bash
# Health
curl -s http://localhost:8801/health

# Demo accounts
curl -s http://localhost:8801/api/v1/auth/demo-accounts | jq .

# Public summary
curl -s http://localhost:8801/api/v1/public/summary | jq .

# Tenancy hierarchy
curl -s http://localhost:8801/api/v1/auth/tenancy | jq .

# Demo login (exec nationwide)
curl -s -X POST http://localhost:8801/api/v1/auth/demo-login \
  -H "Content-Type: application/json" -d '{"role":"exec"}' | jq .

# Demo login (SOC with dept override)
curl -s -X POST http://localhost:8801/api/v1/auth/demo-login \
  -H "Content-Type: application/json" -d '{"role":"soc","department_id":"home-affairs-digital"}' | jq .

# Regular login
curl -s -X POST http://localhost:8801/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"admin123"}' | jq .

# Decode JWT (paste token)
# Use https://jwt.io or: python3 -c "import jwt; print(jwt.decode('TOKEN', options={'verify_signature': False}))"
```

---

**End of Manual Testing Execution Plan**  
*Keep this printed or open during test sessions. Check off each step.*