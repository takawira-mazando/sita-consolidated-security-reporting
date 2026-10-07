# SITA Consolidated Security Reporting Platform
# Deliverable C3: CISO 4-Tier Role-Based Access Control Architecture (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Target Executive:** Chief Information Security Officer (CISO) & National Cyber Security Advisory  
**Cross-Reference Document:** `backend/test_api_comprehensive.py` & `backend/app/tenant.py`  
**Security Standard:** Principle of Least Privilege, Need-to-Know Segregation, and Non-Repudiation

---

## 1. Executive Summary & Four-Tier Hierarchy

The South African Government cybersecurity estate requires a governance model that accommodates national oversight while preserving institutional autonomy and operational confidentiality.

The platform formalizes a **4-Tier Hierarchical Role-Based Access Control (RBAC) Architecture**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│              TIER 4: SITA NATIONAL COMMAND CENTER                       │
│    • SITA Superadmin (`admin@`)     • Transversal Admin (`transversal@`)│
│    • Platform Operator (`operator@`)• Executive Leadership (`exec@`)    │
│    Scope: Whole Estate (Nationwide) | 173 Departments | 9 Provinces     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TIER 3: PROVINCIAL COMMAND & COORDINATION                  │
│    • Provincial SOC Lead (`provincesoc@`) • Prov Admin (`provdeptadmin@`)│
│    Scope: Designated Province (e.g. GP - 14 Provincial Departments)     │
│    Feature: Blinded Provincial Peer Benchmarking                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TIER 2: INSTITUTIONAL / DEPARTMENTAL ADMIN                 │
│    • Department Administrator (`deptadmin-ha@`)                         │
│    Scope: Single Department Subtree (e.g. Department of Home Affairs)   │
│    Enforcement: Anti-Elevation Ceiling (Cannot manage Tier 3/4)         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TIER 1: OPERATIONAL SPECIALTY & BRANCH EXECUTION           │
│    • SOC Analyst (`soc-ha@`)        • AppSec Analyst (`appsec-ha@`)     │
│    • DB Security (`dbsec-ha@`)      • Branch Admin (`branchadmin-ha@`)  │
│    Scope: Operational queues strictly scoped to departmental assets     │
│    Enforcement: Zero Cross-Tenant Leakage Guarantee                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Tier Specifications & Verification Evidence

### Tier 4: SITA National Command Center & Transversal Administration
- **Personas:**
  - `admin@example.com` (SITA Superadmin — Holds `ALL_ROLES`)
  - `transversal@example.com` (SITA Transversal Admin)
  - `operator@example.com` (Managed Service Platform Operator)
  - `exec@example.com` (National Cybersecurity Executive)
- **Tenancy Scope:** Nationwide (`department_ids: []`, `province_ids: []`). Empty scope indicates whole-of-government coverage.
- **Key Capabilities:**
  - Complete visibility across all 173 national departments and 9 provinces.
  - Estate-wide risk posture aggregation, SLA escalation oversight, and Auditor-General export certification.
  - User administration: Unrestricted authority to provision Tier 2 and Tier 3 departmental administrators.
  - Platform Operator isolation: The `operator` account is restricted to creator rotation and peer admin lifecycle, preventing unauthorized telemetry tampering.
- **Empirical Test Evidence:**
  - `POST9-07`: SITA superadmin login verified with nationwide scope.
  - `POST9-08`: Transversal admin login verified across all ministerial clusters.
  - `POST9-19`: Unrestricted user administration verified via `GET /admin/users` (20 accounts accessible).

### Tier 3: Provincial Command & Coordination
- **Personas:**
  - `provincesoc@example.com` (Provincial SOC Lead — Gauteng)
  - `provdeptadmin@example.com` (Provincial Department Administrator)
- **Tenancy Scope:** Single Province (`province_ids: ["gp"]`). Automatically expands to all 14 provincial departments under that province.
- **Key Capabilities:**
  - Unified oversight across all provincial health, education, transport, and treasury entities.
  - **Blinded Peer Benchmarking:** The provincial SOC lead observes Gauteng's exact posture metrics, while all other provinces are anonymized with cryptographic pseudonyms to foster cooperative governance without competitive exposure.
- **Empirical Test Evidence:**
  - `TC-RBAC-05`: Gauteng benchmark scores unblinded; peer provinces blinded.
  - `API-07 & API-08`: Allowed scope override within GP; blocked from Western Cape (`wc`).

### Tier 2: Institutional / Departmental Administration
- **Personas:**
  - `deptadmin-ha@example.com` (Department Admin — Department of Home Affairs)
  - `deptadmin@example.com` (Department Admin — National Treasury)
- **Tenancy Scope:** Single Department (`department_ids: ["home-affairs-digital"]`) encompassing all 8 departmental branches (`dha-civic`, `dha-digital`, `dha-immigration`, `dha-ops`, etc.).
- **Key Capabilities:**
  - User provisioning and credential management strictly confined to departmental personnel (6 DHA users).
  - Branch assignment and operational access granting (SOC, AppSec, DB Sec).
  - **Anti-Elevation Security Ceiling:** Cannot assign superadmin roles, cannot grant transversal privileges, and cannot create users outside their assigned department.
- **Empirical Test Evidence:**
  - `POST9-09`: DHA dept admin strictly scoped to DHA subtree.
  - `POST9-20`: Scoped user admin ceiling verified; 0 non-DHA users visible in `/admin/users`.

### Tier 1: Operational Specialty & Branch Execution
- **Personas:**
  - `soc-ha@example.com` (SOC Analyst — Incident Response)
  - `appsec-ha@example.com` (AppSec Specialist — HCL AppScan & WAF)
  - `dbsec-ha@example.com` (Database Security Lead — Thales DAM & Cassandra)
  - `branchadmin-ha@example.com` (Branch Administrator — DHA Civic Services)
- **Tenancy Scope:** Confined to assigned departmental branch and specialty queues.
- **Key Capabilities:**
  - SOC Analyst: Triage active security alerts, investigate incidents, manage remediation lifecycles.
  - AppSec Analyst: Scan review, CWE analysis, CVSS scoring, Imperva WAF rule tuning.
  - DB Security: Database query anomaly investigation, out-of-window DDL detection, Cassandra keyspace monitoring.
  - **Zero-Leakage Enforcement:** All queries append `WHERE department_id IN ('home-affairs-digital')`.
- **Empirical Test Evidence:**
  - `POST9-10`, `POST9-11`, `POST9-12`: Operational role authentication verified.
  - `POST9-21`: Zero cross-tenant data leakage verified (0 non-DHA records returned).

---

## 3. Delegation Matrix & Anti-Elevation Rules

The delegation cascade enforces strict downward-only authorization:

| Caller Role | Caller Tier | Maximum Grantable Tier | Permitted Grantable Roles | Tenancy Constraint |
| :--- | :---: | :---: | :--- | :--- |
| `operator` | 4+ | Tier 4 | `admin`, `operator` | Nationwide |
| `admin` | Tier 4 | Tier 3 / Tier 2 | `dept-admin`, `province-dept-admin`, `branch-admin`, `exec`, `compliance`, `sre` | Nationwide or Scoped |
| `transversal-admin`| Tier 4 | Tier 2 | `dept-admin`, `branch-admin`, `soc`, `appsec`, `dbsec` | Multi-Department |
| `dept-admin` | Tier 2 | Tier 1 | `branch-admin`, `soc`, `appsec`, `dbsec` | Strictly Caller's Dept |
| `branch-admin` | Tier 1 | Tier 1 | `soc`, `appsec`, `dbsec` | Strictly Caller's Branch |
| Operational Roles | Tier 1 | None (0) | Cannot create or manage users | N/A |

---

## 4. CISO Governance Certification

This 4-tier model has been validated through automated integration testing, unit regression, and live zero-leakage security audits. It is recommended for full institutional adoption across all participating government departments.
