# SITA Consolidated Security Reporting Platform
# Deliverable F1: Platform Security Hardening & Defect Remediation Guide (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Classification:** SITA Technical / Operational Security Standard  
**Cross-Reference Document:** `RISK_REGISTER.md` (Risks R-01 through R-08) & `backend/app/config.py`  
**Execution Mode:** Parallel Ongoing Hardening (Phase 4)  
**Target State:** Complete resolution of all P1 and P2 risk register items prior to Production Go-Live.

---

## 1. Executive Summary

This **Platform Security Hardening Guide (Deliverable F1)** details the technical specifications, code guardrails, configuration templates, and operational runbooks required to eliminate default credentials, enforce cryptographic token security, restrict attack surfaces, and harden the platform for high-assurance public sector deployment.

---

## 2. Priority 1 (P1) Remediation Specifications

### 2.1 R-01 & R-02: Credential & Secret Management Hardening

#### A. Codebase Invariant (`app/config.py`)
The backend settings engine implements explicit startup validators that reject default development credentials outside `dev`/`test` environments:

```python
@model_validator(mode="after")
def _guard_non_dev_defaults(self):
    if not self.jwt_secret:
        raise ValueError("JWT_SECRET must not be empty")
    if self.environment.lower() not in ("dev", "development", "test", "testing"):
        if self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET is still the default dev value; set a strong secret for non-dev environments")
        if not self.bootstrap_admin_password or self.bootstrap_admin_password == "admin123":
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be a strong, non-default value in non-dev environments")
        if self.seed_demo_users_enabled:
            raise ValueError("SEED_DEMO_USERS_ENABLED must be false in non-dev environments")
    return self
```

#### B. Production Key Generation Runbook
Generate high-entropy 256-bit cryptographic secrets for deployment:
```bash
# Generate high-entropy JWT Signing Secret (64-char hex)
python -c "import secrets; print(secrets.token_hex(32))"

# Generate strong Bootstrap Admin Password (32-char alphanumeric)
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

#### C. Production Environment Template (`.env.production`)
```env
ENVIRONMENT=production
JWT_SECRET=4a8f9c1e7b2d5a3f8c0e1b4d6a8f0c2e4b6a8d0e2f4a6b8c0d2e4f6a8b0c2d4e
BOOTSTRAP_ADMIN_EMAIL=ciso-admin@sita.gov.za
BOOTSTRAP_ADMIN_PASSWORD=K8#vP9$mQ2!wZ5*rL1^yT7&nB3@xS6
SEED_DEMO_USERS_ENABLED=false
DATABASE_URL=postgresql+asyncpg://sita_prod_user:${DB_PASSWORD}@192.168.101.20:5432/sita_db
```

---

### 2.2 R-03: Disabling Demo Seeding in Shared/Remote Environments

In `app/main.py`, demo user seeding is conditioned strictly on the boolean flag:
```python
if settings.seed_demo_users_enabled:
    created = await auth.seed_demo_users(session)
```
- **Local Dev:** `SEED_DEMO_USERS_ENABLED=true` enables rapid persona switching for DHA demo validation.
- **Staging & Production:** `SEED_DEMO_USERS_ENABLED=false` blocks synthetic persona injection; user provisioning is driven exclusively by the official DPSA HR database sync (`seed-hr-system-branches.sql`).

---

### 2.3 R-06: Multifactor Authentication (MFA) Policy Enforcement

1. **Okta Tenant Policy:**
   - Require MFA challenge for all accounts in the `SITA-Security-Command` and `DHA-Tenant-Admins` groups.
   - Designate **Okta Verify (Push / OTP)** or **FIDO2 WebAuthn Hardware Keys** as required primary factors.
   - Disable SMS/Voice OTP fallback for Tier 4 transversal superadmins.
2. **Session Lifetimes:**
   - Reduce JWT session expiration (`jwt_ttl_seconds`) from 12 hours to **2 hours** in production profiles.
   - Enforce mandatory step-up re-authentication when downloading Auditor-General SHA-256 compliance packs (`/exports/ag`).

---

### 2.4 R-08: Transport Layer Security (TLS) & HSTS Hardening

#### A. Nginx Reverse Proxy TLS Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name security.sita.gov.za;

    ssl_certificate /etc/ssl/certs/sita_platform.crt;
    ssl_certificate_key /etc/ssl/private/sita_platform.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HTTP Strict Transport Security (HSTS)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        proxy_pass http://127.0.0.1:8088;
    }
}
```

---

## 3. Priority 2 (P2) Remediation Specifications

### 3.1 R-04: Strict Cross-Origin Resource Sharing (CORS)

Implemented in `app/main.py`:
- In `production`, wildcard origin (`*`) is disabled.
- Permitted origins are pinned to explicit FQDNs:
```python
if settings.environment.lower() in ("dev", "development", "test", "testing"):
    allowed_origins = ["*"]
    allow_credentials = True
else:
    allowed_origins = [
        "http://192.168.101.20:8088",
        "https://security.sita.gov.za"
    ]
    allow_credentials = False
```

---

### 3.2 R-05: Swagger / OpenAPI Schema Protection

In non-development environments, the FastAPI documentation routers are completely deactivated:
```python
if settings.environment.lower() in ("dev", "development", "test", "testing"):
    app = FastAPI(
        title="SITA Security Intelligence Platform API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
else:
    app = FastAPI(
        title="SITA Security Intelligence Platform API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
```

---

### 3.3 R-07: Health & Diagnostic Endpoint Protection

Health monitoring endpoints are bifurcated:
1. **Public Health (`GET /health`):** Minimal response `{ "status": "ok" }` without database pool or internal topology exposure.
2. **Detailed Diagnostic (`GET /health/detailed`):** Restricted to loopback (`127.0.0.1`) and Prometheus monitoring scraper subnets.

---

## 4. Hardening Verification Checklist

| Security Control | Test Command / Method | Acceptance Criteria | Status |
| :--- | :--- | :--- | :---: |
| **JWT Secret Validation** | Start app with `dev` secret in `production` | App exits with `ValueError` | **VERIFIED** |
| **Demo User Lockdown** | Start app with `seed_demo_users_enabled=true` in `production` | App exits with `ValueError` | **VERIFIED** |
| **CORS Wildcard Rejection** | `curl -H "Origin: https://evil.com" /api/v1/public/summary` | Access-Control-Allow-Origin header absent | **VERIFIED** |
| **Swagger UI Lockdown** | `curl -I https://target/docs` in `production` | HTTP 404 Not Found | **VERIFIED** |
| **Security Headers** | `curl -I https://target/api/v1/public/summary` | HSTS, nosniff, DENY headers present | **VERIFIED** |
| **Fail-Closed Tenancy** | Pytest unit test `TestTenantFilter` | Zero records returned for unscoped roles | **VERIFIED** |
