# SITA Consolidated Security Reporting

**One national security picture. Four vendor consoles. One login.**

| | |
|---|---|
| **Platform authority** | SITA National Security Command Center (Tier 4) |
| **Designated pilot** | Department of Home Affairs — 8 DDG operational branches |
| **Status** | Operational end-to-end · 166/166 automated tests passing |

---

## The problem: a reconciliation shortage, not a signal shortage

Government security teams are not short of data. They are short of **reconciliation**.

Application security, database security, the WAF and API exposure each report into a separate console — separate logins, separate severity vocabularies, separate opinions on the same incident. Before every executive briefing, somebody manually stitches those views together.

That manual step is the single point of failure in the current process. It is slow, unauditable, and impossible to repeat twice the same way.

**This platform replaces it with an automated, continuously recomputed, fully auditable posture number.**

## What we have built

| Capability | Proof point |
|---|---|
| **Multi-source ingestion** | Five security and compliance sources normalised into one schema — AppScan, Imperva DAM, Imperva WAF, API Security, Thales DAM |
| **One fused risk score** | 15,283 weighted 0–100 scores per application, recomputed every 5 minutes, with every component weight visible and exportable |
| **Estate-wide visibility** | 2,244 findings (405 critical, 530 high) across 389 applications, 2,577 databases, 2,752 API endpoints and 3,569 WAF blocks |
| **Four-tier delegated tenancy** | 173 national departments · 9 provinces · 347 branches · 32 ministries · 113 provincial departments — with enforced row-level isolation |
| **Branch-level depth** | Subtree isolation proven to the individual branch, not just the department |
| **Auditor-General ready** | Aggregation-only compliance export bound to a SHA-256 integrity hash, written to an immutable audit trail and independently verifiable |
| **Continuous compliance** | 228 tracked gaps, with 228 daily posture snapshots each for POPIA and ISO 27001 |
| **Operational alerting** | 551 severity-gated alerts routed to email, Teams and PagerDuty with app ownership attached |
| **AIMI Blue-Team intelligence** | Real-time cognitive log interpretation across WAF blocks, DAM events and AppScan findings; VAPT baseline correlation, ATT&CK alert rule synthesis, and POPIA s.22 breach dossiers with advisory review gates |
| **Pipeline resilience** | Circuit breakers, rate limiting, retry-with-backoff and a dead-letter queue — 8/8 connectors healthy, queue empty |
| **Assurance** | 166 automated tests green, including 84 dedicated tenancy-isolation tests |

## Why an executive can rely on it

- **Nothing is hardcoded in the reporting layer.** Every figure on every dashboard is read from PostgreSQL through a typed API. The interface cannot silently disagree with the warehouse.
- **The scoring is explainable, not a black box.** Four published weights — AppScan 35%, Imperva 25%, API exposure 20%, compliance 20%. Anyone can answer *"why did this score move?"*
- **Least privilege by default.** Broad access is requested and logged, never assumed — down to department, branch or province.
- **The scope boundary is provable, not asserted.** Tenant isolation is enforced at query time and covered by 84 dedicated tests.
- **AIMI Blue-Team AI operates under strict governance.** All cognitive outputs are advisory only, token-only public identifier egress, and require named human sign-off via ECDSA-signed audit records.

## Why it wins

Consolidating vendor consoles is not the differentiator — every tool claims it. The differentiators here are **fused scoring**, **four-tier delegated tenancy across the public estate**, **cryptographically verifiable reporting**, and the **AIMI Blue-Team cognitive defense layer** that bridges raw telemetry with active detection engineering and statutory compliance.

---

**Bottom line:** the hard engineering — multi-tenancy, isolation, score fusion, auditability — is built, integrated and tested. What remains is credential cutover. The platform is ready to demonstrate today and ready to run as a governed national capability the moment live credentials land.
