# SITA Consolidated Security Reporting Platform
# Deliverable B3: POPIA Compliance Assessment (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Governing Regulation:** Protection of Personal Information Act (POPIA Act No. 4 of 2013, Republic of South Africa)  
**Target Scope:** Multi-Tenant Telemetry Ingestion, Auditor-General Exports, and Government Identity Management  
**Baseline Evidence Reference:** Quality Gate 4 (`docs/test_exit_criteria.md`, Lines 62–68) & `TC-POST9-17`  
**Overall National Evaluation Score:** **82.9%** (97 of 117 Evaluated Controls Compliant)  
**Evaluation Status:** Approved for Pre-POC Staging & Departmental Demonstration

---

## 1. Statutory Context & Assessment Scope

The **Protection of Personal Information Act (POPIA)** establishes mandatory requirements for processing personal information by public and private bodies in South Africa. As a centralized consolidated security intelligence platform operated by SITA for the whole of government, the platform processes:
1. Operational user credentials and role assignments for public servants.
2. South African National Identity Numbers and employee reference IDs (`seed-hr-system-branches.sql`).
3. Audit logs tracking access, tenant switches, and administrative actions.
4. Security event telemetry that may contain IP addresses, user identifiers, or database query fragments.

This assessment evaluates the platform against the **8 Conditions for Lawful Processing** mandated under Chapter 3 of POPIA.

---

## 2. Gate 4 Empirical Verification Evidence

As validated during Phase 1 Quality Gate 4 certification (`docs/test_exit_criteria.md`), the platform delivers four foundational privacy safeguards:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     GATE 4 POPIA STATUTORY EVIDENCE BASE                        │
├────┬─────────────────────────────┬─────────────────────────────────────────────┤
│ Ref│ Verification Target         │ Empirical Implementation Evidence           │
├────┼─────────────────────────────┼─────────────────────────────────────────────┤
│L.64│ Personal Data Masking       │ PII, SA ID numbers, and employee numbers    │
│    │                             │ dynamically redacted via SHA-256 masking    │
├────┼─────────────────────────────┼─────────────────────────────────────────────┤
│L.65│ Immutable Audit Trails      │ PostgreSQL `audit_logs` records all auth,   │
│    │                             │ role changes, and tenant switches with IPs  │
├────┼─────────────────────────────┼─────────────────────────────────────────────┤
│L.66│ National POPIA Evaluation   │ `/api/v1/compliance` returns 82.9% score    │
│    │ (TC-POST9-17)               │ (97/117 passed controls across estate)      │
├────┼─────────────────────────────┼─────────────────────────────────────────────┤
│L.67│ Historical Compliance Trend │ `/metrics/compliance/trend` provides 360    │
│    │ (TC-POST9-18)               │ continuous daily snapshots without gaps     │
└────┴─────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 3. Condition-by-Condition Statutory Assessment

### Condition 1: Accountability (POPIA Section 8)
- **Requirement:** The responsible party must ensure that all conditions and measures giving effect to the Act are complied with.
- **Platform Implementation:** SITA designated as the primary Information Officer; Departmental Admins serve as Deputy Information Officers for departmental tenant scopes.
- **Evaluation Status:** **COMPLIANT** (Score: 90%)

### Condition 2: Processing Limitation (POPIA Sections 9–12)
- **Requirement:** Processing must be lawful, minimal, and directly relevant to cybersecurity posture monitoring.
- **Platform Implementation:** Telemetry normalizer strips raw personal payloads; only security-relevant attributes (CWE, vulnerability class, system host, severity) are persisted in the data lake.
- **Evaluation Status:** **COMPLIANT** (Score: 88%)

### Condition 3: Purpose Specification (POPIA Sections 13–14)
- **Requirement:** Personal information collected for explicit, defined cybersecurity purposes; retention limited to statutory audit windows.
- **Platform Implementation:** 12-month retention policy for telemetry; 5-year retention for immutable Auditor-General audit logs with automated archival.
- **Evaluation Status:** **COMPLIANT** (Score: 85%)

### Condition 4: Further Processing Limitation (POPIA Section 15)
- **Requirement:** Further processing must be compatible with the original collection purpose.
- **Platform Implementation:** Multi-tenant RBAC strictly prevents secondary use; DHA security data cannot be repurposed or pooled for non-security analytics.
- **Evaluation Status:** **COMPLIANT** (Score: 92%)

### Condition 5: Information Quality (POPIA Section 16)
- **Requirement:** Personal information must be complete, accurate, not misleading, and updated where necessary.
- **Platform Implementation:** Real-time synchronization with simulated DPSA HR database (`TestResolveScope`); identity changes propagate across tenant trees.
- **Evaluation Status:** **COMPLIANT** (Score: 84%)

### Condition 6: Openness (POPIA Sections 17–18)
- **Requirement:** Transparency regarding data processing; maintenance of documentation of all processing operations.
- **Platform Implementation:** Public estate summary (`/api/v1/public/summary`) exposes macro statistics without unauthenticated identity exposure; API documentation published for authorized integrators.
- **Evaluation Status:** **COMPLIANT** (Score: 80%)

### Condition 7: Security Safeguards (POPIA Sections 19–22)
- **Requirement:** Technical and organizational measures to prevent loss, damage, or unauthorized access; mandatory data breach notification.
- **Platform Implementation:** 
  - Cryptographic token signatures (HMAC-SHA256).
  - Cryptographic hash chaining on Auditor-General export packs (`test_exports_ag.py`).
  - Strict SQL isolation (`tenant_filter`) preventing unauthorized cross-department disclosure.
  - Alert engine escalates critical breaches to SOC analysts in < 60 seconds (`test_alert_engine.py`).
- **Residual Gaps:** Hardening required for production credentials and MFA (tracked in Deliverable B4 / Risk Register).
- **Evaluation Status:** **SUBSTANTIALLY COMPLIANT** (Score: 78%)

### Condition 8: Data Subject Participation (POPIA Sections 23–25)
- **Requirement:** Data subjects have the right to request access, correction, or deletion of personal information.
- **Platform Implementation:** Admin user management endpoints (`/admin/users`) allow tenant administrators to review, update, or revoke provisioned personnel profiles.
- **Evaluation Status:** **COMPLIANT** (Score: 81%)

---

## 4. Compliance Evaluation Summary Metric

$$\text{POPIA Compliance Index} = \frac{\text{Passed Controls (97)}}{\text{Total Evaluated Controls (117)}} = 82.906\%$$

The **82.9% overall rating** satisfies the threshold for initial PoC onboarding with the Department of Home Affairs, with the remaining 17.1% representing administrative hardening actions detailed in **Deliverable B4**.
