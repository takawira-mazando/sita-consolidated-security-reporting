# Understanding the SITA Security Ingestion Pipeline
### A Plain-English Guide to How Security Data Flows from Vendor Tools to Executive Dashboards

---

## 1. The Core Problem: The "Tower of Babel" in Cybersecurity

In any large organization—especially national government departments like Home Affairs, SITA, or SAPS—security is handled by many different commercial security products:

* **Application Scanners** (like **HCL AppScan Cloud**) scan web applications for coding flaws and software bugs.
* **Database Monitors** (like **Thales DAM / Imperva SonarG**) watch every single query against databases storing citizen data.
* **Firewalls & API Gateways** block malicious traffic at the perimeter.
* **Compliance Spreadsheets & Audits** track governance rules.

### The Problem
Each of these tools speaks a completely different technical language:
* Tool A rates a problem as `"High"`, Tool B rates it as `"Severity: 2"`, and Tool C gives it a score of `"7.5"`.
* Tool A calls the target `"AppId"`, Tool B calls it `"Cluster_Name"`, and Tool C calls it `"IP_Address"`.
* One tool outputs complex JSON, another outputs raw database rows, and another sends syslog text.

Without a central system, security teams must manually log into 10 different vendor consoles, download spreadsheets, copy-paste findings into PowerPoint decks, and guess which risks are actually urgent. 

**The SITA Security Ingestion Pipeline is the automated digital postal service, universal translator, and central intelligence brain that solves this problem.**

---

## 2. High-Level Architecture (The Big Picture)

```
[ Security Tools ]               [ The SITA Ingestion Pipeline ]                 [ Dashboards & Action ]
==================               ===============================                 =======================

+--------------------+
|  HCL AppScan Cloud | ----\
|  (App Vulnerabilities)|    \
+--------------------+      \
                             --> [ 1. The Couriers ]     (Connectors fetch data via secure APIs)
+--------------------+      /            |
|  Thales DAM        | ----/             v
|  (Database Activity)|         [ 2. The Translator ]   (Normalises field names, dates & severity)
+--------------------+                   |
                                         v
+--------------------+         [ 3. The Address Tagger ] (Assigns department: e.g., DHA Digital)
|  WAF / Gateways    |                   |
|  (Perimeter Logs)  |                   v
+--------------------+         [ 4. The Threat Tagger ] (Maps to OWASP Top 10 & CWE standards)
                                         |
                                         v
                               [ 5. The Central Vault ] (Saves deduplicated records to Lake)
                                         |
                                         v
                               [ 6. The Alarm Engine ]  (Calculates risk score & alerts SOC)
                                         |
                                         +---> [ Executive Dashboards ]
                                         +---> [ SOC Analyst Alerts ]
                                         +---> [ Automated Compliance Reports ]
```

---

## 3. Step-by-Step Walkthrough in Layman's Terms

### Step 1: The Couriers (Connectors & Secure Collection)
* **What happens:** The platform connects to the external security tools to collect raw activity logs and vulnerability reports.
* **How it works:**
  * For **HCL AppScan Cloud**, our connector connects over encrypted HTTPS, provides secret API keys, gets an approved temporary digital badge (bearer token), and asks: *"What new vulnerabilities have been detected?"*
  * For **Thales DAM**, it connects to the database security gateway to monitor live queries against sensitive citizen databases (such as Cassandra or PostgreSQL).
* **Built-in Resilience:** If a vendor cloud is temporarily slow or down, the pipeline doesn't crash. It uses a **Circuit Breaker** and **Token Bucket** (rate limiter) to pause, retry safely, and protect system memory.

---

### Step 2: The Universal Translator (Data Normalisation)
* **What happens:** Raw logs from different vendors are translated into one clean, standard SITA format.
* **Every single record is given the same standard attributes:**
  * **Who:** What application, database, or server is affected?
  * **What:** What kind of vulnerability or suspicious event occurred?
  * **How Bad:** Is it Critical, High, Medium, or Low?
  * **When:** When was it first discovered, and when was it last confirmed?
* **Data Sanitisation:** In technical software, messy raw data often contains missing values or bad numbers (`NaN` or blank dates). The translator scrubs these clean so they never corrupt the database.

---

### Step 3: The Address Tagger (Multi-Tenancy Attribution)
* **What happens:** The system answers the vital question: *"Whose problem is this?"*
* **Why this is critical for South Africa:**
  * SITA serves over 170 national departments and 9 provincial administrations.
  * A security flaw in the **Department of Home Affairs (DHA) Digital Portal** must belong to DHA, not the Department of Health or Transport.
  * Even inside DHA, it tags the exact branch: **DHA Civic Services**, **DHA Immigration**, **DHA Operations**, or **DHA Digital**.
* **Zero Cross-Leakage:** Strict database rules ensure that a DHA administrator can only see DHA security data, while the National SITA CISO has a master view across all departments.

---

### Step 4: The Threat Tagger (OWASP Top 10 & CWE Classification)
* **What happens:** Every issue is categorized against international security standards (such as **OWASP Top 10** and **CWE**).
* **Examples:**
  * If AppScan finds a login page allowing users to guess passwords, it is tagged as **OWASP A01 (Broken Access Control)**.
  * If AppScan finds an outdated SSL certificate, it is tagged as **OWASP A02 (Cryptographic Failure)**.
  * If Thales DAM sees an unusual SQL database extraction attempt, it is tagged as **OWASP A03 (Injection)**.
* **Why it matters:** Government leadership can see high-level trends: *"65% of our vulnerabilities across national portals are Cryptographic Failures—we need to enforce modern TLS 1.3 across all departments."*

---

### Step 5: The Central Vault (Lake Writer & Smart Deduplication)
* **What happens:** Standardized, tagged findings are stored in the PostgreSQL Security Data Lake (`warehouse.findings`).
* **Smart Deduplication ("Upsert"):**
  * If AppScan runs every hour and flags the *same* missing security header 24 times a day, you don't want 24 duplicate tickets cluttering the screen.
  * The pipeline recognizes it has seen this issue before. Instead of creating a duplicate, it simply updates the record:
    * *"Confirmed still open at 08:30 today (Occurrence count: 24)."*
  * When the developer finally fixes the flaw, the next scan automatically marks it as **Resolved**.

---

### Step 6: The Alarm Engine (Risk Scoring & Alert Dispatch)
* **What happens:** The system calculates the risk score and notifies the right people.
* **Risk Engine:** Instead of just looking at raw severity, it evaluates context:
  * A flaw on an internal offline printer is low risk.
  * A flaw on the public **DHA Passport System** holding millions of citizen records is **Critical**.
* **Alert Dispatch:**
  * **Informational issues:** Sent quietly to routine weekly developer backlogs.
  * **Critical threats:** Instant alerts dispatched via automated webhooks, MS Teams, or SMS to the SOC (Security Operations Center) on-duty engineer.

---

## 4. Real-World Example: Tracing a Real Vulnerability

Here is an actual issue pulled live from HCL AppScan Cloud into the platform:

```
[ 1. Raw AppScan Cloud Finding ]
      ID:       16650518-9e9f-f111-9b33-000d3ae276b2
      Issue:    "Encryption Not Enforced"
      URL:      https://demo.testfire.net/
      Raw Sev:  2 (Medium)
      CVSS:     5.4
          |
          v
[ 2. Translated & Standardised ]
      Standard ID:   ASC-16650518-9e9f-f111-9b33-000d3ae276b2
      Title:         "AppScan: Encryption Not Enforced"
      Severity:      "medium" (Normalised from vendor code)
          |
          v
[ 3. Address & Department Assigned ]
      Department:    "home-affairs-digital" (Department of Home Affairs)
      Branch:        "dha-digital"
      Tier:          Tier 3 (National Public Entity)
          |
          v
[ 4. Security Standard Classification ]
      CWE:           CWE-311 (Missing Encryption of Sensitive Data)
      OWASP:         A02:2021 (Cryptographic Failures)
          |
          v
[ 5. Stored & Evaluated ]
      Action:        Upserted into SITA Security Data Lake
      Visibility:    Visible instantly on the DHA Security Officer Dashboard
                     and the National Executive Scorecard.
```

---

## 5. The Cognitive Layer: AIMI Blue-Team & VAPT Log Intelligence

Once raw logs are safely ingested and normalised in the Security Data Lake, the **AIMI Blue-Team Intelligence Layer** transforms raw events into actionable defense capabilities:

```
[ Normalized Lake Telemetry ]
  • Imperva WAF blocks (SQLi, BOLA, XSS, Path Traversal)
  • Thales / Imperva DAM queries (Cassandra, PostgreSQL)
  • HCL AppScan DAST/SAST findings (CWE mappings)
  • Operational alerts (551 severity-gated events)
                 │
                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │         AIMI Blue-Team Cognitive Reasoning Engine           │
  │                                                             │
  │  1. VAPT Vector Correlation (DAST/SAST vs WAF blocks)       │
  │  2. MITRE ATT&CK Mapping & Rule Authoring (AVP-2)          │
  │  3. Threat Campaign Attribution & OTX Feeds (AVP-3)         │
  │  4. Statutory POPIA s.22 Breach Threshold Analysis (AVP-5)  │
  │  5. Entity Correlation Graph & Blast Radius (AVP-6)         │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
  ┌──────────────────────────────┐┌──────────────────────────────┐
  │   SOC / AppSec Forensics     ││  Compliance & Legal Impact   │
  │ • Hostile payload payloads   ││ • POPIA s.22 exposure risk   │
  │ • Unique attacker IP traces  ││ • ISO 27001 control state    │
  │ • Sigma rule proposals diff  ││ • Signed AG audit packet     │
  └──────────────────────────────┘└──────────────────────────────┘
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │    Executive Risk Posture    │
                  │ • Perimeter resilience grade │
                  │ • Fused risk score delta     │
                  │ • Advisory governance gate   │
                  └──────────────────────────────┘
```

### The 7 Core Blue-Team Defense Capabilities

The platform integrates the verified recommendations of the **Blue-Team AI Capability Assessment**:

1. **VAPT & Ingested Log Analysis:** Correlates real-time WAF blocks and database logs against the 13 verified VAPT baseline vectors (SQL Injection, Cross-Site Scripting, Path Traversal, Credential Brute-Force, Deserialization, and OpenAPI Reconnaissance).
2. **Detection Content Generation (AVP-2):** Synthesizes defensive Sigma and WAF inspection rules mapped directly to MITRE ATT&CK techniques, generating reviewable git diffs for `alert_rules.yaml`.
3. **Internal Entity-Correlation Graph (AVP-6):** In-cluster, tenant-safe self-joins between findings, alerts, API endpoints, and database inventories to determine application blast radiuses without cross-tenant leakage.
4. **Context-Aware Alert Prioritisation:** Replaces raw severity reordering with multi-dimensional ranking incorporating asset tier, threat context, peer group deviation, and confidence.
5. **POPIA s.22 Breach Dossiers & Investigation (AVP-5):** Compiles evidence packets for the Information Regulator with an immutable timeline of indicators.
6. **Governed Security Reporting & Auditing:** Deterministic metrics backed by ECDSA-signed cryptographic attestations (`app.security_pki`), anti-drift tested against reporting rot.
7. **Threat Intelligence Enrichment (AVP-3):** Enriches observed indicators with CVE, MITRE ATT&CK, and AlienVault OTX pulse intelligence using **token-only egress** (public identifiers only — no tenant data ever crosses the boundary).

### The Human-Validation Clause & Governance Gates
All AIMI Blue-Team outputs operate under strict governance:
* **Advisory Only:** No autonomous iptables mutation or code deployment occurs without a human analyst sign-off.
* **Hermes Review Gate Standard:** Every AI deduction carries a 3-layer QA envelope (`layer_1` deterministic validation, `layer_2` cross-source verification, `layer_3` human review gate recommendation).
* **Cryptographic Traceability:** Every validated action is recorded against a named decider and signed into the ECDSA audit trail.

---

## 6. Summary of Key Benefits

| Benefit | Before (Manual / Siloed) | With SITA Ingestion Pipeline |
| :--- | :--- | :--- |
| **Speed** | Weekly/Monthly manual spreadsheet exports | **Real-time & Automated** (every 5 minutes or on demand) |
| **Accuracy** | Human copy-paste errors, mismatched columns | **100% Validated** with automated schema checks |
| **Duplication** | Duplicate tickets created on every new scan | **Smart Upserting** updates existing records seamlessly |
| **Multi-Tenancy** | Dangerous risk of sharing other department logs | **Strict Isolation** per Department, Ministry, and Branch |
| **Actionability** | Overwhelmed by thousands of disconnected alerts | **Contextual Risk Scoring** prioritizes what matters most |
| **Blue-Team AI** | Disconnected logs with no automated threat context | **Cognitive VAPT Interpretation** + ATT&CK detection rule authoring |

---

## 7. How to Run & Verify the Pipeline

The pipeline can be run or tested at any time:

```powershell
# In c:\sita-platform\backend

# 1. Run live simulation demonstrating AppScan + Thales DAM ingestion
python -m scripts.demo_pull_logs --count 10

# 2. Run full AppScan Cloud production connector (Dry-run mode)
python -m scripts.ingest_appscan_logs --dry-run -v

# 3. Run automated tests for Ingestion, VAPT, and Blue-Team intelligence
pytest backend/tests/test_vapt_log_intel.py backend/tests/test_intel_layer.py

# 4. View live dashboards & Blue-Team AI Workspace
# Open http://localhost:3000 in your browser to view findings and the AI Intel workspace.
```
