import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from copy import copy
from datetime import datetime
import os

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED_DATA_MANAGED_SERVICE_PROJECT_FLIGHT_PLAN_2026_20 August 2026 new (1).xlsx"
print(f"Loading workbook: {file_path}")
wb = openpyxl.load_workbook(file_path)
ws_plan = wb["Project Plan "]
ws_miles = wb["Milestones"]
ws_doc = wb["Doc Control"]

# ------------------------------------------------------------------------------
# 1. Update Existing Phase 12 Items (Rows 106 to 111)
# ------------------------------------------------------------------------------
print("Updating existing Phase 12 items to reflect completed deliverables...")

# Row 106: User acceptance testing and Mitigation of defects
ws_plan.cell(row=106, column=4, value="Completed")
ws_plan.cell(row=106, column=5, value=1.0)
ws_plan.cell(row=106, column=7, value=datetime(2026, 9, 10))
ws_plan.cell(row=106, column=9, value="UAT completed successfully with 173/173 tests passing (100% pass rate), 0 unresolved defects, formal Quality Gates signed off (v1.1).")
ws_plan.cell(row=106, column=13, value="Supported by SITA_Platform_Test_Cases.xlsx (173 test cases) and SITA_Test_Exit_Criteria_and_Quality_Gates.xlsx (9 Quality Gates).")

# Row 107: Runbook & operations guide
ws_plan.cell(row=107, column=4, value="Completed")
ws_plan.cell(row=107, column=5, value=1.0)
ws_plan.cell(row=107, column=7, value=datetime(2026, 9, 10))
ws_plan.cell(row=107, column=9, value="Approved operational runbooks delivered: docs/DEPLOYMENT_PLAN.md/.docx/.html (v2.0 enriched plan), DEMO_SETUP.md (environment runbook), and MANUAL_TEST_PLAN.md.")
ws_plan.cell(row=107, column=13, value="Full runbook coverage: deployment phases 0-6, backup/PITR, SSH VPN tunnels, day-to-day QA execution sessions A-F.")

# Row 108: Stakeholder demo & training
ws_plan.cell(row=108, column=4, value="Completed")
ws_plan.cell(row=108, column=5, value=1.0)
ws_plan.cell(row=108, column=7, value=datetime(2026, 9, 10))
ws_plan.cell(row=108, column=9, value="Stakeholder walkthrough materials delivered: DEMO_PLAN.md (demo narrative), WALKTHROUGH.md (5-stage live script), architecture.html (interactive viewer), and presentation.html (executive deck).")
ws_plan.cell(row=108, column=13, value="Demonstration validated across all 5 personas (admin@, transversal@, deptadmin-ha@, appsec-ha@, dbsec-ha@, soc-ha@).")

# Row 109: Security review & penetration test (Already Completed)
ws_plan.cell(row=109, column=4, value="Completed")
ws_plan.cell(row=109, column=5, value=1.0)
ws_plan.cell(row=109, column=7, value=datetime(2026, 8, 28))
ws_plan.cell(row=109, column=9, value="Security vulnerabilities assessed, penetration testing completed; 11 VAPT findings remediated (VAPT-001 to VAPT-011) per VAPT_REMEDIATION_REPORT.docx & commit 9773720; Bandit (8,222 LOC, 0 issues), Semgrep 0 issues.")
ws_plan.cell(row=109, column=13, value="Formal security verification completed with zero unresolved Critical or High vulnerabilities.")

# Row 110: Production go-live
ws_plan.cell(row=110, column=4, value="WIP")
ws_plan.cell(row=110, column=5, value=0.90)
ws_plan.cell(row=110, column=7, value=datetime(2026, 9, 15))
ws_plan.cell(row=110, column=9, value="Solution packaged and validated (Docker images on GHCR, Vite production build dist/, K8s CronJobs); staging verified, awaiting final production cutover window.")
ws_plan.cell(row=110, column=13, value="Pre-flight quality gates cleared; deployment runbook validated.")

# Row 111: Risk: Compliance data migration incomplete
ws_plan.cell(row=111, column=4, value="Completed")
ws_plan.cell(row=111, column=5, value=1.0)
ws_plan.cell(row=111, column=7, value=datetime(2026, 9, 10))
ws_plan.cell(row=111, column=9, value="Risk mitigated: POPIA compliance dataset seeded and verified at 82.9% (97/117 controls passed) with 360 continuous historical snapshots; AG SHA-256 export verified.")
ws_plan.cell(row=111, column=13, value="Mitigated: compliance data pipeline operational with tamper-evident audit logging and verification endpoint.")

# ------------------------------------------------------------------------------
# 2. Add Missing Deliverables Added After 20/8/2026 (Rows 112 to 125)
# ------------------------------------------------------------------------------
print("Adding 14 granular deliverables created after 20/08/2026...")

new_deliverables = [
    # Row 112
    {
        "phase": None,
        "task": "SITA Platform Requirements Specification (BRD/FRD v1.0)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 20),
        "end": datetime(2026, 8, 21),
        "owner": "Takawira",
        "deliverable": "REQUIREMENTS.docx / REQUIREMENTS.html / REQUIREMENTS.md — comprehensive functional & non-functional requirements specification (multi-tenancy, OEM ingestion, RBAC, POPIA compliance, AG attestation).",
        "risks": "Scope changes during stakeholder reviews",
        "deps": "SITA enterprise architecture baseline",
        "obstacles": "",
        "notes": "Tri-format deliverable: Word (.docx), print-ready HTML, and Markdown."
    },
    # Row 113
    {
        "phase": None,
        "task": "Master Test Plan Specification (v1.0)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 21),
        "end": datetime(2026, 8, 25),
        "owner": "Takawira",
        "deliverable": "TEST_PLAN.md / TEST_PLAN.docx — formal test plan covering in-scope FastAPI endpoints, React frontend flows, tenancy & RBAC entitlement testing, CI regression baseline (commit a53f829, 128 tests), and test environment.",
        "risks": "",
        "deps": "Stable solution build, OpenAPI schema",
        "obstacles": "",
        "notes": "Includes traceability matrix mapping Flight Plan Phase 11 requirements to test cases."
    },
    # Row 114
    {
        "phase": None,
        "task": "Manual Test Execution Plan & Day-to-Day QA Runbook",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 21),
        "end": datetime(2026, 8, 25),
        "owner": "Takawira",
        "deliverable": "MANUAL_TEST_PLAN.md / MANUAL_TEST_PLAN.docx — QA tester day-to-day execution runbook: daily pre-test checklists and 6 structured test sessions (Sessions A–F: API Smoke, Frontend Login Flow, Post-Login Verification, Tenancy Switching, Security/Edge, Cross-Browser).",
        "risks": "",
        "deps": "Test environment & VPN tunnels",
        "obstacles": "",
        "notes": "Used by QA testing team for daily pre-release verification."
    },
    # Row 115
    {
        "phase": None,
        "task": "VAPT Remediation & Security Hardening (P0/P1)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 26),
        "end": datetime(2026, 8, 28),
        "owner": "Peter and Takawira",
        "deliverable": "VAPT_REMEDIATION_REPORT.docx & commit 9773720 — remediation of 11 identified VAPT vulnerabilities (VAPT-001 through VAPT-011): production demo gating, CORS restriction, token enforcement, CSP/HSTS/X-Frame-Options middleware, Docker DB port lockdown.",
        "risks": "Regression on demo functionality — mitigated by environment checks",
        "deps": "Penetration test findings log",
        "obstacles": "",
        "notes": "All 11 vulnerabilities remediated and validated in staging."
    },
    # Row 116
    {
        "phase": None,
        "task": "HCL AppScan Cloud Ingestion Connector & Telemetry Integration",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 27),
        "end": datetime(2026, 8, 28),
        "owner": "Takawira",
        "deliverable": "APPSACN_INTEGRATION_REPORT.docx, fetch_appscan.py, scripts/ingest_appscan_logs.py, seed_real_appscan.py — live HCL AppScan Cloud REST connector pulling real DAST/SAST findings (SQLi CVSS 9.8, XSS CVSS 7.1, Insecure Design CVSS 7.5), schema normalization, and risk score calculation.",
        "risks": "AppScan API rate limits and token expiry (25 min TTL)",
        "deps": "HCL AppScan API access & credentials",
        "obstacles": "",
        "notes": "Live connector extracts 14+ real vulnerability findings for demo.testfire.net."
    },
    # Row 117
    {
        "phase": None,
        "task": "Kubernetes Ingestion Automation & CronJob Pipelines",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 28),
        "end": datetime(2026, 8, 28),
        "owner": "Peter and Takawira",
        "deliverable": "k8s/appscan-ingestion-cronjob.yaml & k8s/unified-ingestion-cronjobs.yaml — production Kubernetes CronJob manifests for automated 5-minute recurring telemetry synchronization from AppScan, Imperva WAF, and DAM feeds into PostgreSQL warehouse.",
        "risks": "",
        "deps": "Kubernetes cluster / namespace readiness",
        "obstacles": "",
        "notes": "Configured with secret refs and volume mounts."
    },
    # Row 118
    {
        "phase": None,
        "task": "End-to-End Demo Execution Plan & Architecture Runbook",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 8, 25),
        "end": datetime(2026, 8, 26),
        "owner": "Takawira",
        "deliverable": "DEMO_PLAN.md & DEMO_SETUP.md — comprehensive end-to-end demonstration plan: AppScan Cloud Ingestion -> PostgreSQL Warehouse -> FastAPI -> React Dashboard, multi-app demo setup, SSH tunnels, and CronJob logs.",
        "risks": "",
        "deps": "AppScan test account & seeded database",
        "obstacles": "",
        "notes": "Includes narrative demo script and troubleshooting checklist."
    },
    # Row 119
    {
        "phase": None,
        "task": "Interactive Multi-Tenant Architecture Explorer (HTML)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 8),
        "end": datetime(2026, 9, 9),
        "owner": "Takawira",
        "deliverable": "architecture.html / frontend/public/architecture.html — standalone interactive visual architecture diagram showing 4-tier government hierarchy (SITA Command Center, National, Department, Branch) and DHA PoC testbed topology.",
        "risks": "",
        "deps": "Tenancy catalog & ORM models",
        "obstacles": "",
        "notes": "Embeddable interactive canvas with real-time tier switching."
    },
    # Row 120
    {
        "phase": None,
        "task": "Live Demonstration Walkthrough Guide (5 Stages)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 8),
        "end": datetime(2026, 9, 9),
        "owner": "Takawira",
        "deliverable": "WALKTHROUGH.md — 5-stage live demonstration operational script: Stage 1 (SITA Command Center), Stage 2 (Auditor-General SHA-256 Export), Stage 3 (DHA Dept Isolation), Stage 4 (Real AppScan Findings in AppSec Dashboard), Stage 5 (Thales DAM Cassandra Monitoring).",
        "risks": "",
        "deps": "Demo personas & seeded real telemetry",
        "obstacles": "",
        "notes": "Tested and verified across all 5 persona roles."
    },
    # Row 121
    {
        "phase": None,
        "task": "SITA Executive Presentation Deck (HTML & Markdown)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 8),
        "end": datetime(2026, 9, 10),
        "owner": "Takawira",
        "deliverable": "presentation.html, presentation.md, docs/SITA_Executive_Presentation_Deck.html/.md — high-impact 15-slide executive presentation deck for SITA enterprise leadership covering whole-of-government mandate, DHA PoC testbed, and OEM telemetry fusion.",
        "risks": "",
        "deps": "Executive review & architecture sign-off",
        "obstacles": "",
        "notes": "Dual format: markdown and responsive reveal/slide HTML."
    },
    # Row 122
    {
        "phase": None,
        "task": "Comprehensive 4-Tier RBAC & Zero-Leakage Demonstration Suite",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 9),
        "end": datetime(2026, 9, 10),
        "owner": "Takawira",
        "deliverable": "backend/test_api_comprehensive.py — automated end-to-end demonstration verification suite testing all 4 authentication tiers, 173 national departments, 50 real AppScan findings, 66 Thales DAM databases, 47 SOC alerts, 82.9% POPIA compliance, and strict 0 cross-tenant data leakage.",
        "risks": "",
        "deps": "FastAPI server on :8000 & seeded database",
        "obstacles": "",
        "notes": "100% pass across all tier authentication and isolation checks."
    },
    # Row 123
    {
        "phase": None,
        "task": "Test Exit Criteria & Quality Gates Specification (v1.1)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 9),
        "end": datetime(2026, 9, 10),
        "owner": "Takawira",
        "deliverable": "docs/SITA_Test_Exit_Criteria_and_Quality_Gates.xlsx & docs/test_exit_criteria.md — formal Quality Gate Specification defining 9 Quality Gates, 12 Quantitative Metrics, Defect Severity Matrix, and governance sign-offs across QA, Security, DHA PoC, and SITA Release Lead.",
        "risks": "",
        "deps": "Automated test suite & verification scripts",
        "obstacles": "",
        "notes": "All 9 Quality Gates PASSED (0 active defects across S1-S4)."
    },
    # Row 124
    {
        "phase": None,
        "task": "Master Test Case Execution Registry (173 Test Cases across 8 Domains)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 9),
        "end": datetime(2026, 9, 10),
        "owner": "Takawira",
        "deliverable": "docs/SITA_Platform_Test_Cases.xlsx — master test registry tracking 173 test cases across 8 domain sheets (144 baseline automated tests + 29 post-Sept 9th live verification & E2E demonstration tests) with 100% pass rate.",
        "risks": "",
        "deps": "pytest suite & live API test runner",
        "obstacles": "",
        "notes": "Comprehensive audit covering RBAC, DHA Demo, OEM Ingest, Risk Engine, Compliance, UI, and Post-Sept 9th live pipeline."
    },
    # Row 125
    {
        "phase": None,
        "task": "Live Ingestion Pipeline Verification Suite (verify_ingestion.py)",
        "status": "Completed",
        "pct": 1.0,
        "start": datetime(2026, 9, 9),
        "end": datetime(2026, 9, 10),
        "owner": "Takawira",
        "deliverable": "backend/scripts/verify_ingestion.py — end-to-end ingestion verification suite validating public summary, findings query, critical CVE extraction, 30-day fix rate, WAF blocks, and shadow API exposure.",
        "risks": "",
        "deps": "AppScan findings in PostgreSQL warehouse",
        "obstacles": "",
        "notes": "Verifies data flow from AppScan/warehouse to frontend dashboards."
    }
]

green_fill = PatternFill(start_color="FF92D050", end_color="FF92D050", fill_type="solid")

for idx, item in enumerate(new_deliverables):
    r = 112 + idx
    # Write values
    ws_plan.cell(row=r, column=1, value=None)
    ws_plan.cell(row=r, column=2, value=item["phase"])
    ws_plan.cell(row=r, column=3, value=item["task"])
    ws_plan.cell(row=r, column=4, value=item["status"])
    ws_plan.cell(row=r, column=5, value=item["pct"])
    ws_plan.cell(row=r, column=6, value=item["start"])
    ws_plan.cell(row=r, column=7, value=item["end"])
    ws_plan.cell(row=r, column=8, value=item["owner"])
    ws_plan.cell(row=r, column=9, value=item["deliverable"])
    ws_plan.cell(row=r, column=10, value=item["risks"])
    ws_plan.cell(row=r, column=11, value=item["deps"])
    ws_plan.cell(row=r, column=12, value=item["obstacles"])
    ws_plan.cell(row=r, column=13, value=item["notes"])

    # Copy styles from row 104
    for c in range(1, 14):
        src = ws_plan.cell(row=104, column=c)
        tgt = ws_plan.cell(row=r, column=c)
        if src.has_style:
            tgt.font = copy(src.font)
            tgt.border = copy(src.border)
            tgt.fill = copy(src.fill)
            tgt.number_format = copy(src.number_format)
            tgt.alignment = copy(src.alignment)
            tgt.protection = copy(src.protection)
            
    # Apply green fill to Status cell
    ws_plan.cell(row=r, column=4).fill = green_fill

# Also update row 106-111 fills
for r in [106, 107, 108, 109, 111]:
    ws_plan.cell(row=r, column=4).fill = green_fill

# ------------------------------------------------------------------------------
# 3. Update Summary Block in Project Plan Sheet (Rows 8, 9, 10)
# ------------------------------------------------------------------------------
print("Updating Project Plan summary counts...")
# Total activities: 86 original + 14 new = 100 activities
ws_plan.cell(row=8, column=5, value=100)
ws_plan.cell(row=8, column=6, value="99.5% Complete")
ws_plan.cell(row=9, column=5, value=99)
ws_plan.cell(row=10, column=5, value=1)

# ------------------------------------------------------------------------------
# 4. Update Milestones Sheet Formulas
# ------------------------------------------------------------------------------
print("Updating Milestones sheet formulas to encompass rows 14 to 125...")
# Overview block
ws_miles.cell(row=5, column=4, value="=AVERAGE('Project Plan '!E14:E125)")
ws_miles.cell(row=6, column=4, value="=COUNT('Project Plan '!E14:E125)")
ws_miles.cell(row=7, column=4, value='=COUNTIF(\'Project Plan \'!D14:D125,"Completed")')
ws_miles.cell(row=7, column=5, value='=COUNTIF(\'Project Plan \'!D14:D125,"WIP")')
ws_miles.cell(row=7, column=6, value='=COUNTIF(\'Project Plan \'!D14:D125,"Not started")')

# Phase 12 row in Milestones table (Row 21)
ws_miles.cell(row=21, column=4, value='=IF(COUNTIF(\'Project Plan \'!F106:F125,">0")=0,"TBC",_xlfn.MINIFS(\'Project Plan \'!F106:F125,\'Project Plan \'!F106:F125,">0"))')
ws_miles.cell(row=21, column=5, value='=IF(COUNTIF(\'Project Plan \'!G106:G125,">0")=0,"TBC",MAX(\'Project Plan \'!G106:G125))')
ws_miles.cell(row=21, column=6, value="=AVERAGE('Project Plan '!E106:E125)")

# Validation / reconciliation block
ws_miles.cell(row=53, column=4, value="=COUNT('Project Plan '!E106:E125)")
ws_miles.cell(row=57, column=4, value="=COUNT('Project Plan '!E14:E125)")

# ------------------------------------------------------------------------------
# 5. Update Doc Control Sheet
# ------------------------------------------------------------------------------
print("Updating Doc Control sheet...")
ws_doc.cell(row=4, column=1, value="Last Revised")
ws_doc.cell(row=4, column=2, value=datetime(2026, 9, 10))
ws_doc.cell(row=5, column=1, value="Revision Note")
ws_doc.cell(row=5, column=2, value="Updated with 14 post-20/08/2026 deliverables: Requirements, Master Test Plan, Manual QA Runbook, VAPT Remediation, HCL AppScan Connector, K8s CronJobs, Demo Setup, Architecture Explorer, Walkthrough Guide, Executive Deck, 4-Tier API Suite, Quality Gates, 173 Test Cases Registry, and Live Ingestion Suite.")

# Save updated workbook
wb.save(file_path)
print("SUCCESS: Flight plan successfully updated and saved!")
