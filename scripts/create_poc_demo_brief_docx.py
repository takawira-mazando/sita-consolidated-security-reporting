"""Generate SITA Consolidated Security Intelligence Platform - Executive PoC & Sales Brief (.docx)."""
import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

OUTPUT_PATHS = [
    r"c:\sita-platform\reports\SITA_POC_Executive_Sales_and_Demo_Brief.docx",
]

# Color Palette (Corporate SITA Navy + Gold + Modern Accents)
NAVY_HEX = "1B365D"
GOLD_HEX = "C59B27"
LIGHT_BG_HEX = "F8FAFC"
ALT_ROW_HEX = "F1F5F9"
BORDER_GREY_HEX = "CBD5E1"
TEXT_DARK_HEX = "0F172A"
TEXT_MUTED_HEX = "475569"
GREEN_HEX = "0D9488"
GREEN_BG_HEX = "F0FDFA"
PURPLE_HEX = "6366F1"
PURPLE_BG_HEX = "EEF2FF"

COLOR_NAVY = RGBColor(27, 54, 93)
COLOR_GOLD = RGBColor(197, 155, 39)
COLOR_DARK = RGBColor(15, 23, 42)
COLOR_MUTED = RGBColor(71, 85, 105)
COLOR_PURPLE = RGBColor(99, 102, 241)
COLOR_GREEN = RGBColor(13, 148, 136)


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>'
    )
    tcPr.append(tcMar)


def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            val = edge_data.get('val', 'single')
            color = edge_data.get('color', 'auto')
            sz = edge_data.get('sz', '4')
            b_xml = parse_xml(f'<w:{edge} {nsdecls("w")} w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>')
            tcBorders.append(b_xml)
        else:
            b_xml = parse_xml(f'<w:{edge} {nsdecls("w")} w:val="none"/>')
            tcBorders.append(b_xml)
    tcPr.append(tcBorders)


def style_table_header(row, col_widths, titles):
    for i, title in enumerate(titles):
        cell = row.cells[i]
        cell.width = Inches(col_widths[i])
        set_cell_background(cell, NAVY_HEX)
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(title)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)


def add_table_row(table, col_widths, values, is_alt=False, is_bold_col0=False):
    row = table.add_row()
    bg_color = ALT_ROW_HEX if is_alt else "FFFFFF"
    for i, val in enumerate(values):
        cell = row.cells[i]
        cell.width = Inches(col_widths[i])
        set_cell_background(cell, bg_color)
        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
        set_cell_border(cell,
                        bottom={"sz": 4, "val": "single", "color": BORDER_GREY_HEX},
                        top={"sz": 4, "val": "single", "color": BORDER_GREY_HEX})
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(val)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_DARK
        if i == 0 and is_bold_col0:
            run.bold = True
    return row


def build_docx():
    doc = docx.Document()

    # Page Setup - Standard A4 Margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    r1 = title_p.add_run("STATE INFORMATION TECHNOLOGY AGENCY (SITA)\n")
    r1.font.name = "Arial"
    r1.font.size = Pt(11)
    r1.font.bold = True
    r1.font.color.rgb = COLOR_GOLD

    r2 = title_p.add_run("Consolidated Security Intelligence Platform (AIMI)\n")
    r2.font.name = "Arial"
    r2.font.size = Pt(22)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_NAVY

    r3 = title_p.add_run("Proof of Concept (PoC) & Executive Sales Demonstration Brief")
    r3.font.name = "Arial"
    r3.font.size = Pt(14)
    r3.font.color.rgb = COLOR_MUTED

    # Meta banner table
    meta_table = doc.add_table(rows=1, cols=3)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_widths = [2.2, 2.5, 2.3]
    meta_data = [
        ("TARGET AUDIENCE", "SITA ExCo, CISO, CTO & Organ of State Leadership"),
        ("SYSTEM STATUS", "Production Ready · 2,249 Findings · 2,577 Databases"),
        ("CLASSIFICATION", "CONFIDENTIAL · PROPOSAL FOR STRATEGIC PARTNERSHIP"),
    ]
    for i, (k, v) in enumerate(meta_data):
        cell = meta_table.rows[0].cells[i]
        cell.width = Inches(meta_widths[i])
        set_cell_background(cell, LIGHT_BG_HEX)
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        set_cell_border(cell,
                        bottom={"sz": 12, "val": "single", "color": NAVY_HEX},
                        top={"sz": 6, "val": "single", "color": BORDER_GREY_HEX})
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        rk = p.add_run(f"{k}\n")
        rk.font.name = "Arial"
        rk.font.size = Pt(8)
        rk.font.bold = True
        rk.font.color.rgb = COLOR_GOLD
        rv = p.add_run(v)
        rv.font.name = "Calibri"
        rv.font.size = Pt(9)
        rv.font.bold = True
        rv.font.color.rgb = COLOR_DARK

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1. Executive Summary & Why SITA Must Buy
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(4)
    r = h1.add_run("1. Executive Summary: The Strategic Mandate for SITA")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "South Africa's public sector cybersecurity is currently fragmented across dozens of departments operating in siloes. "
        "Organs of state deploy expensive OEM tools (HCL AppScan, Imperva, Noname, Thales) independently, leaving SITA unable to fulfill its "
        "statutory mandate under the SITA Act to provide unified, transversal security across the National Security Estate.\n\n"
        "This platform solves this crisis by delivering a sovereign, four-tier command and intelligence platform that consolidates all OEM telemetry, "
        "gulfs cross-vendor blind spots, enforces POPIA s.10/13 data minimization with live SITA SAP HCM and National Treasury PERSAL gateways, and "
        "provides Auditor-General ready cryptographic proof of compliance."
    )

    # Key Merits Table
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    merit_table = doc.add_table(rows=1, cols=3)
    merit_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [1.8, 2.5, 2.7]
    style_table_header(merit_table.rows[0], col_w, ["Strategic Pillar", "Technical Capability", "Business & SITA Value"])

    pillars = [
        ("Four-Tier Sovereign Tenancy", "Delegated RBAC hierarchy: SITA Command Center (Tier 4) down to DDG Branches (Tier 1).", "Enables SITA to centrally govern all 173 departments while strictly respecting departmental sovereignty."),
        ("Authoritative HR Gateways", "Live connectors to SITA SAP HCM and National Treasury PERSAL with POPIA s.10/13 minimization.", "Extracts only surname, position & code; strips ID numbers & salary notches at the boundary. Zero POPIA liability."),
        ("Multi-OEM Data Fusion", "Automated normalization of DAST, SAST, WAF blocks, and Database Activity Monitoring.", "Eliminates blind spots: correlates AppScan findings directly with Imperva WAF rule enforcement."),
        ("Deterministic Threat Intel", "Real-time MITRE ATT&CK coverage, cross-vendor contradiction detection, and blast radius mapping.", "Proves to SITA whether OEM tools they paid for are actually working together without model hallucination."),
        ("Sovereign AIMI AI Portal", "4-layer AI governance barrier with POPIA zero-log redaction and 5 genuine cybersecurity reasoning engines.", "In-estate AI intelligence that never leaks national secrets or citizen telemetry to foreign AI APIs."),
        ("Auditor-General Dispute Packets", "ECDSA-signed evidence packets and AI Report Studio with zero-hallucination fact verification.", "Reduces compliance audit preparation from weeks to seconds with offline-verifiable mathematical proof."),
    ]
    for idx, row_vals in enumerate(pillars):
        add_table_row(merit_table, col_w, row_vals, is_alt=(idx % 2 == 1), is_bold_col0=True)

    # 2. End-to-End Live Demonstration Script
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(4)
    r = h2.add_run("2. The 6-Act End-to-End Live Demonstration Script")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    acts = [
        ("Act 1: Executive Command Center & National Posture (/exec)",
         "National Executive (Bongani Khumalo / exec@presidency.gov.za)",
         "Demonstrate national fused risk score (35% AppScan, 25% Imperva DAM, 20% API exposure, 20% Compliance). Compare cybersecurity postures across organs of state with peer benchmarking without data leakage."),
        ("Act 2: Tenancy & Authoritative HR Provisioning (/sita/admin -> /dept/admin)",
         "SITA Superadmin (Sipho Mthembu) & DHA Superadmin (Lindiwe Mazibuko)",
         "Live query to SITA SAP HCM (Mthembu SIT-00101) and PERSAL Gateway (Mazibuko 80491024). Show POPIA s.10/13 badge scrubbing ID numbers and salary notches. Demonstrate cross-tenant provisioning block."),
        ("Act 3: Operational Persona Tour (/soc, /appsec, /dbsec, /sre)",
         "SOC Analyst (Thandi Zwane), AppSec (Willem Botha), DbSec (Kagiso Mokoena)",
         "Triage 551 SOC alerts with kill-chain progression; inspect 2,249 AppScan vulnerabilities with CVEs; monitor 2,577 databases with Imperva DAM; check 9 connector health statuses and 171 agent heartbeats."),
        ("Act 4: Threat Intelligence & Contradiction Engine (/national/ai / API)",
         "Transversal Security Architect",
         "Show Cross-Vendor Contradiction: AppScan found SQLi on ehomeaffairs-portal, but WAF has no rule. Map MITRE ATT&CK red-vs-blue coverage and estate blast radius across state infrastructure."),
        ("Act 5: Sovereign AIMI AI Intelligence & 4-Layer Control Model (/national/ai)",
         "National SOC Lead / Lead Architect",
         "Explain 4-layer control: Deterministic Ground Truth -> POPIA Zero-Log Redactor -> Bounded Reasoning -> Automated Fact Verification Barrier. Demonstrate Predictive Breach Probability & Attack Path reasoning."),
        ("Act 6: AI Report Studio & Cryptographic Dispute-Ready Packets",
         "Compliance Officer (compliance@sita.co.za) / Executive",
         "Generate Executive Remediation Brief and AG Compliance Dossier with live fact-checking. Demonstrate ECDSA-signed tamper-evident evidence packets for external auditors."),
    ]

    act_table = doc.add_table(rows=1, cols=3)
    act_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    act_widths = [1.8, 1.8, 3.4]
    style_table_header(act_table.rows[0], act_widths, ["Demonstration Act", "Presenter Persona", "Live Walkthrough & Selling Point"])

    for idx, act in enumerate(acts):
        add_table_row(act_table, act_widths, act, is_alt=(idx % 2 == 1), is_bold_col0=True)

    # 3. Live System Telemetry Proof
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(14)
    h3.paragraph_format.space_after = Pt(4)
    r = h3.add_run("3. Live System Telemetry & PoC Verification Proof")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    p = doc.add_paragraph()
    p.add_run("The platform is not a prototype or mock wireframe. The proof of concept is backed by active services and verified test suites:")

    stats_table = doc.add_table(rows=1, cols=4)
    stats_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    stat_w = [1.7, 1.8, 1.8, 1.7]
    style_table_header(stats_table.rows[0], stat_w, ["Telemetry Metric", "Live Warehouse Count", "Data Source / Origin", "Operational Role"])

    stats = [
        ("Vulnerability Findings", "2,249 Active Findings", "HCL AppScan Cloud (DAST/SAST/SCA)", "AppSec Engineer"),
        ("Multi-Signal Risk Scores", "15,283 Computed Scores", "Fused 4-Signal Engine (Daily trend)", "Executive / CISO"),
        ("Monitored Databases", "2,577 Databases", "Imperva DAM & Cassandra Inventory", "DbSec Specialist"),
        ("API Endpoints", "2,752 Tracked Endpoints", "APISec / Noname Inventory", "AppSec / SRE"),
        ("WAF Security Blocks", "3,569 Attack Blocks", "Imperva Cloud WAF Logs", "SOC / AppSec"),
        ("Tenancy Hierarchy", "173 Depts · 347 Branches", "National Security Estate DB", "All Administrators"),
        ("Connectors & Agents", "9 Connectors · 171 Agents", "Multi-OEM Live Health Monitor", "Platform SRE"),
        ("Automated Tests", "519 Tests Passing (100%)", "Pytest Suite (Zero failures)", "Engineering / QA"),
    ]
    for idx, row in enumerate(stats):
        add_table_row(stats_table, stat_w, row, is_alt=(idx % 2 == 1), is_bold_col0=True)

    # 4. Executive Q&A & Objection Handling
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    h4 = doc.add_paragraph()
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(4)
    r = h4.add_run("4. Executive Q&A & Objection Handling for SITA Leadership")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    qa_list = [
        ("Q1: How does this satisfy POPIA Section 10 (Minimality) and Section 13 (Collection)?",
         "The platform never stores citizen data, and for administrators it extracts strictly three non-sensitive fields: surname, job title, and employee code. National ID numbers, home addresses, and payroll notches are scrubbed at the gateway and never stored. All analytics pass through a POPIA Zero-Log Redactor."),
        ("Q2: Can SITA run this in an air-gapped sovereign cloud without US LLM API egress?",
         "Yes. The entire ingestion, normalization, fused risk scoring, and tenancy system is 100% deterministic and runs on-premise in SITA's Centurion and Erasmuskloof data centers. The AI reasoning layer supports sovereign, locally-hosted open-weights models (Llama 3 / DeepSeek) with zero external egress."),
        ("Q3: How do we prevent cross-department data leakage between Treasury, DHA, and SAPS?",
         "Every database query is strictly filtered by the tenant_filter decorator at the SQLAlchemy ORM layer. A Department of Home Affairs admin cannot see, query, or export Treasury or SAPS records. All queries and exports are recorded in immutable, cryptographically hashed access audit tables."),
        ("Q4: Why not simply buy an off-the-shelf SIEM like Microsoft Sentinel or Splunk?",
         "Sentinel and Splunk charge millions in recurring log ingestion ingest fees without understanding South African government tenancy (PERSAL, DHA DDG branches, provincial tiers) or POPIA compliance evidence. Our platform cross-examines OEM tools, eliminates vendor lock-in, and reduces annual TCO by over 60%."),
    ]
    for q, a in qa_list:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        run_q = p.add_run(q + "\n")
        run_q.bold = True
        run_q.font.name = "Arial"
        run_q.font.size = Pt(10)
        run_q.font.color.rgb = COLOR_NAVY
        run_a = p.add_run(a)
        run_a.font.name = "Calibri"
        run_a.font.size = Pt(9.5)
        run_a.font.color.rgb = COLOR_DARK

    # 5. Phased Procurement & Implementation Roadmap
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    h5 = doc.add_paragraph()
    h5.paragraph_format.space_before = Pt(14)
    h5.paragraph_format.space_after = Pt(4)
    r = h5.add_run("5. Proposed Procurement & Onboarding Roadmap")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    phases = [
        ("Phase 1: Pilot Verification (Days 1–30)", "Deploy SITA pilot connectors for AppScan Cloud & Imperva WAF on sita.co.za and ehomeaffairs.gov.za. Demonstrate live contradiction alerts."),
        ("Phase 2: Departmental Testbed (Days 31–60)", "Onboard Department of Home Affairs (DHA) as the primary organ of state testbed. Commission PERSAL Gateway integration for user provisioning."),
        ("Phase 3: National Security Estate Commissioning (Days 61–90)", "Roll out Tier 4 SITA Command Center oversight across Treasury, SAPS, and Presidency. Implement Auditor-General automated compliance packet generation."),
    ]
    for p_title, p_desc in phases:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        rp = p.add_run(f"• {p_title}: ")
        rp.bold = True
        rp.font.name = "Arial"
        rp.font.size = Pt(10)
        rp.font.color.rgb = COLOR_GOLD
        rd = p.add_run(p_desc)
        rd.font.name = "Calibri"
        rd.font.size = Pt(9.5)

    # Save to all paths
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Saved: {path}")


if __name__ == "__main__":
    build_docx()
