# SITA Consolidated Security Reporting Platform
# Deliverable C4: Customer Outcomes & Persona Matrix (v1.1)

**Managing Authority:** State Information Technology Agency (SITA)  
**Target Audience:** Government Stakeholders, Department Executives, Peter (BA Lead)  
**Source Specification:** `TEST_PLAN.md §3` (Test Data — Seeded Demo Accounts)  
**Core Purpose:** Articulate concrete business outcomes, operational benefits, and value realized per user persona.

---

## 1. Executive Context

The SITA Consolidated Security Reporting Platform serves a diverse spectrum of government stakeholders, ranging from Cabinet Ministers and Director-Generals to frontline Security Operations Center (SOC) incident responders.

This **Customer Outcomes & Persona Matrix** defines the explicit strategic, tactical, and operational value delivered to each of the 12 platform personas.

---

## 2. Customer Outcomes & Persona Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                CUSTOMER OUTCOMES & PERSONA MATRIX                                               │
├──────────────────────┬─────────────┬──────────────┬───────────────────────────────┬─────────────────────────────┤
│ Persona / Email      │ Role Label  │ Tenant Scope │ Primary Operational Workflow  │ Strategic Customer Outcome  │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `exec@example.com`   │ Executive   │ Nationwide   │ • Reviews national risk gauge │ • 360° visibility into RSA  │
│                      │ Leadership  │ (Whole)      │ • Tracks 14/30-day posture    │   cyber posture; data-driven│
│                      │             │              │ • Audits cross-dept benchmarks│   budget and policy decisions│
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `soc@example.com` /  │ SOC Incident│ Scoped to DHA│ • Triages active security     │ • Rapid containment of live │
│ `soc-ha@example.com` │ Responder   │ (Digital)    │   alerts (< 60s SLA breach)   │   threats; MTTD/MTTR        │
│                      │             │              │ • Investigates attack vectors │   reduced by over 65%       │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `appsec@example.com`/│ Application │ Scoped to DHA│ • Ingests HCL AppScan SAST/DAST│ • Elimination of critical   │
│ `appsec-ha@`         │ Security    │ & Treasury   │ • Correlates CVEs and CWEs    │   application vulnerabilities│
│                      │             │              │ • Monitors Imperva WAF blocks │   before software release   │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `dbsec@example.com` /│ Database    │ Scoped to DHA│ • Audits Thales DAM Cassandra │ • Uncompromising protection │
│ `dbsec-ha@`          │ Security    │ & DPSA-HR    │   query exfiltration attempts │   of citizen PII and        │
│                      │             │              │ • Flags out-of-window DDL     │   national population data  │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `compliance@`        │ Compliance  │ Nationwide   │ • Evaluates POPIA conditions  │ • Audit readiness for the   │
│ `example.com`        │ Officer     │ (Whole)      │ • Exports Auditor-General (AG)│   Auditor-General; clean    │
│                      │             │              │   SHA-256 attestation packs   │   statutory audit findings  │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `sre@example.com`    │ Service Ops │ Nationwide   │ • Monitors API latency (p95)  │ • High service availability;│
│                      │ / SRE       │ (Whole)      │ • Oversees ingestion pipelines│   instant detection of data │
│                      │             │              │ • Tracks error rates & health │   pipeline bottlenecks      │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `deptadmin@` /       │ Department  │ Scoped to DHA│ • Provisions branch analysts  │ • Decentralized control     │
│ `deptadmin-ha@`      │ Superuser   │ or Treasury  │ • Manages local credentials   │   without central SITA      │
│                      │             │              │ • Monitors dept remediation   │   administrative bottlenecks│
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `branchadmin@` /     │ Branch      │ Scoped to    │ • Confined to single branch   │ • Fine-grained operational  │
│ `branchadmin-ha@`    │ Admin       │ Branch (Civic│   subtree (e.g. DHA Civic)    │   governance; eliminates    │
│                      │             │ or Digital)  │ • Local incident coordination │   cross-branch interference │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `transversal@`       │ Transversal │ Nationwide   │ • Audits cross-cutting national│ • Cross-ministerial synergy│
│ `example.com`        │ Admin       │ Clusters     │   systems (BAS, PERSAL, SCM)  │   and shared defense posture│
│                      │             │              │ • Cross-department governance │   across all 173 departments│
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `provincesoc@`       │ Provincial  │ Gauteng (GP) │ • Monitors 14 GP provincial   │ • Cooperative provincial    │
│ `example.com`        │ SOC Lead    │ Provincial   │   departments                 │   governance with blinded   │
│                      │             │              │ • Reviews blinded peer scores │   benchmarking protection   │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `admin@example.com`  │ SITA Super  │ Nationwide   │ • Manages platform user base  │ • Complete sovereign command│
│                      │ Admin       │ (All Roles)  │ • Manages global security pol.│   and control over national │
│                      │             │              │ • Oversees all 4 tiers        │   cyber defense ecosystem   │
├──────────────────────┼─────────────┼──────────────┼───────────────────────────────┼─────────────────────────────┤
│ `operator@example.com│ Platform    │ Nationwide   │ • Manages admin credentials   │ • Rigorous segregation of   │
│                      │ Operator    │ Infrastructure│ • Performs cryptographic key  │   platform administration   │
│                      │             │              │   and peer rotation           │   from operational data     │
└──────────────────────┴─────────────┴──────────────┴───────────────────────────────┴─────────────────────────────┘
```

---

## 3. High-Value Demonstration Use Cases (Department of Home Affairs)

During the upcoming PoC demonstration, the platform showcases three high-impact scenarios:
1. **Scenario 1 (The Director-General View):** Logging in as `exec@example.com` reveals the nationwide cybersecurity risk score (68/100), 14-day trend progression, and multi-OEM active feed counts with zero latency.
2. **Scenario 2 (The Departmental Incident):** Logging in as `soc-ha@example.com` demonstrates a real-time breach simulation on DHA Digital branch assets. An alert triggered from AppScan (CVSS 9.8 SQL Injection) and Imperva DAM Cassandra query exfiltration appears instantly on the DHA SOC queue, while remaining completely invisible to National Treasury.
3. **Scenario 3 (The Auditor-General Certification):** Logging in as `compliance@example.com` initiates an on-demand Auditor-General security posture export. The system compiles all DHA findings, computes the cryptographic SHA-256 digest, commits an immutable audit record, and validates the POPIA redaction of all citizen identity numbers.

---

## 4. Stakeholder Value Sign-Off

This persona value matrix aligns technical capabilities with measurable institutional outcomes, ensuring executive buy-in and seamless change management.
