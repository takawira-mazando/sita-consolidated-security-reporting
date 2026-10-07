# SITA Consolidated Security Reporting Platform
# Deliverable B4: POPIA Remediation Plan & Gap Tracker (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Governing Regulation:** Protection of Personal Information Act (POPIA Act No. 4 of 2013, Republic of South Africa)  
**Cross-Reference Document:** `RISK_REGISTER.md` (Risks R-01 through R-08)  
**Target Compliance Milestone:** Pre-POC Staging & Live Demonstration Promotion  
**Remediation Target:** Elevate statutory compliance from 82.9% to **≥ 95%** prior to full production go-live.

---

## 1. Statutory Alignment & Remediation Framework

Section 19 of the Protection of Personal Information Act (POPIA) mandates that a responsible party must secure the integrity and confidentiality of personal information in its possession or under its control by taking appropriate, reasonable technical and organizational measures to prevent:
- Loss of, damage to, or unauthorized destruction of personal information.
- Unlawful access to or processing of personal information.

This **Remediation Plan** systematically maps each identified vulnerability and misconfiguration from the platform's Risk Register (`RISK_REGISTER.md`) to specific POPIA sections, establishing clear ownership, technical treatments, and verification milestones.

---

## 2. Risk Register (R-01 through R-08) to POPIA Statutory Mapping

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    RISK REGISTER TO POPIA STATUTORY MAPPING                     │
├────┬──────────┬─────────────────────────────┬───────────────────┬───────────────┤
│ ID │ Priority │ Vulnerability Description   │ POPIA Section     │ Residual Risk │
├────┼──────────┼─────────────────────────────┼───────────────────┼───────────────┤
│R-01│ P1       │ Default admin/demo creds    │ Section 19(1)(b)  │ High → Low    │
│R-02│ P1       │ Default JWT secret in source│ Section 19(2)(c)  │ High → Low    │
│R-03│ P1       │ Demo seeding in shared env  │ Section 11 & 19   │ High → Low    │
│R-04│ P2       │ Permissive CORS wildcard    │ Section 19 & 21   │ Med → Low     │
│R-05│ P2       │ Swagger docs exposed        │ Section 17 & 19   │ Med → Low     │
│R-06│ P1       │ Okta profile MFA disabled   │ Section 19(2)(b)  │ High → Low    │
│R-07│ P2       │ Diagnostic endpoint leakage │ Section 19(1)     │ Med → Low     │
│R-08│ P1       │ TLS/HSTS header enforcement │ Section 19(1)(b)  │ High → Low    │
└────┴──────────┴─────────────────────────────┴───────────────────┴───────────────┘
```

---

## 3. Detailed Remediation Workflows

### R-01: Default Demo and Administrative Credentials in Source
- **POPIA Impact:** Section 19(1)(b) — Failure to establish safeguards against unauthorized access.
- **Root Cause:** Hardcoded demo passwords (`pass123`, `admin123`) in `app/api/routers/auth.py` and `app/config.py`.
- **Remediation Action:**
  1. Remove all fallback passwords from repository code.
  2. Implement environment-variable driven bootstrap credentials (`BOOTSTRAP_ADMIN_PASSWORD`).
  3. Fail startup immediately in staging/production if default passwords remain present.
- **Owner:** Platform Security Engineering
- **Target Date:** Pre-POC Gate (Immediate)
- **Verification:** Unit test assertion rejecting default strings; automated secret scan in CI.

### R-02: Weak Default JWT Secret and Bootstrap Password
- **POPIA Impact:** Section 19(2)(c) — Vulnerability permitting forged authentication tokens.
- **Root Cause:** Static development string `"sita-local-dev-secret-change-me"` in `app/config.py`.
- **Remediation Action:**
  1. Rotate JWT signing secret to a cryptographically strong 256-bit entropy value generated via `secrets.token_hex(32)`.
  2. Integrate with HashiCorp Vault or AWS Secrets Manager / Azure Key Vault.
  3. Enforce startup guardrail in `app/config.py` raising `ValueError` in non-dev modes if default secret is detected.
- **Owner:** DevOps / Security Architecture
- **Target Date:** Pre-POC Gate (Immediate)
- **Verification:** CI validation test confirming application refuses startup with default secret in `production`.

### R-03: Demo User Seeding Enabled by Default
- **POPIA Impact:** Section 11 — Processing limitation; unvetted synthetic user accounts active in live database.
- **Root Cause:** `seed_demo_users_enabled = True` in default settings.
- **Remediation Action:**
  1. Set default `seed_demo_users_enabled = False` in production environment configuration.
  2. Isolate demo seeding strictly behind a dedicated `--seed-demo` CLI flag or local Docker compose profile.
- **Owner:** DevOps Engineering
- **Target Date:** Pre-POC Gate (Immediate)
- **Verification:** Database inspection post-deployment confirms 0 demo user accounts created in production staging.

### R-04: Permissive CORS Configuration
- **POPIA Impact:** Section 19 & Section 21 — Cross-origin data exposure risk.
- **Root Cause:** Wildcard `allow_origins = ["*"]` combined with credential support in development profiles.
- **Remediation Action:**
  1. Restrict CORS origins explicitly to authorized SITA domain names and VPN IP ranges (e.g. `http://192.168.101.20:8088`, `https://security.sita.gov.za`).
  2. Strip wildcard fallback in non-local profiles.
- **Owner:** Backend & Frontend Lead
- **Target Date:** Phase 4 Hardening
- **Verification:** Automated browser preflight test asserting origin header rejection from unauthorized hosts.

### R-05: Swagger / OpenAPI Documentation Exposure
- **POPIA Impact:** Section 17 & Section 19 — System reconnaissance enabling targeted intrusion.
- **Root Cause:** FastAPI `/docs` and `/redoc` enabled by default.
- **Remediation Action:**
  1. Bind Swagger UI availability to `settings.environment in ("dev", "local", "test")`.
  2. Disable OpenAPI JSON schema routes in production deployments.
- **Owner:** Backend Lead
- **Target Date:** Phase 4 Hardening
- **Verification:** HTTP GET `/docs` and `/openapi.json` return `HTTP 404 Not Found` in production profile.

### R-06: Okta MFA Disabled for Privileged Identity Profiles
- **POPIA Impact:** Section 19(2)(b) — Inadequate authentication assurance for administrative users.
- **Root Cause:** Okta tenant configuration lacked mandatory MFA enrollment for security analysts and SITA command center staff.
- **Remediation Action:**
  1. Enforce Okta Verify / FIDO2 WebAuthn for all Tier 1 through Tier 4 users.
  2. Require step-up MFA for tenant switching and Auditor-General export downloads.
- **Owner:** Identity & Access Management (IAM) Team
- **Target Date:** Pre-POC Gate (Immediate)
- **Verification:** Authentication trace confirming MFA challenge prompt during login.

### R-07: Diagnostic & Health Endpoint Information Leakage
- **POPIA Impact:** Section 19(1) — Operational metadata disclosure aiding attack surface enumeration.
- **Root Cause:** `/health/detailed` exposes database connection pool metrics and internal hostnames.
- **Remediation Action:**
  1. Simplify public `/health` endpoint to return minimal status `{ "status": "ok" }`.
  2. Restrict `/health/detailed` to localhost and internal Prometheus scraping networks.
- **Owner:** Platform Engineering
- **Target Date:** Phase 4 Hardening
- **Verification:** External curl request to `/health/detailed` returns `HTTP 403 Forbidden`.

### R-08: TLS / HSTS and Security Header Enforcement
- **POPIA Impact:** Section 19(1)(b) & Section 22 — Data interception in transit over government WAN.
- **Root Cause:** HTTP allowed over LAN without mandatory redirect to HTTPS; missing HSTS headers.
- **Remediation Action:**
  1. Enforce TLS 1.3 encryption on remote host reverse proxy (Nginx).
  2. Inject `Strict-Transport-Security: max-age=31536000; includeSubDomains` header.
  3. Configure FortiGate network policy to reject unencrypted port 80 traffic.
- **Owner:** Infrastructure & Network Security Team
- **Target Date:** Pre-POC Gate (Immediate)
- **Verification:** SSL Labs / OpenSSL test verifying A+ rating and HSTS presence.

---

## 4. Remediation Progress & Post-Remediation Compliance Projection

$$\text{Projected POPIA Compliance Index} = \frac{97 + 16 \text{ Remediated Controls}}{117 \text{ Total Controls}} = \mathbf{96.58\%}$$

Upon executing the P1 remediation items prior to the Department of Home Affairs PoC launch, the SITA platform achieves full audit readiness under the South African Information Regulator's statutory inspection standard.
