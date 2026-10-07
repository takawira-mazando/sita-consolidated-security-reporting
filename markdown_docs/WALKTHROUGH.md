# SITA Platform — Live Demonstration Walkthrough Guide

> **Target Audience**: Executive Stakeholders, DHA Tenant Leadership, SITA Enterprise Architecture & Security Teams  
> **Platform Version**: Production Demo Release (Vite + React 18 / FastAPI / PostgreSQL)  
> **Base URL**: [http://localhost:3000](http://localhost:3000)  
> **Backend API**: [http://localhost:8000](http://localhost:8000)  

---

## 🏛️ Executive Architecture & Context

The **SITA Consolidated Security Reporting Platform** is designed for the **State Information Technology Agency (SITA)** as the platform managing authority and client, securing the whole of South African Government across:
- **173 National Departments**
- **9 Provincial Administrations** (113 provincial departments)
- **347 Operational DDG Branches**

The **Department of Home Affairs (DHA)** (`home-affairs-digital`) is the designated **Proof of Concept (PoC) Testbed**, featuring **8 real operational DDG branches** and live ingested telemetry from **HCL AppScan Cloud** and **Thales DAM**.

```
🇿🇦 TIER 4 · SITA NATIONAL SECURITY COMMAND CENTER (admin@, operator@)
   │ Transversal authority across all 173 Departments & 9 Provinces
   │ Global downward superadmin provisioning cascade
   ▼
🏛️ TIER 3 · NATIONAL ESTATE (transversal-admin, exec@, compliance@, sre@)
   │ Whole-of-government fused risk score (0–100) & AG compliance export
   ▼
🏢 TIER 2 · DEPARTMENT & PROVINCIAL TIER (deptadmin-ha@, provincesoc@)
   │ Dept of Home Affairs (DHA) isolation & provincial peer blinding
   ▼
📍 TIER 1 · OPERATIONAL BRANCH TIER (branchadmin-ha@, soc-ha@, appsec-ha@, dbsec-ha@)
   │ Granular DDG units: dha-civic, dha-digital, dha-immigration, etc.
   │ Live HCL AppScan vulnerabilities & Thales DAM Cassandra query monitoring
```

---

## 🎬 Live Demonstration Script: 5 Key Stages

### Stage 1: SITA Command Center & Transversal Superadmin Authority
* **Objective**: Demonstrate that SITA holds overarching transversal authority to monitor nationwide threat posture and provision administrators across all tiers.
1. **Navigate to**: [http://localhost:3000/login](http://localhost:3000/login)
2. **Authenticate as SITA Superadmin**:
   - **Email**: `admin@example.com`
   - **Password**: `admin123`
3. **Verify Dashboard Capabilities**:
   - Notice the **🇿🇦 SITA Command Center** badge and navigation pill in the top header.
   - Click between the tier pills: **🇿🇦 SITA Command Center**, **🏛️ National**, **🏢 Department**, **📍 Branch**.
   - Navigate to `/sita/admin` (or `/admin/users`):
     - View all 20 accounts across all 4 tiers.
     - Click **Create User**: demonstrate that SITA can provision **Tier 3 Transversal Admins**, **Tier 2 Department Admins**, and **Tier 1 Branch Admins** with zero elevation restrictions.
4. **Inspect National Compliance**:
   - Navigate to `/national/compliance`:
     - Review the **POPIA Compliance Score** (82.9%, 97/117 controls passed).
     - Inspect the **Historical Compliance Trend** showing **360 historical snapshots** over time.

---

### Stage 2: Auditor-General (AG) Cryptographic Attestation Export
* **Objective**: Demonstrate the Auditor-General export with cryptographic SHA-256 hash chains, POPIA PII stripping, and tamper-evident audit logging.
1. **Action**:
   - While in Compliance view (`/national/compliance` or `/dept/compliance`), click **Export AG Attestation Report** (or call `GET /api/v1/exports/ag-compliance`).
2. **Verify Output**:
   - Notice that raw database records and employee PII are completely stripped.
   - The export payload includes an immutable **SHA-256 Hash Chain** bound to the requesting actor, tenant scope, and exact timestamp.
   - Verification endpoint (`GET /api/v1/exports/ag-compliance/verify/{hash}`) returns `{"valid": true}`, proving audit integrity.

---

### Stage 3: Department of Home Affairs (DHA) Isolation & Scoped Superadmin
* **Objective**: Demonstrate that DHA Department Superadmin has comprehensive oversight across all 8 DHA branches, but cannot view or administer other departments (e.g. Treasury, DPSA, SAPS).
1. **Switch User / Log In**:
   - Click **Sign Out** or return to [http://localhost:3000/login](http://localhost:3000/login).
   - Select the **🏛️ Department of Home Affairs Demo Persona** chip: **Dept Admin (`deptadmin-ha@example.com`)**.
   - Password: `pass123`.
2. **Verify Tenancy Scope**:
   - The header displays the **Department of Home Affairs** badge.
   - Available tiers are restricted strictly to **🏢 Department** and **📍 Branch** (Tier 4 SITA Command Center and Tier 3 National Estate pills are hidden).
3. **Verify User Management Ceilings**:
   - Navigate to **User Administration** (`/dept/admin` or `/users`):
     - Total users visible drops from 20 down to **6** (strictly DHA personnel). Zero non-DHA accounts leak into view.
     - Click **Add User**: The role dropdown enforces the anti-elevation ceiling. The DHA Dept Admin can provision `branch-admin` and operational roles (`soc`, `appsec`, `dbsec`), but **cannot** provision `admin`, `operator`, or `transversal-admin`.

---

### Stage 4: Real HCL AppScan Vulnerabilities in Action (AppSec Dashboard)
* **Objective**: Show live, normalized HCL AppScan findings loaded through the API for Home Affairs software assets.
1. **Log in as DHA AppSec Engineer**:
   - Select **AppSec Specialist (`appsec-ha@example.com`)** / `pass123`.
2. **Navigate to AppSec View**: `/dept/appsec` (or `/branch/appsec`).
3. **Verify Real Telemetry**:
   - **Total Findings**: 50 live findings loaded via `/api/v1/findings`.
   - **Severity Breakdown**:
     - Critical: SQL Injection on `/bank/showtransactions` (CVSS 9.8 / CWE-89).
     - High: Reflected Cross-Site Scripting (XSS) on `/search.jsp` and `/sendfeedback` (CVSS 7.1 / CWE-79).
     - High: Integer Overflow / Insecure Design on `/bank/dotransfer` (CVSS 7.5 / CWE-190).
   - **OEM Attribution**: Verified with `<OemTag source="appscan" />`.
   - **Tenant Scoping**: All 50 findings belong strictly to DHA applications (`home-affairs-digital`).

---

### Stage 5: Thales DAM Database Activity Monitoring & SOC Alert Queue
* **Objective**: Demonstrate Thales DAM Cassandra cluster monitoring and real-time alert triage in the SOC queue.
1. **Log in as DHA DB Security Lead**:
   - Select **DB Security (`dbsec-ha@example.com`)** / `pass123`.
2. **Inspect DB Security Dashboard**: `/dept/dbsec`:
   - **Monitored Databases**: 66 database instances visible under DHA scope (`AUDIT_KEYSPACE`, `FLORENCE_CASSANDRA`, `USER_KEYSPACE`).
   - **Security Violations**: Out-of-window DDL `TRUNCATE` operations, unauthorized CQL spikes, and privileged account access.
3. **Log in as DHA SOC Analyst**:
   - Select **SOC Analyst (`soc-ha@example.com`)** / `pass123`.
4. **Inspect SOC Alert Queue**: `/dept/soc`:
   - 47 active security alerts correlated across AppScan and Thales DAM.
   - Status triage: transition alerts between **New**, **Acknowledged**, **Investigating**, and **Resolved**.

---

## 📊 Demo Verification Matrix

| Step | Persona | Target Route | Expected Result | Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `admin@example.com` | `/sita/admin` | Unrestricted 4-tier navigation & 20 users visible | ✅ Verified |
| **2** | `transversal@example.com`| `/national/exec` | Whole-of-government fused risk score (0–100) | ✅ Verified |
| **3** | `compliance@example.com` | `/national/compliance` | AG export with SHA-256 hash & 360-pt trend | ✅ Verified |
| **4** | `deptadmin-ha@example.com` | `/dept/admin` | Strictly 6 DHA users; anti-elevation ceiling enforced | ✅ Verified |
| **5** | `appsec-ha@example.com` | `/dept/appsec` | 50 real AppScan findings (SQLi, XSS, Overflow) | ✅ Verified |
| **6** | `dbsec-ha@example.com` | `/dept/dbsec` | 66 Thales DAM monitored DBs & CQL violation logs | ✅ Verified |
| **7** | `soc-ha@example.com` | `/dept/soc` | 47 live alerts scoped strictly to DHA assets | ✅ Verified |

---

## 🚀 Quick Launch Links

- **Home & Architecture Diagram**: [http://localhost:3000/#tenancy](http://localhost:3000/#tenancy)
- **Interactive Architecture Viewer**: Open [`architecture.html`](file:///c:/sita-platform/architecture.html) in browser
- **Login Modal**: [http://localhost:3000/login](http://localhost:3000/login)
- **FastAPI OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
