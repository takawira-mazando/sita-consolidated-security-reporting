# Risk Register - SITA Platform DAST/VAPT

## Scope
This register maps the identified DAST/VAPT findings to the OWASP Top 10 (2021) and ISO/IEC 27001 controls. It should be used as the working remediation tracker for the remote platform deployment and associated AppScan Cloud review.

## Risk rating scale
- Likelihood: Low / Medium / High
- Impact: Low / Medium / High
- Overall risk: Low / Medium / High / Critical

## Risk register

| ID | Risk description | OWASP Top 10 mapping | ISO 27001 mapping | Likelihood | Impact | Overall risk | Owner | Evidence / source | Recommended treatment | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Default demo and administrative credentials remain available in source code and configuration, enabling trivial account takeover in misconfigured deployments. | A07: Identification and Authentication Failures | A.5.17 Authentication; A.5.15 Access control; A.8.2 Privileged access rights | High | High | Critical | Platform Owner / Security Engineering | [backend/app/api/routers/auth.py](backend/app/api/routers/auth.py#L16-L48), [backend/app/config.py](backend/app/config.py#L4-L18) | Remove all default credentials from source, disable seeded demo identities in production, rotate admin credentials immediately, fail build/deploy if weak defaults are present. | P1 | Open |
| R-02 | Weak default JWT secret and bootstrap admin password can permit token forgery and privilege escalation if the environment is mis-set. | A07: Identification and Authentication Failures | A.5.17 Authentication; A.8.25 Secure development lifecycle; A.8.31 Logging and monitoring | High | High | High | Security Engineering | [backend/app/config.py](backend/app/config.py#L4-L18), [backend/app/config.py](backend/app/config.py#L35-L48) | Replace with strong secrets from a managed secret store, reject default values in production, rotate active JWTs after secret replacement. | P1 | Open |
| R-03 | Demo user seeding is enabled by default and creates privileged access paths in shared or externally reachable environments. | A05: Security Misconfiguration | A.5.8 Access control; A.5.33 Protection of records; A.8.25 Secure development lifecycle | High | High | High | DevOps / Platform Engineering | [backend/app/main.py](backend/app/main.py#L12-L31), [backend/app/config.py](backend/app/config.py#L8-L18) | Set `seed_demo_users_enabled` to false outside local development, block startup if demo mode is enabled in non-dev profiles, isolate demo identities from production data. | P1 | Open |
| R-04 | CORS is permissive in development mode (`allow_origins = ["*"]` with credentials enabled), increasing browser-based attack exposure if the environment is misclassified. | A05: Security Misconfiguration; A01: Broken Access Control | A.5.8 Access control; A.5.14 Access restriction; A.8.23 Web application security | Medium | High | High | Frontend / API Team | [backend/app/main.py](backend/app/main.py#L72-L100) | Restrict CORS to exact trusted origins, disable wildcard origins in shared environments, ensure credentials are not allowed with wildcard configuration. | P2 | Open |
| R-05 | Swagger/OpenAPI documentation may be exposed in dev/test environments, leaking internal API structure and aiding reconnaissance. | A05: Security Misconfiguration | A.8.25 Secure development lifecycle; A.8.29 Security of system services; A.5.14 Access restriction | Medium | Medium | Medium | Security Engineering | [backend/app/main.py](backend/app/main.py#L36-L50) | Disable Swagger/OpenAPI in all non-local environments, restrict docs access to internal networks, review generated schemas before production release. | P2 | Open |
| R-06 | The provided Okta account profile shows MFA methods disabled, creating single-factor compromise risk for privileged identities. | A07: Identification and Authentication Failures | A.5.17 Authentication; A.5.2 Policies for access control; A.8.2 Privileged access rights | Medium | High | High | Identity & Access Management | Okta account profile supplied in the assessment context | Enforce MFA for administrators and AppScan Cloud users; prefer phishing-resistant methods such as Okta Verify; review all privileged access accounts. | P1 | Open |
| R-07 | Exposed health and diagnostic endpoints may leak operational metadata if reachable beyond internal controls. | A05: Security Misconfiguration | A.8.2 Privileged access rights; A.8.31 Logging and monitoring; A.5.14 Access restriction | Medium | Medium | Medium | Platform Engineering | [backend/app/main.py](backend/app/main.py#L102-L108) | Restrict `/health` and `/health/detailed` to trusted networks or internal proxies, ensure detailed health data is not publicly reachable. | P2 | Open |
| R-08 | TLS, HSTS, and header hardening may not be consistently enforced in the actual remote deployment, increasing browser-side confidentiality/integrity risk. | A05: Security Misconfiguration | A.8.27 Secure system architecture and engineering principles; A.8.29 Security of system services | Medium | High | High | Infrastructure / Network Security | [backend/app/main.py](backend/app/main.py#L44-L69) | Ensure HTTPS-only access, enforce HSTS in production, validate frontend and backend headers on the live target, confirm FortiGate policy allows only approved paths. | P1 | Open |

## Treatment priorities

### P1 - Immediate remediation
- Rotate default admin/demo credentials
- Replace weak JWT secret and bootstrap password
- Disable demo user seeding in non-dev environments
- Enforce MFA for all privileged accounts
- Validate production deployment hardening and TLS/HSTS compliance

### P2 - Near-term remediation
- Restrict CORS and remove wildcards
- Restrict or disable Swagger/OpenAPI in remote environments
- Harden health endpoint exposure
- Add deployment guardrails to prevent weak defaults from shipping

## Control mapping summary

### OWASP Top 10 2021
- A01: Broken Access Control — impacted by permissive CORS and access control misconfiguration
- A05: Security Misconfiguration — impacted by demo seeding, docs exposure, health endpoint exposure, and TLS/header misconfiguration
- A07: Identification and Authentication Failures — impacted by weak credentials, weak JWT secret, and missing MFA

### ISO/IEC 27001 relevant domains
- A.5.17 Authentication
- A.5.8 Access control
- A.5.14 Access restriction
- A.8.2 Privileged access rights
- A.8.23 Web application security
- A.8.25 Secure development lifecycle
- A.8.27 Secure system architecture and engineering principles
- A.8.29 Security of system services
- A.8.31 Logging and monitoring

## Owner and review cadence
- Review frequency: Monthly during remediation, then quarterly post-closure
- Primary owner: Security Engineering + Platform Owner
- Risk acceptance authority: CISO / Security Architecture lead for any residual risk after remediation

## Residual risk statement
The current control posture is acceptable for a tightly controlled local demo environment, but it is not yet acceptable for a remote or shared deployment without enforced hardening and MFA. Residual risk should be reduced to Low before production exposure is considered safe.
