# SITA Consolidated Security Reporting Platform
# Deliverable C2: International Security Framework Mapping (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Security Frameworks:** OWASP Top 10 (2021) & ISO/IEC 27001:2022 Security Controls  
**Cross-Reference Document:** `RISK_REGISTER.md`  
**Target Audience:** Chief Information Security Officer (CISO), Security Engineering, Peter (Governance Lead)

---

## 1. Executive Summary & Framework Coverage

The **SITA Consolidated Security Reporting Platform** aligns with leading international cybersecurity and risk management frameworks:
1. **OWASP Top 10 (2021):** Ensuring resilient defense against the most prevalent web application security risks.
2. **ISO/IEC 27001:2022 (Annex A Controls):** Structuring information security, cybersecurity, and privacy management practices across organizational and technical controls.

This mapping provides a comprehensive correlation matrix linking platform architectural controls to both frameworks and tracking the remediation status of active risk register findings.

---

## 2. OWASP Top 10 (2021) Mapping Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                OWASP TOP 10 (2021) MAPPING MATRIX                                      │
├────┬─────────────────────────────┬─────────────────────────────────┬───────────────────────────────────┤
│ ID │ OWASP Category              │ Platform Control Implementation │ Relevant Risk Register & Status   │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A01 │ Broken Access Control       │ • Multi-tenant SQL filter       │ R-04 (CORS Restrict — In Progress)│
│    │                             │ • Strict `scope_covers` guard   │ TC-RBAC-01 through TC-RBAC-08     │
│    │                             │ • Zero-leakage JWT validation   │ (100% Passed)                     │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A02 │ Cryptographic Failures      │ • HMAC-SHA256 JWT tokens        │ R-02 (JWT Secret Rotation — P1)   │
│    │                             │ • SHA-256 AG export hash chains │ R-08 (TLS/HSTS Enforcement — P1)  │
│    │                             │ • TLS 1.3 in-transit encryption │ TC-AG-01 (Passed)                 │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A03 │ Injection                   │ • SQLAlchemy parameterized ORM  │ Parameterized query enforcement   │
│    │                             │ • Schema validation via Pydantic│ SEC-05 (SQLi Injection Reject —   │
│    │                             │ • Imperva WAF SQLi block feed   │ Passed)                           │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A04 │ Insecure Design             │ • 4-tier zero-trust hierarchy   │ Anti-elevation delegation matrix  │
│    │                             │ • Fail-closed authorization     │ `test_tenancy.py` (84 tests passed│
│    │                             │ • Blinded provincial benchmarks │ TC-RBAC-05 (Passed)               │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A05 │ Security Misconfiguration   │ • Environment guardrails        │ R-03 (Demo Seeding Disable — P1)  │
│    │                             │ • Dev mode secret check         │ R-05 (Swagger Docs Toggle — P2)   │
│    │                             │ • Hardened Docker compose       │ R-07 (Health Endpoint Hardening)  │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A06 │ Vulnerable / Outdated Comp. │ • HCL AppScan SAST/DAST ingest  │ Continuous ingestion pipeline     │
│    │                             │ • Dependabot / pip-audit checks │ POST9-02, POST9-03, POST9-14      │
│    │                             │ • Pinned dependency hashes      │ (50 real AppScan findings audited)│
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A07 │ Identification & Auth Fail. │ • JWT signature verification    │ R-01 (Default Creds Rotation — P1)│
│    │                             │ • Rate limiting (429 Too Many)  │ R-06 (Okta MFA Enforcement — P1)  │
│    │                             │ • Bcrypt password hashing       │ API-09, API-10, SEC-01, SEC-04    │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A08 │ Software & Data Integrity   │ • Verifiable SHA-256 AG export  │ TC-AG-01 (Cryptographic hash      │
│    │                             │ • Vite reproducible builds      │ verified)                         │
│    │                             │ • Tamper-evident audit rows     │ POST9-28 (Clean dist/ build)      │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A09 │ Security Logging & Monitor. │ • PostgreSQL immutable audit_log│ TC-AG-03 (Immutable audit trails) │
│    │                             │ • Prometheus metrics & SLOs     │ POST9-16 (47 active alerts)       │
│    │                             │ • Correlated SOC alert engine   │ POST9-23 (MTTD/MTTR verified)     │
├────┼─────────────────────────────┼─────────────────────────────────┼───────────────────────────────────┤
│A10 │ Server-Side Request Forgery │ • URL validator for webhooks    │ Strict egress whitelisting on     │
│    │                             │ • Restricted outbound connectors│ alert dispatchers                 │
└────┴─────────────────────────────┴─────────────────────────────────┴───────────────────────────────────┘
```

---

## 3. ISO/IEC 27001:2022 Control Mapping Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ISO/IEC 27001:2022 ANNEX A CONTROL MAPPING                                │
├──────────┬─────────────────────────────┬─────────────────────────────────┬─────────────────────────────┤
│ Control  │ Control Domain & Title      │ Platform Technical Mechanism    │ Verification Reference      │
├──────────┼─────────────────────────────┼─────────────────────────────────┼─────────────────────────────┤
│ A.5.15   │ Access control              │ JWT scopes, `scope_covers` guard│ `test_tenancy.py` (84 tests)│
│ A.5.17   │ Authentication information  │ Bcrypt, JWT TTL, credential rot.│ R-01, R-02, test_admin_login│
│ A.5.18   │ Access rights               │ 4-tier RBAC delegation matrix   │ `can_manage`, POST9-19/20   │
│ A.8.2    │ Privileged access rights    │ Separation of superadmin/oper.  │ `TestOperatorGovernance`    │
│ A.8.7    │ Protection against malware  │ Ingest payload sanitization     │ Ingest schema validator     │
│ A.8.9    │ Configuration management    │ Pydantic BaseSettings, .env file│ `app/config.py` guardrails  │
│ A.8.12   │ Data leakage prevention     │ Zero-leakage `tenant_filter` SQL│ POST9-21 (0 leaks verified) │
│ A.8.15   │ Logging                     │ Structured JSON logging & audit │ `audit_logs` table (Postgres│
│ A.8.16   │ Monitoring activities       │ SOC SLO metrics (MTTD/MTTR)     │ POST9-23, `/metrics/soc/slo`│
│ A.8.20   │ Network security            │ Reverse proxy TLS, FortiGate VPN│ R-08, SSH Tunnel localhost  │
│ A.8.23   │ Web application security    │ OWASP Top 10 defense stack      │ Full automated test suite   │
│ A.8.25   │ Secure development lifecycle│ Automated CI testing, pytest    │ A1 Test Report (173 tests)  │
│ A.8.28   │ Secure coding               │ Static typing (Python + TS)     │ MET-02 (`tsc` 0 errors)     │
└──────────┴─────────────────────────────┴─────────────────────────────────┴─────────────────────────────┘
```

---

## 4. Governance Sign-Off

This security mapping serves as the authoritative baseline for SITA cyber-compliance audits and ISO 27001 surveillance certification.
