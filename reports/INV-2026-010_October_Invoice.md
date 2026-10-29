===============================================================================
                         BANTU INFOTECH (B.iT)
                   Pretoria, Gauteng, South Africa
                          TAX INVOICE
===============================================================================

**Invoice No:**       INV-2026-010  
**Date Issued:**      22 October 2026  
**Period:**           23 September 2026 – 22 October 2026  
**Prepared By:**      Takawira Mazando  
**Email:**            takawira.mazando@entailabs.com  
**Contact:**          0672 319 200  

### BILL TO:
**Attn:** Koketso Molelemane (Human Capital Manager)  
**Company:** Hosi Technologies (Pty) Ltd  
**Registration:** 2010/015030/07  
**Division:** Hosi Academy LMS Division  
**Address:** Block A, 2nd Floor, The Pivot, Fourways, Johannesburg  
**Email:** koketso@hosi.co.za  
**Contact:** admin@hosi.co.za  

---

**PROJECT:** SITA Security Intelligence Platform (Addendum B, AppScan SAST/DAST Remediation, AIMI AI Layer) & FMCG Enterprise Ingestion, Data Lake & Predictive Analytics Backend Architecture  
**CONTRACT:** Monthly Retainer under Independent Contractor Agreement (01 May 2026 – 30 April 2028 per ADD-2026-002)  
**MONTHLY RETAINER:** R60,000.00  

===============================================================================
 DELIVERABLES BREAKDOWN (23 SEPTEMBER – 22 OCTOBER 2026)
===============================================================================

### PART 1 – FLIGHT PLANNING & ADDENDUM B COMPRESSION (23 SEP – 07 OCT) (18 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **1.1** | **Unified Flight Plan Addendum B & Execution Decomposition**<br>• Re-engineered flight plan compression from 12-day to 9-day execution window (Plan v4)<br>• Authored HOSI-UNIFIED_FLIGHT_PLAN_ADDENDUM_B_G2_9DAY_COMPRESSION.xlsx decomposing 39 discrete engineering tasks (T01–T39, 14.25 PD)<br>• Established strict boundary verification: separated prompt authoring from verification, with verifier containment test assertions<br>• Authored scratch/build_9day_addendum.py (1,715 lines) validating resource capacity, float, and gate milestones | **9** |
| **1.2** | **Architecture Decision Records & Evidence Pack Framework**<br>• Authored comprehensive governance suite: docs/AI_INTEGRATION_PLAN_MASTER.md (660 lines) and 01_G2_POC_Plan_2026-10-05_to_2026-10-15.md<br>• Authored 02_G2_POC_Decision_Papers_D1-D8.md, 05_G2_Agent_Architecture_Assessment.md, and 06_G2_Architecture_Decision_Record.md<br>• Compiled 08_Evidence_Pack.md (DEL-19): non-interference proof, verification-independence proof, latency budget register, and acceptance checklist<br>• Implemented cryptographic ECDSA P-256 PKI Attestation Keypair engine (backend/app/security_pki.py) for attestation signing and verification | **9** |
| | **Part 1 Subtotal** | **18** |

### PART 2 – MULTI-TENANCY HARDENING & GOVERNANCE EVIDENCE (07 – 12 OCT) (18 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **2.1** | **Regulatory Alignment & Security Mapping Matrix**<br>• Authored docs/B3_POPIA_Compliance_Assessment.md and docs/B4_POPIA_Remediation_Plan.md establishing zero-log PII guardrails<br>• Formulated compliance traceability documentation: C1_Requirements_Traceability_Matrix.md, C2_Framework_Security_Mapping.md, and C3_CISO_Four_Tier_Role_Mapping.md<br>• Authored C4_Customer_Outcomes_Persona_Matrix.md, A1_Automated_Test_Report_Pack.md, and A2_Master_Test_Registry.md (2,347 lines) mapping 150+ automated test verifications<br>• Developed scripts/export_master_registry.py with defusedxml and canonical path validation | **10** |
| **2.2** | **Infrastructure Hardening & Reverse Proxy Modernization**<br>• Replaced generic Nginx config with hardened infrastructure/nginx/sita-http.conf<br>• Pinned Nginx upstream frontend port to 8080 and exposed secured backend API on port 8000 in docker-compose.remote.yml<br>• Implemented server token suppression, HR-backed user provisioning enforcement, and configurable environment controls (SEED_DEMO_USERS_ENABLED, PII_ENCRYPTION_KEY) | **8** |
| | **Part 2 Subtotal** | **18** |

### PART 3 – FMCG DISTRIBUTED DATA LAKE & INGESTION BACKEND ARCHITECTURE (07 – 13 OCT) (22 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **3.1** | **High-Throughput Streaming Ingestion Pipeline & Enterprise Reliability**<br>• Architected asynchronous ingestion pipeline (app/ingestion/fmgc_pipeline.py) streaming 12,500+ ERP order records from raw multi-sheet workbooks into PostgreSQL lake<br>• Engineered enterprise fault-tolerance: Three-state Circuit Breaker (circuit_breaker.py), Token-Bucket rate limiter (token_bucket.py), and Exponential Backoff Retry engine (retry.py)<br>• Implemented Dead-Letter Queue (dlq.py) isolating invalid/malformed records into staging.rejected_records with failure payloads and ingestion audit trails<br>• Developed dual-bus event architecture supporting Redis Streams (STREAM_FMGC_RAW) with zero-config local memory bus fallback (local_bus.py) | **11** |
| **3.2** | **PostgreSQL Lake Engine, Normalisation Rules & Predictive Analytics Models**<br>• Designed multi-schema Postgres lake (fmgc, staging, warehouse) with chunked transactional upsert engine (fmgc_writer.py, 500-record batches)<br>• Built declarative normalisation engine (fmgc_normaliser.py, field_mapper_fmgc.yaml) handling Excel sentinel dates (1900-01-01 to NaT), whitespace trimming, and net/gross lost value logic<br>• Developed predictive analytics suite (predictive.py): Logistic Regression delay-risk classifier (ROC/PR tuned), Random Forest delivery ageing regressor with multi-horizon SLA breach probabilities (7/14/30/45 days), and additive Holt-Winters intake demand forecaster<br>• Built high-performance FastAPI service (:13000, /api/v1/fmgc/*) with dual-TTL fingerprint-keyed memory cache (cache.py) and automated executive HTML report generation (reports.py) | **11** |
| | **Part 3 Subtotal** | **22** |

### PART 4 – HCL APPSCAN DAST & SAST VULNERABILITY REMEDIATION (12 – 14 OCT) (22 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **4.1** | **HCL AppScan DAST Dynamic Vulnerability Remediation & Proxy Hardening**<br>• Remediated HCL AppScan DAST assessment findings across production target (Oct 13-14 cycles)<br>• Enforced strict algorithm verification in JWT decoding, explicitly rejecting alg: none exploits<br>• Implemented mass assignment guards preventing privilege escalation and per-tenant/per-IP rate limiting middleware<br>• Upgraded Nginx to 1.27.4-alpine (resolving CVE-2025-23419), purged unsafe-inline/unsafe-eval from CSP, and remediated BFLA (CWE-284) on metrics endpoints<br>• Authored docs/SITA_DAST_VAPT_Report_Oct2026.docx and docs/SITA_VAPT_Remediation_Report_Oct2026.docx | **11** |
| **4.2** | **SAST Static Code Remediation & DefusedXML/Cryptography Hardening (49 Findings)**<br>• Resolved 49 HCL AppScan SAST static security findings across backend codebase<br>• Upgraded alert deduplication hashing from MD5 to collision-resistant SHA-256 (alert_dedup.py) and adopted secrets.SystemRandom for backoff jitter (CWE-327)<br>• Hardened backend Dockerfile: pinned python:3.12.7-slim, established non-root appuser:appgroup (CWE-266), dropped root capabilities, and enforced read-only root filesystems<br>• Mitigated XML External Entity (XXE, CWE-91) via defusedxml, eliminated Path Traversal (CWE-73) via canonical Path.resolve(), and purged hardcoded credential heuristics<br>• Authored docs/SITA_SAST_Remediation_Report.docx, docs/SAST_REMEDIATION_REPORT.md, and docs/SITA_SAST_Comparative_Analysis_Report_Oct2026.docx | **11** |
| | **Part 4 Subtotal** | **22** |

### PART 5 – AIMI AI INTELLIGENCE & 5 AVP ENDPOINTS (14 – 15 OCT) (24 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **5.1** | **AIMI VAPT Log Intelligence Engine**<br>• Architected and built backend/app/processing/intel/vapt.py: automated log intelligence parser performing severity clustering, pattern extraction, and threat narrative generation<br>• Implemented end-to-end unit test suite (backend/tests/test_vapt_log_intel.py) covering 8 deterministic scenarios<br>• Built frontend API client (frontend/src/api/intel.ts) and interactive UI panel AimiVaptLogInterpreterPanel within frontend/src/pages/AiIntelPage.tsx<br>• Gated endpoints POST /intel/vapt/interpret-logs and GET /intel/vapt/baseline-status with tenant and RBAC controls | **8** |
| **5.2** | **Five Core AI Value Proposition (AVP) Endpoints**<br>• Developed and integrated 5 core AI Value Proposition residual modules (backend/app/processing/intel/):<br>• AVP-2 (Detection Content): author_rules.py (POST /intel/attack/author-rule) proposing git-diff alert rules without automated merges<br>• AVP-3 (Threat Enrichment): campaign.py (POST /intel/threat/attribute) extracting ATT&CK/CVE techniques against estate exposure<br>• AVP-5 (Legal Guidance): popia.py (POST /intel/popia/dossier) generating POPIA Section 22 breach notification evidence packages<br>• AVP-8 (Causal Analysis): causal.py (POST /intel/risk/causal) hypothesizing root causes and mapping dominant telemetry to ATT&CK<br>• AVP-11 (Behavioral Auditing): behaviour.py (POST /intel/audit/explain) identifying temporal burst anomalies (RAPID_AUTHORITY_SWEEP, CROSS_SCOPE_PIVOT) | **10** |
| **5.3** | **Threat Attribution & Advisory Review Boundary Invariants**<br>• Enforced strict architectural safety invariant across all AI intelligence endpoints: advisory_only=True<br>• Implemented zero automated database writes and mandatory human analyst sign-off workflows<br>• Validated cross-tenant isolation and strict schema conformance across all five AVP modules | **6** |
| | **Part 5 Subtotal** | **24** |

### PART 6 – G2 AI REPORT GENERATION ENGINE & COPILOT (15 – 18 OCT) (18 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **6.1** | **G2 Two-Gate Verification Engine**<br>• Built G2 report generation architecture (backend/app/ai/):<br>• Gate 1 (Pre-generation Scope Filter): strict tenancy validation and role permission enforcement (backend/app/ai/scope.py, permissions.py)<br>• Gate 2 (Post-generation Containment Verifier): automated assertion engine verifying zero hallucination and tenant boundary compliance (backend/app/ai/verify.py)<br>• Developed context assembly pipeline (backend/app/ai/context.py) binding AI models directly to ingested tenant telemetry logs<br>• Exposed secured POST /api/v1/reports-ai endpoint with full unit test coverage (backend/tests/test_reports_ai.py) | **10** |
| **6.2** | **Frontend Interactive Grounded Copilot & Report Studio**<br>• Developed frontend/src/components/ai/AiReportStudio.tsx (1,021 lines): interactive studio featuring streaming report preview, tenant selection, two-gate status indicators, and export actions<br>• Built frontend/src/api/reportsAi.ts typed client and role-aware navigation integration | **8** |
| | **Part 6 Subtotal** | **18** |

### PART 7 – AIMI MULTI-PROVIDER GATEWAY & DBSEC AI ENGINE (19 – 21 OCT) (22 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **7.1** | **AIMI Multi-Provider Gateway Abstraction**<br>• Implemented multi-provider abstraction gateway (backend/app/ai/aimi/gateway.py, 375 lines) supporting Ollama, OpenAI, and Anthropic backends with automatic failover<br>• Authored unit test suite backend/tests/test_aimi_integration.py (425 lines) verifying deterministic provider routing and error recovery | **6** |
| **7.2** | **Real-time Contextual Enrichment & POPIA Zero-Log Sanitizer**<br>• Built real-time contextual enrichment engine (enrichment.py, 245 lines) augmenting threat prompts with localized tenant telemetry<br>• Implemented POPIA zero-log PII redaction sanitizer (redaction.py, 145 lines) scrubbing RSA ID numbers, phone numbers, and employee credentials before external inference | **5** |
| **7.3** | **Database Security (DbSec) AI Alerts Engine & React UI**<br>• Implemented database security anomaly detection engine (backend/app/processing/intel/dbsec.py, 555 lines) detecting exfiltration, privilege abuse, and anomalous queries<br>• Authored test suite backend/tests/test_dbsec_ai_alerts.py (265 lines)<br>• Developed frontend DbSecAiAlertsPanel.tsx and React hook useDbSecAiAlerts.ts | **6** |
| **7.4** | **Stakeholder Value Documentation & OpenAPI 3.1 Technical Artefacts**<br>• Generated executive value reports: generate_aimi_stakeholder_report.py -> docs/SITA_AIMI_AI_Integration_Business_Value_Proposition.docx, generate_security_progress_report.py -> docs/SITA_Security_Assessment_Progress_Report_Oct2026.docx, generate_truth_remediation_report.py -> docs/SITA_Security_Remediation_Executive_Truth_Report_Oct2026.docx<br>• Compiled complete OpenAPI 3.1 specifications (openapi.json, openapi.yaml) and ingestion documentation (INGESTION_PIPELINE_EXPLAINED.md) | **5** |
| | **Part 7 Subtotal** | **22** |

### PART 8 – C4 ARCHITECTURE VIEWER, DECKS & EXECUTIVE BRIEFS (21 – 22 OCT) (16 HRS)

| # | DELIVERABLE / DESCRIPTION | HRS |
|---|---------------------------|:---:|
| **8.1** | **Interactive C4 Architecture Viewer & Handover Decks**<br>• Enhanced interactive architecture viewer (architecture.html, 2,116 lines) incorporating comprehensive AI integration layers, inspection modals, and zero-log markers<br>• Updated handover_presentation.html and presentation.html incorporating 4-layer AI control model, live demo flows, and granular RBAC-within-tenancy matrix | **8** |
| **8.2** | **Executive Briefs Generation, UI Polish & Remote Deploy Automation**<br>• Developed scripts/create_executive_brief_docx.py generating reports/SITA_Security_Remediation_Executive_Brief.docx and reports/SITA_AI_Role_Advantage_Executive_Brief.docx<br>• Polished homepage UI (frontend/src/pages/HomePage.tsx, home.css) with clean role navigation and status badges<br>• Finalized automated remote deployment scripts (scripts/deploy_remote.py and infrastructure/scripts/deploy.sh) | **8** |
| | **Part 8 Subtotal** | **16** |



===============================================================================
 INVOICE SUMMARY
===============================================================================

| DELIVERABLE SUMMARY | HOURS |
|:--------------------|:-----:|
| PART 1 – FLIGHT PLANNING & ADDENDUM B COMPRESSION (23 SEP – 07 OCT) | 18 hrs |
| PART 2 – MULTI-TENANCY HARDENING & GOVERNANCE EVIDENCE (07 – 12 OCT) | 18 hrs |
| PART 3 – FMCG DISTRIBUTED DATA LAKE & INGESTION BACKEND ARCHITECTURE (07 – 13 OCT) | 22 hrs |
| PART 4 – HCL APPSCAN DAST & SAST VULNERABILITY REMEDIATION (12 – 14 OCT) | 22 hrs |
| PART 5 – AIMI AI INTELLIGENCE & 5 AVP ENDPOINTS (14 – 15 OCT) | 24 hrs |
| PART 6 – G2 AI REPORT GENERATION ENGINE & COPILOT (15 – 18 OCT) | 18 hrs |
| PART 7 – AIMI MULTI-PROVIDER GATEWAY & DBSEC AI ENGINE (19 – 21 OCT) | 22 hrs |
| PART 8 – C4 ARCHITECTURE VIEWER, DECKS & EXECUTIVE BRIEFS (21 – 22 OCT) | 16 hrs |
| **TOTAL HOURS** | **160 hrs** |

---

### BANKING DETAILS
- **Bank:** Bank Zero - Mukuru
- **Branch Code:** 435000
- **Account Number:** 70030185715
- **Account Holder:** Bantu InfoTech (Pty) Ltd
- **Registration No:** 2025/228003/07
- **Tax No:** 9637019200
- **Covered under:** Monthly Retainer INV-2026-010 **(R60,000.00)**

---
*Bantu InfoTech (B.iT) • Pretoria, Gauteng • SITA Platform Delivery, FMCG Data Lake Backend Architecture & AIMI AI Integration • October 2026*
