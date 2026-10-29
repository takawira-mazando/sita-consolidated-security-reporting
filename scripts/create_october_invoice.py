import os
import docx
from docx.shared import Inches, Pt, RGBColor

BASE_DOCX = r"C:\Users\HosiTech\Downloads\Invoice_INV-2026-009.docx"
OUTPUT_DOCX_DOWNLOADS = r"C:\Users\HosiTech\Downloads\INV-2026-010_October_Invoice.docx"
OUTPUT_DOCX_REPORTS = r"C:\sita-platform\reports\INV-2026-010_October_Invoice.docx"
OUTPUT_HTML_DOWNLOADS = r"C:\Users\HosiTech\Downloads\INV-2026-010_October_Invoice.html"
OUTPUT_HTML_REPORTS = r"C:\sita-platform\reports\INV-2026-010_October_Invoice.html"

COLOR_NAVY_DARK = RGBColor(0x16, 0x20, 0x3A)
COLOR_NAVY_DEEP = RGBColor(0x1F, 0x2A, 0x44)
COLOR_GOLD = RGBColor(0xC9, 0xA2, 0x4B)
COLOR_TEXT_DARK = RGBColor(0x33, 0x33, 0x33)
COLOR_MUTED = RGBColor(0x66, 0x66, 0x66)
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_BANNER_MUTED = RGBColor(0xD9, 0xD2, 0xBE)

PARTS_DATA = [
    {
        "table_idx": 2,
        "part_num": 1,
        "title": "PART 1 \u2013 FLIGHT PLANNING & ADDENDUM B COMPRESSION (23 SEP \u2013 07 OCT)",
        "total_hrs": 18,
        "items": [
            {
                "num": "1.1",
                "title": "Unified Flight Plan Addendum B & Execution Decomposition",
                "bullets": [
                    "Re-engineered flight plan compression from 12-day to 9-day execution window (Plan v4)",
                    "Authored HOSI-UNIFIED_FLIGHT_PLAN_ADDENDUM_B_G2_9DAY_COMPRESSION.xlsx decomposing 39 discrete engineering tasks (T01\u2013T39, 14.25 PD)",
                    "Established strict boundary verification: separated prompt authoring from verification, with verifier containment test assertions",
                    "Authored scratch/build_9day_addendum.py (1,715 lines) validating resource capacity, float, and gate milestones"
                ],
                "hrs": 9
            },
            {
                "num": "1.2",
                "title": "Architecture Decision Records & Evidence Pack Framework",
                "bullets": [
                    "Authored comprehensive governance suite: docs/AI_INTEGRATION_PLAN_MASTER.md (660 lines) and 01_G2_POC_Plan_2026-10-05_to_2026-10-15.md",
                    "Authored 02_G2_POC_Decision_Papers_D1-D8.md, 05_G2_Agent_Architecture_Assessment.md, and 06_G2_Architecture_Decision_Record.md",
                    "Compiled 08_Evidence_Pack.md (DEL-19): non-interference proof, verification-independence proof, latency budget register, and acceptance checklist",
                    "Implemented cryptographic ECDSA P-256 PKI Attestation Keypair engine (backend/app/security_pki.py) for attestation signing and verification"
                ],
                "hrs": 9
            }
        ]
    },
    {
        "table_idx": 3,
        "part_num": 2,
        "title": "PART 2 \u2013 MULTI-TENANCY HARDENING & GOVERNANCE EVIDENCE (07 \u2013 12 OCT)",
        "total_hrs": 18,
        "items": [
            {
                "num": "2.1",
                "title": "Regulatory Alignment & Security Mapping Matrix",
                "bullets": [
                    "Authored docs/B3_POPIA_Compliance_Assessment.md and docs/B4_POPIA_Remediation_Plan.md establishing zero-log PII guardrails",
                    "Formulated compliance traceability documentation: C1_Requirements_Traceability_Matrix.md, C2_Framework_Security_Mapping.md, and C3_CISO_Four_Tier_Role_Mapping.md",
                    "Authored C4_Customer_Outcomes_Persona_Matrix.md, A1_Automated_Test_Report_Pack.md, and A2_Master_Test_Registry.md (2,347 lines) mapping 150+ automated test verifications",
                    "Developed scripts/export_master_registry.py with defusedxml and canonical path validation"
                ],
                "hrs": 10
            },
            {
                "num": "2.2",
                "title": "Infrastructure Hardening & Reverse Proxy Modernization",
                "bullets": [
                    "Replaced generic Nginx config with hardened infrastructure/nginx/sita-http.conf",
                    "Pinned Nginx upstream frontend port to 8080 and exposed secured backend API on port 8000 in docker-compose.remote.yml",
                    "Implemented server token suppression, HR-backed user provisioning enforcement, and configurable environment controls (SEED_DEMO_USERS_ENABLED, PII_ENCRYPTION_KEY)"
                ],
                "hrs": 8
            }
        ]
    },
    {
        "table_idx": 4,
        "part_num": 3,
        "title": "PART 3 \u2013 FMCG DISTRIBUTED DATA LAKE & INGESTION BACKEND ARCHITECTURE (07 \u2013 13 OCT)",
        "total_hrs": 22,
        "items": [
            {
                "num": "3.1",
                "title": "High-Throughput Streaming Ingestion Pipeline & Enterprise Reliability",
                "bullets": [
                    "Architected asynchronous ingestion pipeline (app/ingestion/fmgc_pipeline.py) streaming 12,500+ ERP order records from raw multi-sheet workbooks into PostgreSQL lake",
                    "Engineered enterprise fault-tolerance: Three-state Circuit Breaker (circuit_breaker.py), Token-Bucket rate limiter (token_bucket.py), and Exponential Backoff Retry engine (retry.py)",
                    "Implemented Dead-Letter Queue (dlq.py) isolating invalid/malformed records into staging.rejected_records with failure payloads and ingestion audit trails",
                    "Developed dual-bus event architecture supporting Redis Streams (STREAM_FMGC_RAW) with zero-config local memory bus fallback (local_bus.py)"
                ],
                "hrs": 11
            },
            {
                "num": "3.2",
                "title": "PostgreSQL Lake Engine, Normalisation Rules & Predictive Analytics Models",
                "bullets": [
                    "Designed multi-schema Postgres lake (fmgc, staging, warehouse) with chunked transactional upsert engine (fmgc_writer.py, 500-record batches)",
                    "Built declarative normalisation engine (fmgc_normaliser.py, field_mapper_fmgc.yaml) handling Excel sentinel dates (1900-01-01 to NaT), whitespace trimming, and net/gross lost value logic",
                    "Developed predictive analytics suite (predictive.py): Logistic Regression delay-risk classifier (ROC/PR tuned), Random Forest delivery ageing regressor with multi-horizon SLA breach probabilities (7/14/30/45 days), and additive Holt-Winters intake demand forecaster",
                    "Built high-performance FastAPI service (:13000, /api/v1/fmgc/*) with dual-TTL fingerprint-keyed memory cache (cache.py) and automated executive HTML report generation (reports.py)"
                ],
                "hrs": 11
            }
        ]
    },
    {
        "table_idx": 5,
        "part_num": 4,
        "title": "PART 4 \u2013 HCL APPSCAN DAST & SAST VULNERABILITY REMEDIATION (12 \u2013 14 OCT)",
        "total_hrs": 22,
        "items": [
            {
                "num": "4.1",
                "title": "HCL AppScan DAST Dynamic Vulnerability Remediation & Proxy Hardening",
                "bullets": [
                    "Remediated HCL AppScan DAST assessment findings across production target (Oct 13-14 cycles)",
                    "Enforced strict algorithm verification in JWT decoding, explicitly rejecting alg: none exploits",
                    "Implemented mass assignment guards preventing privilege escalation and per-tenant/per-IP rate limiting middleware",
                    "Upgraded Nginx to 1.27.4-alpine (resolving CVE-2025-23419), purged unsafe-inline/unsafe-eval from CSP, and remediated BFLA (CWE-284) on metrics endpoints",
                    "Authored docs/SITA_DAST_VAPT_Report_Oct2026.docx and docs/SITA_VAPT_Remediation_Report_Oct2026.docx"
                ],
                "hrs": 11
            },
            {
                "num": "4.2",
                "title": "SAST Static Code Remediation & DefusedXML/Cryptography Hardening (49 Findings)",
                "bullets": [
                    "Resolved 49 HCL AppScan SAST static security findings across backend codebase",
                    "Upgraded alert deduplication hashing from MD5 to collision-resistant SHA-256 (alert_dedup.py) and adopted secrets.SystemRandom for backoff jitter (CWE-327)",
                    "Hardened backend Dockerfile: pinned python:3.12.7-slim, established non-root appuser:appgroup (CWE-266), dropped root capabilities, and enforced read-only root filesystems",
                    "Mitigated XML External Entity (XXE, CWE-91) via defusedxml, eliminated Path Traversal (CWE-73) via canonical Path.resolve(), and purged hardcoded credential heuristics",
                    "Authored docs/SITA_SAST_Remediation_Report.docx, docs/SAST_REMEDIATION_REPORT.md, and docs/SITA_SAST_Comparative_Analysis_Report_Oct2026.docx"
                ],
                "hrs": 11
            }
        ]
    },
    {
        "table_idx": 6,
        "part_num": 5,
        "title": "PART 5 \u2013 AIMI AI INTELLIGENCE & 5 AVP ENDPOINTS (14 \u2013 15 OCT)",
        "total_hrs": 24,
        "items": [
            {
                "num": "5.1",
                "title": "AIMI VAPT Log Intelligence Engine",
                "bullets": [
                    "Architected and built backend/app/processing/intel/vapt.py: automated log intelligence parser performing severity clustering, pattern extraction, and threat narrative generation",
                    "Implemented end-to-end unit test suite (backend/tests/test_vapt_log_intel.py) covering 8 deterministic scenarios",
                    "Built frontend API client (frontend/src/api/intel.ts) and interactive UI panel AimiVaptLogInterpreterPanel within frontend/src/pages/AiIntelPage.tsx",
                    "Gated endpoints POST /intel/vapt/interpret-logs and GET /intel/vapt/baseline-status with tenant and RBAC controls"
                ],
                "hrs": 8
            },
            {
                "num": "5.2",
                "title": "Five Core AI Value Proposition (AVP) Endpoints",
                "bullets": [
                    "Developed and integrated 5 core AI Value Proposition residual modules (backend/app/processing/intel/):",
                    "AVP-2 (Detection Content): author_rules.py (POST /intel/attack/author-rule) proposing git-diff alert rules without automated merges",
                    "AVP-3 (Threat Enrichment): campaign.py (POST /intel/threat/attribute) extracting ATT&CK/CVE techniques against estate exposure",
                    "AVP-5 (Legal Guidance): popia.py (POST /intel/popia/dossier) generating POPIA Section 22 breach notification evidence packages",
                    "AVP-8 (Causal Analysis): causal.py (POST /intel/risk/causal) hypothesizing root causes and mapping dominant telemetry to ATT&CK",
                    "AVP-11 (Behavioral Auditing): behaviour.py (POST /intel/audit/explain) identifying temporal burst anomalies (RAPID_AUTHORITY_SWEEP, CROSS_SCOPE_PIVOT)"
                ],
                "hrs": 10
            },
            {
                "num": "5.3",
                "title": "Threat Attribution & Advisory Review Boundary Invariants",
                "bullets": [
                    "Enforced strict architectural safety invariant across all AI intelligence endpoints: advisory_only=True",
                    "Implemented zero automated database writes and mandatory human analyst sign-off workflows",
                    "Validated cross-tenant isolation and strict schema conformance across all five AVP modules"
                ],
                "hrs": 6
            }
        ]
    },
    {
        "table_idx": 7,
        "part_num": 6,
        "title": "PART 6 \u2013 G2 AI REPORT GENERATION ENGINE & COPILOT (15 \u2013 18 OCT)",
        "total_hrs": 18,
        "items": [
            {
                "num": "6.1",
                "title": "G2 Two-Gate Verification Engine",
                "bullets": [
                    "Built G2 report generation architecture (backend/app/ai/):",
                    "Gate 1 (Pre-generation Scope Filter): strict tenancy validation and role permission enforcement (backend/app/ai/scope.py, permissions.py)",
                    "Gate 2 (Post-generation Containment Verifier): automated assertion engine verifying zero hallucination and tenant boundary compliance (backend/app/ai/verify.py)",
                    "Developed context assembly pipeline (backend/app/ai/context.py) binding AI models directly to ingested tenant telemetry logs",
                    "Exposed secured POST /api/v1/reports-ai endpoint with full unit test coverage (backend/tests/test_reports_ai.py)"
                ],
                "hrs": 10
            },
            {
                "num": "6.2",
                "title": "Frontend Interactive Grounded Copilot & Report Studio",
                "bullets": [
                    "Developed frontend/src/components/ai/AiReportStudio.tsx (1,021 lines): interactive studio featuring streaming report preview, tenant selection, two-gate status indicators, and export actions",
                    "Built frontend/src/api/reportsAi.ts typed client and role-aware navigation integration"
                ],
                "hrs": 8
            }
        ]
    },
    {
        "table_idx": 8,
        "part_num": 7,
        "title": "PART 7 \u2013 AIMI MULTI-PROVIDER GATEWAY & DBSEC AI ENGINE (19 \u2013 21 OCT)",
        "total_hrs": 22,
        "items": [
            {
                "num": "7.1",
                "title": "AIMI Multi-Provider Gateway Abstraction",
                "bullets": [
                    "Implemented multi-provider abstraction gateway (backend/app/ai/aimi/gateway.py, 375 lines) supporting Ollama, OpenAI, and Anthropic backends with automatic failover",
                    "Authored unit test suite backend/tests/test_aimi_integration.py (425 lines) verifying deterministic provider routing and error recovery"
                ],
                "hrs": 6
            },
            {
                "num": "7.2",
                "title": "Real-time Contextual Enrichment & POPIA Zero-Log Sanitizer",
                "bullets": [
                    "Built real-time contextual enrichment engine (enrichment.py, 245 lines) augmenting threat prompts with localized tenant telemetry",
                    "Implemented POPIA zero-log PII redaction sanitizer (redaction.py, 145 lines) scrubbing RSA ID numbers, phone numbers, and employee credentials before external inference"
                ],
                "hrs": 5
            },
            {
                "num": "7.3",
                "title": "Database Security (DbSec) AI Alerts Engine & React UI",
                "bullets": [
                    "Implemented database security anomaly detection engine (backend/app/processing/intel/dbsec.py, 555 lines) detecting exfiltration, privilege abuse, and anomalous queries",
                    "Authored test suite backend/tests/test_dbsec_ai_alerts.py (265 lines)",
                    "Developed frontend DbSecAiAlertsPanel.tsx and React hook useDbSecAiAlerts.ts"
                ],
                "hrs": 6
            },
            {
                "num": "7.4",
                "title": "Stakeholder Value Documentation & OpenAPI 3.1 Technical Artefacts",
                "bullets": [
                    "Generated executive value reports: generate_aimi_stakeholder_report.py -> docs/SITA_AIMI_AI_Integration_Business_Value_Proposition.docx, generate_security_progress_report.py -> docs/SITA_Security_Assessment_Progress_Report_Oct2026.docx, generate_truth_remediation_report.py -> docs/SITA_Security_Remediation_Executive_Truth_Report_Oct2026.docx",
                    "Compiled complete OpenAPI 3.1 specifications (openapi.json, openapi.yaml) and ingestion documentation (INGESTION_PIPELINE_EXPLAINED.md)"
                ],
                "hrs": 5
            }
        ]
    },
    {
        "table_idx": 9,
        "part_num": 8,
        "title": "PART 8 \u2013 C4 ARCHITECTURE VIEWER, DECKS & EXECUTIVE BRIEFS (21 \u2013 22 OCT)",
        "total_hrs": 16,
        "items": [
            {
                "num": "8.1",
                "title": "Interactive C4 Architecture Viewer & Handover Decks",
                "bullets": [
                    "Enhanced interactive architecture viewer (architecture.html, 2,116 lines) incorporating comprehensive AI integration layers, inspection modals, and zero-log markers",
                    "Updated handover_presentation.html and presentation.html incorporating 4-layer AI control model, live demo flows, and granular RBAC-within-tenancy matrix"
                ],
                "hrs": 8
            },
            {
                "num": "8.2",
                "title": "Executive Briefs Generation, UI Polish & Remote Deploy Automation",
                "bullets": [
                    "Developed scripts/create_executive_brief_docx.py generating reports/SITA_Security_Remediation_Executive_Brief.docx and reports/SITA_AI_Role_Advantage_Executive_Brief.docx",
                    "Polished homepage UI (frontend/src/pages/HomePage.tsx, home.css) with clean role navigation and status badges",
                    "Finalized automated remote deployment scripts (scripts/deploy_remote.py and infrastructure/scripts/deploy.sh)"
                ],
                "hrs": 8
            }
        ]
    }
]

def format_cell_text(cell, paragraphs_data):
    """
    Clears cell and sets structured paragraphs.
    paragraphs_data: list of list of (text, font_name, size_pt, bold, color_rgb)
    """
    p0 = cell.paragraphs[0]
    p0.text = ""
    for r in p0.runs:
        r.text = ""
    
    # remove extra paragraphs in cell
    p_elements = cell._tc.xpath('./w:p')
    for extra_p in p_elements[1:]:
        cell._tc.remove(extra_p)
    
    for i, p_runs in enumerate(paragraphs_data):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.05
        for text, font_name, size_pt, bold, color_rgb in p_runs:
            run = p.add_run(text)
            run.font.name = font_name
            if size_pt:
                run.font.size = Pt(size_pt)
            if bold is not None:
                run.font.bold = bold
            if color_rgb:
                run.font.color.rgb = color_rgb

def generate_docx():
    doc = docx.Document(BASE_DOCX)
    
    # 1. Update Table 0 (Banner)
    t0 = doc.tables[0]
    cell0 = t0.rows[0].cells[0]
    format_cell_text(cell0, [
        [("BANTU INFOTECH", "Calibri", 15.0, True, COLOR_WHITE)],
        [("(B.iT)", "Calibri", 10.0, True, COLOR_GOLD)],
        [("INV-2026-010  \u2022  SITA Security Platform & FMCG Ingestion Data Lake Backend Architecture", "Calibri", 11.0, True, COLOR_WHITE)],
        [("Period: 23 September 2026 \u2013 22 October 2026", "Calibri", 9.0, None, COLOR_BANNER_MUTED)]
    ])
    
    # 2. Update Paragraph 1 (Project Info)
    p1 = doc.paragraphs[1]
    p1.text = ""
    
    def add_p1_field(label, val, newline=True):
        if newline:
            r1 = p1.add_run("\n   |   " + label)
        else:
            r1 = p1.add_run("   |   " + label)
        r1.font.name = "Calibri"
        r1.font.size = Pt(8.5)
        r1.font.bold = True
        r1.font.color.rgb = COLOR_NAVY_DARK
        
        r2 = p1.add_run(val)
        r2.font.name = "Calibri"
        r2.font.size = Pt(8.5)
        r2.font.color.rgb = COLOR_TEXT_DARK
        
    r_lead = p1.add_run("Project: ")
    r_lead.font.name = "Calibri"
    r_lead.font.size = Pt(8.5)
    r_lead.font.bold = True
    r_lead.font.color.rgb = COLOR_NAVY_DARK
    
    r_pname = p1.add_run("SITA Security Intelligence Platform (Addendum B, AppScan SAST/DAST Remediation, AIMI AI Layer) & FMCG Enterprise Ingestion, Data Lake & Predictive Analytics Backend Architecture")
    r_pname.font.name = "Calibri"
    r_pname.font.size = Pt(8.5)
    r_pname.font.color.rgb = COLOR_TEXT_DARK
    
    add_p1_field("Contract: ", "Monthly Retainer under Independent Contractor Agreement (01 May 2026 \u2013 30 April 2028 per ADD-2026-002)", newline=True)
    add_p1_field("Period: ", "23 September 2026 \u2013 22 October 2026", newline=True)
    add_p1_field("Date: ", "22 October 2026", newline=False)
    add_p1_field("Invoice: ", "INV-2026-010", newline=False)
    add_p1_field("Contact: ", "admin@hosi.co.za", newline=True)
    
    # 3. Update Deliverable Tables (Tables 2 to 9)
    for pdata in PARTS_DATA:
        t_idx = pdata["table_idx"]
        t = doc.tables[t_idx]
        
        # Row 0: Title and Total Hours
        r0 = t.rows[0]
        # cells 0 and 1 have title, cell 2 has hours
        format_cell_text(r0.cells[0], [[(pdata["title"], "Calibri", 10.0, True, COLOR_WHITE)]])
        if len(r0.cells) > 1:
            format_cell_text(r0.cells[1], [[(pdata["title"], "Calibri", 10.0, True, COLOR_WHITE)]])
        if len(r0.cells) > 2:
            format_cell_text(r0.cells[2], [[(f"{pdata['total_hrs']} HRS", "Calibri", 10.0, True, COLOR_WHITE)]])
            
        # Row 1 is Header (#, DELIVERABLE / DESCRIPTION, HRS) - already styled
        
        # Deliverable Rows
        items = pdata["items"]
        for it_idx, item in enumerate(items):
            row_idx = 2 + it_idx
            r_item = t.rows[row_idx]
            
            # Cell 0: Number
            format_cell_text(r_item.cells[0], [[(item["num"], "Calibri", 9.0, True, COLOR_NAVY_DEEP)]])
            
            # Cell 1: Title and Bullets
            paras = [[(item["title"], "Calibri", 9.5, True, COLOR_NAVY_DARK)]]
            for bullet in item["bullets"]:
                paras.append([
                    ("\u2022 ", "Calibri", 9.0, True, COLOR_GOLD),
                    (bullet, "Calibri", 9.0, None, COLOR_TEXT_DARK)
                ])
            format_cell_text(r_item.cells[1], paras)
            
            # Cell 2: Hours
            format_cell_text(r_item.cells[2], [[(str(item["hrs"]), "Calibri", 9.5, True, COLOR_NAVY_DEEP)]])
            
        # Subtotal Row (last row)
        subtotal_row = t.rows[-1]
        subtotal_label = f"Part {pdata['part_num']} Subtotal"
        format_cell_text(subtotal_row.cells[0], [[(subtotal_label, "Calibri", 9.5, True, COLOR_NAVY_DARK)]])
        if len(subtotal_row.cells) > 1:
            format_cell_text(subtotal_row.cells[1], [[(subtotal_label, "Calibri", 9.5, True, COLOR_NAVY_DARK)]])
        if len(subtotal_row.cells) > 2:
            format_cell_text(subtotal_row.cells[2], [[(str(pdata["total_hrs"]), "Calibri", 9.5, True, COLOR_NAVY_DARK)]])

    # 4. Update Table 10 (Summary Table)
    t10 = doc.tables[10]
    for pdata in PARTS_DATA:
        p_num = pdata["part_num"]
        r = t10.rows[p_num]
        format_cell_text(r.cells[0], [[(pdata["title"], "Calibri", 9.0, None, RGBColor(0x22, 0x22, 0x22))]])
        format_cell_text(r.cells[1], [[(f"{pdata['total_hrs']} hrs", "Calibri", 9.0, True, COLOR_NAVY_DEEP)]])
    
    # Total hours row
    r_total = t10.rows[9]
    format_cell_text(r_total.cells[0], [[("TOTAL HOURS", "Calibri", 9.5, True, COLOR_NAVY_DARK)]])
    format_cell_text(r_total.cells[1], [[("160 hrs", "Calibri", 9.5, True, COLOR_NAVY_DARK)]])
    
    # 5. Update Table 11 (Banking Details)
    t11 = doc.tables[11]
    cell11 = t11.rows[0].cells[0]
    format_cell_text(cell11, [
        [("BANKING DETAILS", "Calibri", 9.0, True, COLOR_GOLD)],
        [("Bank: Bank Zero - Mukuru Branch Code: 435000", "Calibri", 8.5, None, COLOR_TEXT_DARK)],
        [("Account Number: 70030185715", "Calibri", 8.5, None, COLOR_TEXT_DARK)],
        [("Account Holder: Bantu InfoTech (Pty) Ltd", "Calibri", 8.5, None, COLOR_TEXT_DARK)],
        [("Registration No: 2025/228003/07", "Calibri", 8.5, None, COLOR_TEXT_DARK)],
        [("Tax No: 9637019200", "Calibri", 8.5, None, COLOR_TEXT_DARK)],
        [("Covered under: Monthly Retainer INV-2026-010  (R60,000.00)", "Calibri", 8.5, True, COLOR_NAVY_DARK)]
    ])
    
    # 6. Update Footer Paragraph
    p_footer = doc.paragraphs[-1]
    p_footer.text = ""
    r_f1 = p_footer.add_run("\nBantu InfoTech (B.iT) \u2022 Pretoria, Gauteng\n")
    r_f1.font.name = "Calibri"
    r_f1.font.size = Pt(8.0)
    r_f1.font.color.rgb = COLOR_MUTED
    
    r_f2 = p_footer.add_run("SITA Platform Delivery, FMCG Data Lake Backend Architecture & AIMI AI Integration \u2022 October 2026")
    r_f2.font.name = "Calibri"
    r_f2.font.size = Pt(8.0)
    r_f2.font.color.rgb = COLOR_MUTED

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_DOCX_REPORTS), exist_ok=True)
    try:
        doc.save(OUTPUT_DOCX_DOWNLOADS)
        print("DOCX successfully generated at:")
        print(" ", OUTPUT_DOCX_DOWNLOADS)
    except PermissionError:
        print(f"Notice: {OUTPUT_DOCX_DOWNLOADS} is currently open in another program (e.g. Word). Skipping write.")
    try:
        doc.save(OUTPUT_DOCX_REPORTS)
        print(" ", OUTPUT_DOCX_REPORTS)
    except PermissionError:
        print(f"Notice: {OUTPUT_DOCX_REPORTS} is currently open in another program. Skipping write.")

def generate_html():
    rows_html = ""
    summary_rows_html = ""
    
    for pdata in PARTS_DATA:
        items_html = ""
        for it in pdata["items"]:
            bullets_li = "".join(f"<li>{b}</li>" for b in it["bullets"])
            items_html += f"""
            <tr>
              <td class="col-num">{it["num"]}</td>
              <td class="col-desc">
                <div class="deliv-title">{it["title"]}</div>
                <ul class="bullet-list">{bullets_li}</ul>
              </td>
              <td class="col-hrs">{it["hrs"]}</td>
            </tr>
            """
            
        rows_html += f"""
        <div class="part-block">
          <div class="part-header">
            <span class="part-title">{pdata["title"]}</span>
            <span class="part-badge">{pdata["total_hrs"]} HRS</span>
          </div>
          <table class="deliv-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th>DELIVERABLE / DESCRIPTION</th>
                <th style="width: 70px;">HRS</th>
              </tr>
            </thead>
            <tbody>
              {items_html}
              <tr class="subtotal-row">
                <td colspan="2">Part {pdata["part_num"]} Subtotal</td>
                <td class="col-hrs">{pdata["total_hrs"]}</td>
              </tr>
            </tbody>
          </table>
        </div>
        """
        
        summary_rows_html += f"""
        <tr>
          <td>{pdata["title"]}</td>
          <td style="text-align: right; font-weight: bold; color: #1f2a44;">{pdata["total_hrs"]} hrs</td>
        </tr>
        """
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TAX INVOICE INV-2026-010 | Bantu InfoTech</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 15mm;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    background: #f1f4f8;
    color: #333333;
    line-height: 1.45;
    padding: 25px 0;
  }}
  .invoice-container {{
    max-width: 960px;
    margin: 0 auto;
    background: #ffffff;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border-radius: 6px;
    overflow: hidden;
  }}
  .banner {{
    background: #1F2A44;
    color: #ffffff;
    padding: 24px 32px;
    border-bottom: 4px solid #C9A24B;
  }}
  .banner h1 {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }}
  .banner .subtitle {{
    color: #C9A24B;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 10px;
  }}
  .banner .inv-meta {{
    font-size: 14px;
    font-weight: 600;
    color: #FFFFFF;
    margin-bottom: 4px;
  }}
  .banner .period {{
    font-size: 12px;
    color: #D9D2BE;
  }}
  
  .party-section {{
    display: flex;
    justify-content: space-between;
    padding: 20px 32px;
    background: #FAFAFC;
    border-bottom: 1px solid #E2E8F0;
  }}
  .party-col {{
    width: 48%;
  }}
  .party-tag {{
    font-size: 11px;
    font-weight: 700;
    color: #C9A24B;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
  }}
  .party-name {{
    font-size: 15px;
    font-weight: 700;
    color: #16203A;
    margin-bottom: 3px;
  }}
  .party-details {{
    font-size: 12px;
    color: #4A5568;
    line-height: 1.5;
  }}
  
  .project-box {{
    margin: 20px 32px;
    padding: 14px 18px;
    background: #F8FAFC;
    border-left: 4px solid #1F2A44;
    border-radius: 4px;
    font-size: 12px;
    color: #333333;
  }}
  .project-box strong {{
    color: #16203A;
  }}
  
  .deliverables-wrapper {{
    padding: 0 32px;
  }}
  .part-block {{
    margin-bottom: 22px;
  }}
  .part-header {{
    background: #1F2A44;
    color: #ffffff;
    padding: 8px 14px;
    border-radius: 4px 4px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}
  .part-badge {{
    background: #C9A24B;
    color: #16203A;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 800;
  }}
  
  .deliv-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .deliv-table th {{
    background: #F2F2F2;
    color: #16203A;
    text-align: left;
    padding: 7px 12px;
    font-weight: 700;
    font-size: 11px;
    border: 1px solid #E2E8F0;
  }}
  .deliv-table td {{
    padding: 9px 12px;
    border: 1px solid #E2E8F0;
    vertical-align: top;
  }}
  .col-num {{
    text-align: center;
    font-weight: 700;
    color: #1F2A44;
  }}
  .col-hrs {{
    text-align: center;
    font-weight: 700;
    color: #1F2A44;
  }}
  .deliv-title {{
    font-weight: 700;
    color: #16203A;
    margin-bottom: 5px;
    font-size: 12.5px;
  }}
  .bullet-list {{
    margin-left: 18px;
    color: #4A5568;
    font-size: 11.5px;
  }}
  .bullet-list li {{
    margin-bottom: 3px;
  }}
  .subtotal-row td {{
    background: #F8FAFC;
    font-weight: 700;
    color: #16203A;
  }}
  
  .summary-section {{
    margin: 25px 32px;
  }}
  .summary-title {{
    font-size: 14px;
    font-weight: 800;
    color: #16203A;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
  }}
  .summary-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .summary-table th {{
    background: #1F2A44;
    color: #ffffff;
    text-align: left;
    padding: 8px 12px;
    font-size: 12px;
  }}
  .summary-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid #E2E8F0;
  }}
  .total-row td {{
    background: #F8FAFC;
    font-size: 13px;
    font-weight: 800;
    color: #16203A;
    border-top: 2px solid #1F2A44;
  }}
  
  .banking-box {{
    margin: 20px 32px 30px 32px;
    padding: 16px 20px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    font-size: 12px;
  }}
  .banking-tag {{
    font-weight: 700;
    color: #C9A24B;
    margin-bottom: 6px;
    font-size: 11px;
    letter-spacing: 0.5px;
  }}
  
  .footer {{
    text-align: center;
    padding: 16px 32px;
    background: #F1F4F8;
    font-size: 11px;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
  }}
</style>
</head>
<body>
<div class="invoice-container">
  
  <!-- BANNER -->
  <div class="banner">
    <h1>BANTU INFOTECH</h1>
    <div class="subtitle">(B.iT)</div>
    <div class="inv-meta">INV-2026-010 &nbsp;\u2022&nbsp; SITA Security Platform & FMCG Ingestion Data Lake Backend Architecture</div>
    <div class="period">Period: 23 September 2026 \u2013 22 October 2026 &nbsp;|&nbsp; Date: 22 October 2026</div>
  </div>

  <!-- PARTIES -->
  <div class="party-section">
    <div class="party-col">
      <div class="party-tag">PREPARED BY</div>
      <div class="party-name">Takawira Mazando</div>
      <div class="party-details">
        Senior Full Stack Software Developer<br>
        Bantu InfoTech (B.iT)<br>
        Phone: 0672 319 200<br>
        Email: takawira.mazando@entailabs.com
      </div>
    </div>
    <div class="party-col">
      <div class="party-tag">CLIENT</div>
      <div class="party-name">Hosi Technologies (Pty) Ltd</div>
      <div class="party-details">
        Attn: Koketso Molelemane (Human Capital Manager)<br>
        Email: Koketso@hosi.co.za<br>
        Registration: 2010/015030/07<br>
        Hosi Academy LMS Division<br>
        Block A, 2nd Floor, The Pivot, Fourways, Johannesburg
      </div>
    </div>
  </div>

  <!-- PROJECT CONTEXT -->
  <div class="project-box">
    <strong>Project:</strong> SITA Security Intelligence Platform (Addendum B, AppScan SAST/DAST Remediation, AIMI AI Layer) & FMCG Enterprise Ingestion, Data Lake & Predictive Analytics Backend Architecture<br>
    <strong>Contract:</strong> Monthly Retainer under Independent Contractor Agreement (01 May 2026 \u2013 30 April 2028 per ADD-2026-002)<br>
    <strong>Period:</strong> 23 September 2026 \u2013 22 October 2026 &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Date:</strong> 22 October 2026 &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Invoice No:</strong> INV-2026-010<br>
    <strong>Contact:</strong> admin@hosi.co.za &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Monthly Retainer:</strong> R60,000.00
  </div>

  <!-- DELIVERABLES -->
  <div class="deliverables-wrapper">
    {rows_html}
  </div>

  <!-- SUMMARY -->
  <div class="summary-section">
    <div class="summary-title">INVOICE SUMMARY</div>
    <table class="summary-table">
      <thead>
        <tr>
          <th>DELIVERABLE SUMMARY</th>
          <th style="width: 120px; text-align: right;">HOURS</th>
        </tr>
      </thead>
      <tbody>
        {summary_rows_html}
        <tr class="total-row">
          <td>TOTAL HOURS</td>
          <td style="text-align: right;">160 hrs</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- BANKING DETAILS -->
  <div class="banking-box">
    <div class="banking-tag">BANKING DETAILS</div>
    <strong>Bank:</strong> Bank Zero - Mukuru &nbsp;|&nbsp; <strong>Branch Code:</strong> 435000<br>
    <strong>Account Number:</strong> 70030185715<br>
    <strong>Account Holder:</strong> Bantu InfoTech (Pty) Ltd<br>
    <strong>Registration No:</strong> 2025/228003/07 &nbsp;|&nbsp; <strong>Tax No:</strong> 9637019200<br>
    <strong>Covered under:</strong> Monthly Retainer INV-2026-010 &nbsp;<strong>(R60,000.00)</strong>
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Bantu InfoTech (B.iT) \u2022 Pretoria, Gauteng<br>
    SITA Platform Delivery, FMCG Data Lake Backend Architecture & AIMI AI Integration \u2022 October 2026
  </div>

</div>
</body>
</html>
"""
    with open(OUTPUT_HTML_DOWNLOADS, "w", encoding="utf-8") as f:
        f.write(html)
    with open(OUTPUT_HTML_REPORTS, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML successfully generated at:")
    print(" ", OUTPUT_HTML_DOWNLOADS)
    print(" ", OUTPUT_HTML_REPORTS)

def generate_markdown():
    OUTPUT_MD_DOWNLOADS = r"C:\Users\HosiTech\Downloads\INV-2026-010_October_Invoice.md"
    OUTPUT_MD_REPORTS = r"C:\sita-platform\reports\INV-2026-010_October_Invoice.md"
    
    parts_md = ""
    summary_md = ""
    for pdata in PARTS_DATA:
        parts_md += f"### {pdata['title']} ({pdata['total_hrs']} HRS)\n\n"
        parts_md += "| # | DELIVERABLE / DESCRIPTION | HRS |\n"
        parts_md += "|---|---------------------------|:---:|\n"
        for it in pdata["items"]:
            bullets_txt = "<br>• ".join(it["bullets"])
            parts_md += f"| **{it['num']}** | **{it['title']}**<br>• {bullets_txt} | **{it['hrs']}** |\n"
        parts_md += f"| | **Part {pdata['part_num']} Subtotal** | **{pdata['total_hrs']}** |\n\n"
        
        summary_md += f"| {pdata['title']} | {pdata['total_hrs']} hrs |\n"
        
    md = f"""===============================================================================
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

{parts_md}

===============================================================================
 INVOICE SUMMARY
===============================================================================

| DELIVERABLE SUMMARY | HOURS |
|:--------------------|:-----:|
{summary_md}| **TOTAL HOURS** | **160 hrs** |

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
"""
    with open(OUTPUT_MD_DOWNLOADS, "w", encoding="utf-8") as f:
        f.write(md)
    with open(OUTPUT_MD_REPORTS, "w", encoding="utf-8") as f:
        f.write(md)
    print("Markdown successfully generated at:")
    print(" ", OUTPUT_MD_DOWNLOADS)
    print(" ", OUTPUT_MD_REPORTS)

def generate_pdf():
    import subprocess
    OUTPUT_PDF_DOWNLOADS = r"C:\Users\HosiTech\Downloads\INV-2026-010_October_Invoice.pdf"
    OUTPUT_PDF_REPORTS = r"C:\sita-platform\reports\INV-2026-010_October_Invoice.pdf"
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    if os.path.exists(edge_exe):
        try:
            cmd = [
                edge_exe,
                "--headless",
                "--disable-gpu",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={OUTPUT_PDF_DOWNLOADS}",
                OUTPUT_HTML_DOWNLOADS
            ]
            subprocess.run(cmd, check=True)
            import shutil
            shutil.copy2(OUTPUT_PDF_DOWNLOADS, OUTPUT_PDF_REPORTS)
            print("PDF successfully generated at:")
            print(" ", OUTPUT_PDF_DOWNLOADS)
            print(" ", OUTPUT_PDF_REPORTS)
        except Exception as e:
            print(f"Notice: Could not write PDF (might be open in viewer): {e}")
    else:
        print("Edge binary not found; skipping PDF generation.")

if __name__ == "__main__":
    generate_docx()
    generate_html()
    generate_markdown()
    generate_pdf()


