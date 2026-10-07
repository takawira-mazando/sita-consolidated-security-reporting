# DAST / VAPT Assessment Package

## 1. Scope and context

This package is prepared for the remote SITA platform deployment reachable through the provided tunnel endpoints and LAN URLs:

- Frontend: http://192.168.101.20:8088/
- Backend API base: http://192.168.101.20:8000/api/v1
- Health check: http://192.168.101.20:8000/health
- Swagger UI: http://192.168.101.20:8000/docs
- OpenAPI schema: http://192.168.101.20:8000/openapi.json
- VPN/tunnel equivalents: http://localhost:8802/ and http://localhost:8801/

These endpoints are valid from the LAN or from the SSH tunnel; the note about FortiGate policy means direct access on 8088/8000 from outside the LAN is not expected without tunnel or firewall change.

This assessment combines:
- the live exposure posture described in the remote environment,
- the application code and configuration present in this workspace,
- the information available from the provided Okta account profile and AppScan Cloud target context.

> This is a structured assessment package, suitable for a DAST/VAPT review and remediation backlog. It is not a substitute for a full live AppScan scan against the production target in the AppScan Cloud tenant.

---

## 2. Executive summary

The system is a modern FastAPI + React application with a clear API and role-based access model. The codebase includes important security controls, including security headers, CORS restrictions in non-dev environments, and a hardened production path (with Swagger/OpenAPI disabled in production).

However, the current implementation still contains multiple high-risk weaknesses that should be treated as priority issues during DAST/VAPT:

1. Default development credentials and default bootstrap admin password remain in source and can be abused in misconfigured deployments.
2. The app allows demo user seeding and admin bootstrap logic that is unsafe unless explicitly disabled for non-development environments.
3. JWT secret and bootstrap password defaults are weak and will fail in hardened production unless replaced.
4. The identity layer is not protected by MFA in the provided Okta account profile, which increases risk for single-factor account compromise.
5. The app exposes a broad attack surface through readable backend routes and user-role endpoints if deployed in a dev/test profile without the correct environment hardening.

Overall risk rating: High for any non-production or misconfigured deployment; Medium for a properly hardened production deployment with strict identity and network controls.

---

## 3. Scope of testing

### In-scope assets

- Frontend application on 8088 / tunnel 8802
- Backend API on 8000 / tunnel 8801
- Authentication and tenant-scoping endpoints under /api/v1/auth
- Health and diagnostic endpoints under /health and /health/detailed
- OpenAPI/Swagger exposure paths
- AppScan Cloud portal and associated account configuration at https://cloud.appscan.com/

### Out-of-scope or restricted

- Direct remote exploitation from the public internet without approved tunnel or firewall policy
- Host-level exploitation beyond application-layer DAST/VAPT
- Database and infrastructure service enumeration beyond the application’s own endpoints

---

## 4. DAST/VAPT methodology

The assessment is based on a layered approach:

- API surface review against the exposed routes and OpenAPI contract
- Authentication and authorization review
- Source-level inspection of configuration and defaults
- Security-header and CORS evaluation
- Identity control review from the supplied Okta account information
- AppScan Cloud target validation for required secure configuration and scan readiness

---

## 5. Findings

### Finding 1 — Default demo credentials and bootstrap admin credential remain in source code

Severity: Critical

Description:
The application includes seeded demo accounts such as `exec@example.com`, `soc@example.com`, `appsec@example.com`, and `admin@example.com`, with default passwords such as `pass123` and `admin123`. The application also builds a superadmin if the identity table is empty using the configured bootstrap password.

Evidence:
- [backend/app/api/routers/auth.py](backend/app/api/routers/auth.py#L16-L48)
- [backend/app/config.py](backend/app/config.py#L4-L18)

Impact:
If the deployment is running in a shared, staging, or externally reachable non-production environment, these credentials are trivial to exploit. This can lead to unauthorized access, tenant scope escalation, and privilege misuse.

Recommendation:
- Disable seed demo users in production.
- Enforce unique admin credentials and rotate them immediately.
- Remove or disable default credentials from source-controlled configuration.
- Add a startup check that blocks deployment if weak credentials remain.

---

### Finding 2 — Weak default JWT secret and insecure bootstrap password are allowed by default

Severity: High

Description:
The application defines a default JWT secret of `sita-local-dev-secret-change-me` and allows the bootstrap admin password `admin123` unless the environment is explicitly set to a non-dev profile. The config guard only rejects this when the environment is not in dev/test.

Evidence:
- [backend/app/config.py](backend/app/config.py#L4-L18)
- [backend/app/config.py](backend/app/config.py#L35-L48)

Impact:
If the environment is misconfigured or still running in dev/test mode with defaults, an attacker may forge or tamper with tokens and gain access to protected APIs.

Recommendation:
- Use a strong secret with sufficient entropy.
- Require production deployment to reject the default secret, default password, and demo user seeding.
- Rotate JWT signing keys and invalidate active sessions after change.

---

### Finding 3 — Demo user seeding is enabled by default and can expose privileged access paths

Severity: High

Description:
The application seeds demo users automatically in the application lifecycle when `seed_demo_users_enabled` is true. This is explicitly allowed by default in configuration and is extremely useful for local demos but dangerous in any environment that is reachable or shared.

Evidence:
- [backend/app/main.py](backend/app/main.py#L12-L31)
- [backend/app/config.py](backend/app/config.py#L8-L18)

Impact:
An adversary who can reach the deployed app may enumerate or attempt known demo credential sets and exploit default tenancy scopes.

Recommendation:
- Force `seed_demo_users_enabled = false` outside local development.
- Keep demo identities completely isolated from production data.
- Add environment gate checks that fail startup if demo accounts are enabled in anything but local dev.

---

### Finding 4 — CORS is permissive in development mode and potentially unsafe in mixed environments

Severity: Medium

Description:
In dev/test mode, the app sets `allowed_origins = ["*"]` and allows credentials. This is acceptable for local development but not acceptable in a remote or shared deployment environment.

Evidence:
- [backend/app/main.py](backend/app/main.py#L72-L100)

Impact:
If the environment is ever mis-set to dev/test while exposed, browser-based cross-origin attacks become materially easier. Attackers may abuse the app from untrusted origins and attempt credential theft or API misuse.

Recommendation:
- Restrict CORS origins to the exact frontend origin.
- Disable `allow_credentials` unless strictly necessary.
- Remove wildcard origins entirely outside isolated local dev.

---

### Finding 5 — OpenAPI/Swagger exposure is conditional and should be explicitly governed by deployment environment

Severity: Medium

Description:
The application disables Swagger and OpenAPI in non-dev environments, but enables them in dev/test mode. This is a good defensive pattern only if the environment classification is enforced. If the server is deployed in a dev-like configuration, the schema and interactive API may leak internal endpoints and data contracts.

Evidence:
- [backend/app/main.py](backend/app/main.py#L36-L50)

Impact:
Attackers can use the schema to discover endpoints, roles, and request/response structures. This accelerates reconnaissance and abuse of weak endpoints.

Recommendation:
- Keep Swagger disabled in all non-local environments.
- Restrict access to OpenAPI docs to internal IP ranges or authenticated administrators.
- Review generated schemas before production deployment.

---

### Finding 6 — Identity configuration gap: MFA is not enabled in the provided Okta account profile

Severity: Medium

Description:
The provided Okta account profile shows multiple methods disabled: Okta Verify, Google Authenticator, SMS, and Security Question. This suggests the identity account is not yet enforcing second-factor authentication.

Impact:
A single compromised password can yield full account compromise. The application and AppScan Cloud tenant should not rely on password-only authentication.

Recommendation:
- Enforce MFA for all administrator and privileged accounts.
- Require phishing-resistant methods, with Okta Verify or equivalent as preferred.
- Review all AppScan Cloud and platform identities for delegated SSO/MFA enforcement.

---

## 6. Risk rating summary

| Severity | Count | Notes |
| --- | --- | --- |
| Critical | 1 | Default admin/demo credentials and weak access paths |
| High | 2 | Weak JWT/ bootstrap defaults and demo user seeding |
| Medium | 3 | CORS, schema exposure, and MFA gap |

---

## 7. Recommended remediation plan

### Immediate (0–7 days)

1. Rotate the default superadmin password and all demo credentials.
2. Set strong JWT signing secrets in environment variables.
3. Disable demo user seeding in all non-dev deployments.
4. Enforce MFA on Okta-administered identities and AppScan Cloud access.
5. Verify that the production environment is not running in dev/test mode.

### Short-term (1–4 weeks)

1. Restrict CORS to explicit frontend origins.
2. Disable Swagger/OpenAPI in all remote environments.
3. Add deployment guardrails that fail if `admin123` or `pass123` appear in configuration.
4. Review login rate limiting and brute force protections for all auth endpoints.
5. Validate backend headers and TLS policy from the actual tunnel target.

### Ongoing

1. Run AppScan Cloud DAST against the actual deployed frontend and API endpoints.
2. Add automated checks for secret strength and environment hardening.
3. Maintain a policy that local credentials never exist in production package artifacts or source control.
4. Establish periodic identity reviews for privileged accounts.

---

## 8. AppScan Cloud target validation checklist

For the target at https://cloud.appscan.com/, validate the following before production acceptance:

- [ ] AppScan tenant is protected by enforced SSO or robust multi-factor access
- [ ] Scan targets are limited to approved application URLs only
- [ ] Production environment uses HTTPS only and valid HSTS settings
- [ ] No developer credentials or default passwords are present in environment variables or secrets stores
- [ ] Backend docs are disabled outside local development
- [ ] Access to `/health` and `/health/detailed` is restricted to allowed networks
- [ ] API keys and tokens are stored outside source control

---

## 9. Final assessment

The application presents a reasonable baseline security posture for a development-focused codebase, but it is not yet suitable for broad remote or shared deployment without stronger hardening. The primary weaknesses are rooted in default credentials, weak dev defaults, and the application’s ability to run in a non-hardened mode. These are fixable with straightforward deployment guardrails and identity controls.

The highest-priority actions are:

- Remove weak defaults and disable demo credentials in all non-dev environments.
- Enforce MFA on all privileged users and AppScan Cloud identities.
- Restrict the deployment to the intended frontend and backend origins only.
- Verify the actual remote environment is not running with permissive dev settings.

---

## 10. Assessment sign-off

Prepared for: SITA platform / remote DAST/VAPT review
Prepared by: Assessment package based on source review and environment posture
Date: 2026-09-14
Status: Draft for remediation validation and AppScan live-scan follow-up
