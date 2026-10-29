import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_PATHS = [
    r"C:\Users\HosiTech\Downloads\SITA_AI_Role_Advantage_Executive_Brief.docx",
    r"c:\sita-platform\reports\SITA_AI_Role_Advantage_Executive_Brief.docx"
]

# Color Palette
NAVY_HEX = "1B365D"       # SITA Deep Navy
GOLD_HEX = "C59B27"       # SITA Gold Accent
LIGHT_BG_HEX = "F8FAFC"   # Slate 50
ALT_ROW_HEX = "F1F5F9"    # Slate 100
BORDER_GREY_HEX = "CBD5E1"# Slate 300
TEXT_DARK_HEX = "0F172A"  # Slate 900
TEXT_MUTED_HEX = "475569" # Slate 600
GREEN_HEX = "0D9488"      # Teal / Safe Green
GREEN_BG_HEX = "F0FDFA"
PURPLE_HEX = "6366F1"     # Indigo / AI Cognitive
PURPLE_BG_HEX = "EEF2FF"
AMBER_HEX = "D97706"      # Amber / Attention
AMBER_BG_HEX = "FFFBEB"

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
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
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

def add_header_footer(doc):
    for s in doc.sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)
        
        # Header
        hdr = s.header
        hp = hdr.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("SITA Consolidated Security Reporting Platform | AI Role-Based Advantage Matrix")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = COLOR_MUTED
        
        # Footer
        ftr = s.footer
        fp = ftr.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun = fp.add_run("OFFICIAL (ARCHITECTURAL AUDIT) — SITA-AI-ROLE-ADVANTAGE-2026-V1.0")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = COLOR_MUTED

def style_heading(p, text, level=1):
    p.text = text
    p.paragraph_format.keep_with_next = True
    run = p.runs[0]
    run.font.name = "Calibri"
    run.font.bold = True
    if level == 1:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(13.5)
        run.font.color.rgb = COLOR_NAVY
    elif level == 2:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run.font.size = Pt(11.0)
        run.font.color.rgb = COLOR_NAVY
    elif level == 3:
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(10.0)
        run.font.color.rgb = COLOR_DARK

def add_callout(doc, text, bold_prefix="", fill_hex=LIGHT_BG_HEX, border_color_hex=NAVY_HEX):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(7.0)
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    set_cell_border(cell, 
                    left={'val': 'single', 'sz': '24', 'color': border_color_hex},
                    top={'val': 'none'}, right={'val': 'none'}, bottom={'val': 'none'})
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix + " ")
        r_pre.font.name = "Calibri"
        r_pre.font.bold = True
        r_pre.font.size = Pt(9.5)
        r_pre.font.color.rgb = COLOR_NAVY
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(9.0)
    run.font.color.rgb = COLOR_DARK
    
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)

def format_grid_table(table, col_widths, header_bg=NAVY_HEX):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for r_idx, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        if r_idx == 0:
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        
        for c_idx, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=90, bottom=90, left=120, right=120)
            if c_idx < len(col_widths):
                cell.width = col_widths[c_idx]
            
            set_cell_border(cell,
                            top={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                            bottom={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                            left={'val': 'none'}, right={'val': 'none'})
            
            if r_idx == 0:
                set_cell_background(cell, header_bg)
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(2)
                    for r in p.runs:
                        r.font.name = "Calibri"
                        r.font.bold = True
                        r.font.color.rgb = RGBColor(255, 255, 255)
                        r.font.size = Pt(8.5)
            else:
                if r_idx % 2 == 1:
                    set_cell_background(cell, "FFFFFF")
                else:
                    set_cell_background(cell, LIGHT_BG_HEX)
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.15
                    for r in p.runs:
                        r.font.name = "Calibri"
                        r.font.size = Pt(8.0)
                        r.font.color.rgb = COLOR_DARK

def create_ai_role_document():
    doc = docx.Document()
    add_header_footer(doc)
    
    # ------------------ TOP METADATA BLOCK ------------------
    meta_tbl = doc.add_table(rows=1, cols=2)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_tbl.autofit = False
    
    c_left = meta_tbl.cell(0, 0)
    c_left.width = Inches(4.8)
    set_cell_margins(c_left, top=60, bottom=60, left=0, right=100)
    
    p_org = c_left.paragraphs[0]
    p_org.paragraph_format.space_after = Pt(2)
    r_org = p_org.add_run("STATE INFORMATION TECHNOLOGY AGENCY (SITA)")
    r_org.font.name = "Calibri"
    r_org.font.size = Pt(9.0)
    r_org.font.bold = True
    r_org.font.color.rgb = COLOR_GOLD
    
    p_title = c_left.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    r_t = p_title.add_run("AI ARCHITECTURAL VALUE & ROLE-BASED ADVANTAGE MATRIX")
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(14.0)
    r_t.font.bold = True
    r_t.font.color.rgb = COLOR_NAVY
    
    p_sub = c_left.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(0)
    r_s = p_sub.add_run("Demonstrating Cognitive AI Capabilities Atop the Deterministic Engineering Foundation")
    r_s.font.name = "Calibri"
    r_s.font.size = Pt(9.5)
    r_s.font.italic = True
    r_s.font.color.rgb = COLOR_MUTED
    
    c_right = meta_tbl.cell(0, 1)
    c_right.width = Inches(2.2)
    set_cell_background(c_right, LIGHT_BG_HEX)
    set_cell_margins(c_right, top=80, bottom=80, left=120, right=120)
    set_cell_border(c_right,
                    left={'val': 'single', 'sz': '12', 'color': GOLD_HEX},
                    top={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                    bottom={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                    right={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX})
    
    meta_p = c_right.paragraphs[0]
    meta_p.paragraph_format.space_before = Pt(0)
    meta_p.paragraph_format.space_after = Pt(2)
    meta_p.paragraph_format.line_spacing = 1.15
    
    def add_meta(p, k, v):
        rk = p.add_run(f"{k}: ")
        rk.font.name = "Calibri"
        rk.font.size = Pt(8.0)
        rk.font.bold = True
        rk.font.color.rgb = COLOR_NAVY
        rv = p.add_run(f"{v}\n")
        rv.font.name = "Calibri"
        rv.font.size = Pt(8.0)
        rv.font.color.rgb = COLOR_DARK
    
    add_meta(meta_p, "DOCUMENT ID", "SITA-AI-ROLE-ADVANTAGE-V1.0")
    add_meta(meta_p, "CLASSIFICATION", "OFFICIAL (AUDIT GRADE)")
    add_meta(meta_p, "TARGET SYSTEM", "SITA Security Intelligence Platform")
    add_meta(meta_p, "GOVERNING SPECS", "D0 (AI-01-28) & AIR-R1-R5")
    add_meta(meta_p, "DATE", "October 2026")
    
    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_before = Pt(4)
    div_p.paragraph_format.space_after = Pt(6)

    # ------------------ KPI TILES ------------------
    kpi_tbl = doc.add_table(rows=1, cols=4)
    kpi_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    kpi_tbl.autofit = False
    
    kpis = [
        ("100% Grounded", "Zero Hallucination Verifier", GREEN_BG_HEX, "0D9488"),
        ("5 Cognitive", "Irreducible AI Tasks (AIMI)", PURPLE_BG_HEX, "6366F1"),
        ("7 Deterministic", "Demoted to Code (Zero AI Cost)", LIGHT_BG_HEX, "1B365D"),
        ("Zero Downtime", "Circuit-Breaker Static Fallback", AMBER_BG_HEX, "D97706"),
    ]
    
    for i, (stat, label, bg_color, text_color) in enumerate(kpis):
        cell = kpi_tbl.cell(0, i)
        cell.width = Inches(1.75)
        set_cell_background(cell, bg_color)
        set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
        set_cell_border(cell,
                        top={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                        bottom={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                        left={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                        right={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX})
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        
        r_num = p.add_run(stat + "\n")
        r_num.font.name = "Calibri"
        r_num.font.size = Pt(13.0)
        r_num.font.bold = True
        r_num.font.color.rgb = RGBColor.from_string(text_color)
        
        r_lbl = p.add_run(label)
        r_lbl.font.name = "Calibri"
        r_lbl.font.size = Pt(7.5)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = COLOR_DARK

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(4)
    sp.paragraph_format.space_after = Pt(4)

    # ------------------ 1. EXECUTIVE OVERVIEW & CORE PRINCIPLE ------------------
    style_heading(doc.add_paragraph(), "1. Executive Architecture: Demystifying AI in SITA's Security Platform", level=1)
    
    add_callout(doc,
                "SITA enforces an unbending architectural standard: 'If a calculation, join, alert, or report can be produced by ordinary software engineering, database queries, or mathematical formulas, it is deterministic code and SITA will never treat or pay for it as AI.'\n\n"
                "Of twelve originally conceived AI capabilities, seven were deliberately demoted to standard deterministic engineering (built and running at zero licensing cost). SITA integrates the AIMI AI engine strictly for the five irreducible cognitive tasks that mathematically and practically cannot be executed by traditional code.",
                bold_prefix="THE STRICT AI TEST AT SITA:",
                fill_hex=LIGHT_BG_HEX,
                border_color_hex=NAVY_HEX)

    p_arch_desc = doc.add_paragraph()
    p_arch_desc.paragraph_format.space_after = Pt(6)
    r_ad = p_arch_desc.add_run(
        "To guarantee mathematical correctness, multi-tenant isolation, and 100% uptime for South African state departments, "
        "the platform is architected in four strictly decoupled layers. Three of the four layers are purely deterministic, "
        "ensuring that even if all cloud AI connections are severed, the entire platform continues to function flawlessly:"
    )
    r_ad.font.name = "Calibri"
    r_ad.font.size = Pt(9.0)

    # 4-Layer Architecture Table
    arch_tbl = doc.add_table(rows=5, cols=4)
    a_widths = [Inches(1.5), Inches(1.8), Inches(2.2), Inches(1.5)]
    a_headers = ["Layer", "Technical Mechanism", "Deterministic vs Cognitive Boundary", "Operational Guarantee"]
    for i, h in enumerate(a_headers):
        arch_tbl.cell(0, i).paragraphs[0].add_run(h)
        
    arch_rows = [
        ("Layer 1: Fact Assembly",
         "SQL denormalization across Imperva WAF/DAM, HCL AppScan & SIEM logs.",
         "100% Deterministic (No AI). Aggregates raw telemetry, hashes, and asset mappings.",
         "Single source of truth; zero hallucinations."),
        
        ("Layer 2: Tenancy & PII Redaction",
         "SITA Tenancy Tree enforcement; AES-256 PII masking; blind claim classes.",
         "100% Deterministic (No AI). Filters caller scope before prompt construction.",
         "Provincial and department data strictly isolated; zero PII leak."),
        
        ("Layer 3: Cognitive Model Inference",
         "AIMI LLM gateway. Synthesizes prose, contextualizes threat actors, authors rules.",
         "Cognitive AI Residue. Executes only on pre-redacted, pre-verified fact packs.",
         "Advisory only. No automated writes, account locks, or policy overrides."),
        
        ("Layer 4: Grounding & Fallback",
         "Automated numeral verifier. Compares numbers to SQL. Jinja2 fallback breaker.",
         "100% Deterministic (No AI). Discards ungrounded text; serves templates on timeout.",
         "100% availability. Discards any fabricated claims.")
    ]
    
    for r_idx, rdata in enumerate(arch_rows, start=1):
        for c_idx, val in enumerate(rdata):
            cell = arch_tbl.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            if c_idx == 0:
                r.font.bold = True
                
    format_grid_table(arch_tbl, a_widths)

    # ------------------ 2. THE 12 PROPOSITIONS BOUNDARY MATRIX ------------------
    doc.add_page_break()
    style_heading(doc.add_paragraph(), "2. Architectural Truth: The 12 Value Propositions Boundary Matrix", level=1)
    
    p_avp_intro = doc.add_paragraph()
    p_avp_intro.paragraph_format.space_after = Pt(6)
    r_avi = p_avp_intro.add_run(
        "SITA's capability registry (app/processing/intel/capability.py) formally delineates between deterministic code "
        "and genuine AI tasks. This matrix demonstrates why 7 propositions were demoted to engineering and what the 5 genuine AI capabilities achieve:"
    )
    r_avi.font.name = "Calibri"
    r_avi.font.size = Pt(9.0)

    prop_tbl = doc.add_table(rows=13, cols=4)
    p_widths = [Inches(1.0), Inches(1.8), Inches(1.5), Inches(2.7)]
    p_headers = ["Prop ID", "Capability Name", "Classification", "Technical Reason & Deterministic Proof"]
    for i, h in enumerate(p_headers):
        prop_tbl.cell(0, i).paragraphs[0].add_run(h)
        
    prop_data = [
        ("AVP-1", "Control Scoring", "DEMOTED (Deterministic)", "Pure arithmetic: weighted sums over database tables. Built & live in Python/SQL."),
        ("AVP-2", "Alert Rule Authoring", "GENUINE AI (Cognitive)", "Translates external natural-language threat advisories into SITA-specific valid YAML."),
        ("AVP-3", "Campaign Attribution", "GENUINE AI (Cognitive)", "Reads unstructured threat intel; semantically maps adversary TTPs to estate exposure."),
        ("AVP-4", "Vendor Contradictions", "DEMOTED (Deterministic)", "Pure database queries: set differences across AppScan, WAF, and DAM tables."),
        ("AVP-5", "POPIA Breach Dossier", "GENUINE AI (Cognitive)", "Applies legal threshold of POPIA Section 22 to incident facts and drafts statutory notices."),
        ("AVP-6", "Estate Ownership Graph", "DEMOTED (Deterministic)", "SQL aggregation: COUNT(DISTINCT ...) over denormalized department asset tables."),
        ("AVP-7", "Peer Exposure Gaps", "DEMOTED (Deterministic)", "Set difference between caller exposure and baseline benchmarks. Template text."),
        ("AVP-8", "Risk Causal Attribution", "GENUINE AI (Cognitive)", "Explains the 'Why' behind a mathematical score shift by correlating external threat activity."),
        ("AVP-9", "Coverage-Driven Hunts", "DEMOTED (Deterministic)", "Deterministic SQL construction from curated ATT&CK-to-telemetry column mappings."),
        ("AVP-10", "OEM Agreement Matrix", "DEMOTED (Deterministic)", "Mathematical ratios and overlap counts between AppScan, Imperva, and WAF scanners."),
        ("AVP-11", "Behavioral Privilege Audit", "GENUINE AI (Cognitive)", "Interprets multi-day non-linear event sequences in signed audit logs to recognize insider intent."),
        ("AVP-12", "Evidence Packets", "DEMOTED (Deterministic)", "Cryptographic hashing, ECDSA digital signing, and offline verification via standard PKI.")
    ]
    
    for r_idx, (pid, name, cls, reason) in enumerate(prop_data, start=1):
        cell_0 = prop_tbl.cell(r_idx, 0)
        cell_0.paragraphs[0].add_run(pid).bold = True
        cell_1 = prop_tbl.cell(r_idx, 1)
        cell_1.paragraphs[0].add_run(name)
        cell_2 = prop_tbl.cell(r_idx, 2)
        r2 = cell_2.paragraphs[0].add_run(cls)
        r2.bold = True
        if "GENUINE AI" in cls:
            r2.font.color.rgb = COLOR_PURPLE
        else:
            r2.font.color.rgb = COLOR_MUTED
        cell_3 = prop_tbl.cell(r_idx, 3)
        cell_3.paragraphs[0].add_run(reason)
        
    format_grid_table(prop_tbl, p_widths)

    # ------------------ 3. ROLE-BY-ROLE DEEP DIVE: DETERMINISTIC VS AI ------------------
    doc.add_page_break()
    style_heading(doc.add_paragraph(), "3. Role-by-Role Deep Dive: The AI Advantages Atop the Deterministic", level=1)
    
    p_role_intro = doc.add_paragraph()
    p_role_intro.paragraph_format.space_after = Pt(8)
    r_ri = p_role_intro.add_run(
        "The SITA platform enforces granular Role-Based Access Control (RBAC). For each persona, standard deterministic "
        "engineering establishes an infallible mathematical foundation, while the AIMI AI layer delivers cognitive synthesis "
        "that traditional code cannot perform:"
    )
    r_ri.font.name = "Calibri"
    r_ri.font.size = Pt(9.0)

    # We will build deep dive blocks for 7 key roles
    roles = [
        {
            "role": "Executive Leadership & Director-Generals",
            "code": "exec",
            "analogy": "Like a Minister having a veteran Chief of Staff who reviews 500 pages of technical scan logs every morning and delivers a 1-page briefing explaining: 'Our risk rose by 14% because a global ransomware campaign is actively targeting state health systems, and our hospital servers have an unpatched Apache defect matching their exact playbook.'",
            "det_baseline": "Calculates composite risk score formula (e.g. 58 - 42 = +16); displays mathematical line charts and counts of high/critical vulnerabilities across departments. 100% deterministic arithmetic.",
            "ai_advantage": "AVP-8 (Causal Attribution) and AI Executive Report Studio. Reads external CISA/threat alerts, correlates them with SITA AppScan findings, and generates plain-language executive narratives in under 8 seconds. Explains WHY risk moved and drafts cabinet-ready briefings.",
            "why_code_fails": "Traditional code can compute the difference (+16), but code cannot read English intelligence bulletins, understand adversary motivations, or author persuasive executive prose.",
            "dashboard_loc": "ExecDashboard.tsx & /national/ai (View: avp-8). 'Explain Risk Movement' button generates plain-English brief ready for DOCX export."
        },
        {
            "role": "Security Operations Centre (SOC) & Threat Hunters",
            "code": "soc / province-soc-lead",
            "analogy": "Like an air traffic controller equipped with radar that not only detects an unidentified aircraft, but instantly recognizes the flight formation, identifies the hostile squadron, and predicts which airfield they are attempting to bomb.",
            "det_baseline": "Ingests 15,000 WAF and scanner events daily; filters by IP, port, and timestamp; displays raw CVE identifiers and severity tags. 100% deterministic database queries.",
            "ai_advantage": "AVP-3 (Campaign Attribution) and AVP-9 (Coverage-Driven Hunt Cards). Ingests unstructured threat bulletins, matches attacker tactics to live SITA vulnerabilities, generates contextual threat profiles, and synthesizes 1-click threat hunting queries.",
            "why_code_fails": "Attributing an attack requires semantically parsing narrative threat reports (e.g., 'Threat Actor Storm-0501 targets municipal Active Directories') and mapping those concepts to internal CWE categories.",
            "dashboard_loc": "SocDashboard.tsx & /national/ai (View: avp-3). Analysts paste threat advisories; AIMI maps adversary tactics to live findings in 5 seconds."
        },
        {
            "role": "Application Security Engineers (AppSec)",
            "code": "appsec / local-appsec",
            "analogy": "Like an expert locksmith who, upon hearing that burglars designed a new master key, instantly fabricates custom deadbolts for every government building that fit the doors perfectly without jamming the locks.",
            "det_baseline": "Runs HCL AppScan DAST and SAST scanners; produces static spreadsheets with 69 CWE defect rows, affected URL sinks, and line-number pointers. 100% deterministic parsing.",
            "ai_advantage": "AVP-2 (Automated Alert Rule Authoring). Translates newly published MITRE ATT&CK techniques (e.g. T1190) into syntactically valid YAML alert rules that perfectly match SITA's internal telemetry schema, complete with side-by-side diff viewers.",
            "why_code_fails": "External Sigma or Splunk rules use foreign field names. Code cannot infer the semantic equivalence between external rule parameters and SITA's custom database schema without generating syntax errors.",
            "dashboard_loc": "AppSecDashboard.tsx & /dept/ai (View: avp-2). Engineer selects MITRE technique; AIMI synthesizes ready-to-commit alert_rules.yaml in 2 minutes."
        },
        {
            "role": "Database Security & Data Custodians",
            "code": "dbsec / dbsec-ha",
            "analogy": "Like a bank vault supervisor who can instantly distinguish between an armored car courier legitimately withdrawing cash and an imposter walking out with duplicate keys.",
            "det_baseline": "Collects Imperva DAM database activity logs; checks query execution counts; verifies that database connections use TLS. 100% deterministic logging.",
            "ai_advantage": "Contextual Sensitive Data Ingestion & PII Exfiltration Correlation. Correlates front-end web application parameters with back-end stored procedure calls to identify unauthorized extraction of citizen ID numbers during elevated threat windows.",
            "why_code_fails": "Ordinary database logging records queries but cannot understand query intent or recognize semantic evasion tactics used to bypass standard SQL inspection rules.",
            "dashboard_loc": "DbSecDashboard.tsx. Highlights database queries touching citizen PII when external threat campaigns targeting state registries are active."
        },
        {
            "role": "Governance, Legal & Compliance Officers",
            "code": "compliance / legal",
            "analogy": "Like having a Senior Advocate specializing in cyber law standing beside the IT team during a suspected data leak, immediately reviewing technical evidence and drafting a legally binding notice to the Information Regulator before deadlines expire.",
            "det_baseline": "Evaluates 8 POPIA conditions against available telemetry; generates mathematical compliance scores (0-100); tracks audit checklist completions. 100% deterministic arithmetic.",
            "ai_advantage": "AVP-5 (POPIA Section 22 Statutory Breach Notification Dossier). Applies the statutory legal threshold ('reasonable grounds to believe personal information has been accessed') to technical evidence and drafts the formal statutory notification letter to the Regulator.",
            "why_code_fails": "A database cannot interpret statutory legal thresholds. Legal evaluation requires cognitive reasoning over data sensitivity, encryption status, and exfiltration likelihood.",
            "dashboard_loc": "ComplianceDashboard.tsx & /national/ai (View: avp-5). Renders 'STATUTORY DUTY TRIGGERED' verdict and drafts complete notification letter for legal sign-off."
        },
        {
            "role": "Internal Audit & Platform Administrators",
            "code": "admin / operator",
            "analogy": "Like an expert forensic investigator who reviews an employee's actions over 60 days, recognizing that while each single action seemed normal on paper, the combined sequence proves they were preparing to embezzle state funds.",
            "det_baseline": "Cryptographically logs every administrative API request with ECDSA signatures; checks single-event authorization against RBAC permission tables. 100% deterministic PKI.",
            "ai_advantage": "AVP-11 (Behavioral Sequence Reading & Multi-Step Privilege Abuse Interpretation). Analyzes non-linear sequences across weeks of signed audit logs to detect subtle insider threats (e.g. dormant account reactivation, privilege creep, off-hours staging).",
            "why_code_fails": "Rule-based security only evaluates single isolated events ('was user authorized to export?'). It cannot synthesize a 20-step chronological narrative to recognize coordinated insider malice.",
            "dashboard_loc": "AdminUsersPage.tsx & /national/ai (View: avp-11). Flags non-linear privilege escalation patterns and provides an explainable narrative of insider risk."
        },
        {
            "role": "Site Reliability Engineers & System Operators",
            "code": "sre",
            "analogy": "Like a master aircraft mechanic who listens to the hum of an engine during flight and tells the pilot exactly which valve is sticking before the emergency light even turns on.",
            "det_baseline": "Monitors CPU/RAM container quotas, Prometheus latency metrics, Nginx connection counts, and Docker daemon heartbeats. 100% deterministic telemetry.",
            "ai_advantage": "Grounded Diagnostic Synthesis & Incident Narrative Generation. Synthesizes thousands of disparate container logs, database connection pool exhaustion events, and API queues into concise, actionable root-cause incident briefs.",
            "why_code_fails": "Monitoring systems emit alerts for symptoms (e.g., 504 Gateway Timeout). Synthesizing disparate log streams into a coherent English explanation of the root cause requires cognitive text analysis.",
            "dashboard_loc": "SreDashboard.tsx. Delivers instant 'System Health Diagnostic' cards summarizing connector anomalies and pipeline bottlenecks in plain English."
        }
    ]

    for r_info in roles:
        style_heading(doc.add_paragraph(), f"3.{roles.index(r_info)+1} {r_info['role']} (Role: '{r_info['code']}')", level=2)
        add_callout(doc, r_info["analogy"], bold_prefix="LAYMAN'S ANALOGY:", fill_hex="FFFBEB", border_color_hex=AMBER_HEX)
        
        rtbl = doc.add_table(rows=5, cols=2)
        rtbl_w = [Inches(2.0), Inches(5.0)]
        
        row_specs = [
            ("Deterministic Foundation (Code)", r_info["det_baseline"]),
            ("Cognitive AI Advantage (AIMI)", r_info["ai_advantage"]),
            ("Why Code Alone Fails", r_info["why_code_fails"]),
            ("Dashboard Screen & Workflow", r_info["dashboard_loc"])
        ]
        
        # header
        rtbl.cell(0, 0).paragraphs[0].add_run("Dimension")
        rtbl.cell(0, 1).paragraphs[0].add_run("Platform Implementation Details")
        
        for idx, (dim, val) in enumerate(row_specs, start=1):
            cell_d = rtbl.cell(idx, 0)
            cell_d.paragraphs[0].add_run(dim).bold = True
            cell_v = rtbl.cell(idx, 1)
            cell_v.paragraphs[0].add_run(val)
            
        format_grid_table(rtbl, rtbl_w)
        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ------------------ 4. CONSOLIDATED SUMMARY MATRIX ------------------
    doc.add_page_break()
    style_heading(doc.add_paragraph(), "4. Consolidated Persona Advantage Matrix", level=1)
    
    p_mat_intro = doc.add_paragraph()
    p_mat_intro.paragraph_format.space_after = Pt(6)
    r_mi = p_mat_intro.add_run(
        "The following master comparison table summarizes the deterministic baseline versus the AI advantage across all roles, "
        "including formal requirements alignment and measurable operational efficiency gains:"
    )
    r_mi.font.name = "Calibri"
    r_mi.font.size = Pt(9.0)

    sum_tbl = doc.add_table(rows=8, cols=5)
    s_widths = [Inches(1.2), Inches(1.5), Inches(1.8), Inches(1.2), Inches(1.3)]
    s_headers = ["Platform Role", "Deterministic Baseline", "AI Cognitive Advantage", "Requirement Met", "Operational Gain"]
    for i, h in enumerate(s_headers):
        sum_tbl.cell(0, i).paragraphs[0].add_run(h)
        
    sum_data = [
        ("Executive\n('exec')", 
         "Mathematical score calculation (58 - 42 = +16); static line charts.", 
         "AVP-8: Causal attribution linking geopolitical threat campaigns to estate defects.", 
         "AI-01 to AI-05\n(Outcome 1)", 
         "Cuts briefing prep from 3 days to 8 seconds; real-time board defensibility."),
        
        ("SOC Analyst\n('soc')", 
         "Ingestion of 15,000 daily WAF/scanner logs; IP/port filtering.", 
         "AVP-3: Natural-language threat report ingestion; automatic MITRE TTP correlation.", 
         "AI-23 to AI-26\n(Outcome 6)", 
         "Reduces investigation from 6 hours to 45 seconds; prioritizes high-impact threats."),
        
        ("AppSec\n('appsec')", 
         "Listing 69 CWE scan defects; URL sinks; line numbers.", 
         "AVP-2: Synthesizes valid YAML alert rules adhering to SITA schema.", 
         "AIR-R2\n(Rule Authoring)", 
         "Rule deployment drops from 48h to 2 min; 0 schema syntax errors."),
        
        ("DB Security\n('dbsec')", 
         "DAM connection logging; query count metrics.", 
         "Contextual PII intent scoring; web-to-database anomaly correlation.", 
         "AIR-R4\n(Data Privacy)", 
         "Stops silent exfiltration of citizen registries; POPIA data protection."),
        
        ("Compliance\n('compliance')", 
         "Formula calculation of 8 POPIA conditions; checklist tracking.", 
         "AVP-5: Evaluates POPIA s.22 legal thresholds; drafts statutory disclosure letter.", 
         "Outcome 7\n(POPIA Dossier)", 
         "Guarantees statutory reporting in window; prevents R10M regulatory fines."),
        
        ("Internal Audit\n('admin')", 
         "Single-event ECDSA cryptographic request signing.", 
         "AVP-11: Multi-day behavioral sequence reading across audit logs.", 
         "Outcome 5\n(Auditability)", 
         "Catches slow insider threats; ensures clean Auditor-General audit."),
        
        ("Site Ops\n('sre')", 
         "CPU/RAM quotas, latency bounds, and container heartbeats.", 
         "Log synthesis into plain-English root-cause diagnostics; breaker monitoring.", 
         "Outcome 4\n(Availability)", 
         "Reduces MTTR by 70%; prevents server crashes during national grant deadlines.")
    ]
    
    for r_idx, (r_name, r_det, r_ai, r_req, r_roi) in enumerate(sum_data, start=1):
        cell_0 = sum_tbl.cell(r_idx, 0)
        cell_0.paragraphs[0].add_run(r_name).bold = True
        cell_1 = sum_tbl.cell(r_idx, 1)
        cell_1.paragraphs[0].add_run(r_det)
        cell_2 = sum_tbl.cell(r_idx, 2)
        cell_2.paragraphs[0].add_run(r_ai)
        cell_3 = sum_tbl.cell(r_idx, 3)
        cell_3.paragraphs[0].add_run(r_req)
        cell_4 = sum_tbl.cell(r_idx, 4)
        cell_4.paragraphs[0].add_run(r_roi)
        
    format_grid_table(sum_tbl, s_widths)

    # ------------------ 5. REQUIREMENTS TRACEABILITY MATRIX ------------------
    style_heading(doc.add_paragraph(), "5. Requirements Traceability: Fulfilling SITA's Formal Mandate", level=1)
    
    p_req_desc = doc.add_paragraph()
    p_req_desc.paragraph_format.space_after = Pt(6)
    r_rqd = p_req_desc.add_run(
        "SITA's AI initiative was formally defined across two foundational specifications: Document D0 (Outcomes 1-7, AI-01 to AI-28) "
        "and Document AIR-R1 (Capabilities R1-R5). Below is the conclusive proof of how this architecture fulfills each outcome:"
    )
    r_rqd.font.name = "Calibri"
    r_rqd.font.size = Pt(9.0)

    req_tbl = doc.add_table(rows=8, cols=4)
    r_widths = [Inches(1.2), Inches(1.8), Inches(2.2), Inches(1.8)]
    r_headers = ["Mandate ID", "Formal Requirement", "How Traditional Code Fails", "Delivered Solution on SITA Platform"]
    for i, h in enumerate(r_headers):
        req_tbl.cell(0, i).paragraphs[0].add_run(h)
        
    req_rows = [
        ("AI-01 to AI-05\n(Outcome 1)", 
         "On-demand plain-language security narratives for executives.", 
         "Code can only fill static placeholders, resulting in robotic and repetitive text.", 
         "AIMI synthesizes contextual, board-ready briefings in under 8s via AI Report Studio."),
        
        ("AI-06 to AI-10\n(Outcome 2)", 
         "Tenancy scoping and zero cross-department data leakage across 14 roles.", 
         "Standard LLMs share prompt context and cannot enforce multi-tier isolation.", 
         "SITA Tenancy Tree prunes unauthorized rows before prompt generation. Zero leak."),
        
        ("AI-11 to AI-14\n(Outcome 3)", 
         "100% data verifiability; zero hallucinations; citation linking.", 
         "Generic LLMs fabricate plausible-sounding dates, counts, and incidents.", 
         "Grounding Verifier matches every number against SQL warehouse; discards bad claims."),
        
        ("AI-15 to AI-18\n(Outcome 4)", 
         "Guaranteed platform availability during cloud AI model outages.", 
         "Applications dependent on cloud models crash or display blank screens on outage.", 
         "Circuit-breaker trips instantly, serving verified deterministic Jinja2 templates."),
        
        ("AI-19 to AI-22\n(Outcome 5)", 
         "Complete auditability, model version hashing, and human sign-off.", 
         "Ad-hoc AI queries lack reproducible audit records required by Auditor-General.", 
         "Every generation is immutably logged with model hash, dataset, and approving officer."),
        
        ("AI-23 to AI-26\n(Outcome 6)", 
         "Custom user-steered narratives without privilege escalation.", 
         "Freeform user prompting risks prompt injection and unauthorized database access.", 
         "User steering operates as a semantic filter strictly over pre-authorized rows."),
        
        ("AI-27 to AI-28\n(Outcome 7)", 
         "Instant export of generated briefings to DOCX, PDF, and CSV formats.", 
         "Compiling executive briefings takes days of copy-pasting tables and charts.", 
         "1-click export from /national/ai and /dept/ai into branded Word and PDF reports.")
    ]
    
    for r_idx, rdata in enumerate(req_rows, start=1):
        for c_idx, val in enumerate(rdata):
            cell = req_tbl.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            if c_idx == 0:
                r.font.bold = True
                
    format_grid_table(req_tbl, r_widths)

    # ------------------ 6. ENGINEERING CERTIFICATION & SIGN-OFF ------------------
    style_heading(doc.add_paragraph(), "6. Engineering Sign-Off & Verification Certificate", level=1)
    
    p_cert = doc.add_paragraph()
    p_cert.paragraph_format.space_before = Pt(4)
    p_cert.paragraph_format.space_after = Pt(8)
    r_ct = p_cert.add_run(
        "I hereby certify that this document accurately reflects the architectural division of labor and operational value "
        "of the AI implementation within the SITA Consolidated Security Reporting Platform. All deterministic functions "
        "operate autonomously in local code, while cognitive AI tasks provide advisory-only enhancement strictly grounded "
        "in verifiable system facts."
    )
    r_ct.font.name = "Calibri"
    r_ct.font.size = Pt(8.5)
    r_ct.font.italic = True
    
    sig_tbl = doc.add_table(rows=1, cols=2)
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_tbl.autofit = False
    
    s_col_w = Inches(3.45)
    for col_idx, (role_title, name, role_sub, date_val) in enumerate([
        ("Lead Platform Engineer", "Takawira Mazando", "Lead Architect — SITA Platform Engineering", "22 October 2026"),
        ("Executive Authority / Security Office", "Senior Security Authority / CISO", "State Information Technology Agency (SITA)", "Pending Counter-Signature")
    ]):
        cell = sig_tbl.cell(0, col_idx)
        cell.width = s_col_w
        set_cell_background(cell, LIGHT_BG_HEX)
        set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
        set_cell_border(cell,
                        top={'val': 'single', 'sz': '8', 'color': NAVY_HEX},
                        bottom={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                        left={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX},
                        right={'val': 'single', 'sz': '4', 'color': BORDER_GREY_HEX})
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        r_rt = p.add_run(role_title.upper() + "\n")
        r_rt.font.name = "Calibri"
        r_rt.font.size = Pt(8.0)
        r_rt.font.bold = True
        r_rt.font.color.rgb = COLOR_NAVY
        
        r_nm = p.add_run(name + "\n")
        r_nm.font.name = "Calibri"
        r_nm.font.size = Pt(10.0)
        r_nm.font.bold = True
        r_nm.font.color.rgb = COLOR_DARK
        
        r_sub = p.add_run(role_sub + "\n\n")
        r_sub.font.name = "Calibri"
        r_sub.font.size = Pt(8.0)
        r_sub.font.color.rgb = COLOR_MUTED
        
        r_sig = p.add_run("Signature: ___________________________\n")
        r_sig.font.name = "Calibri"
        r_sig.font.size = Pt(8.5)
        r_sig.font.color.rgb = COLOR_DARK
        
        r_dt = p.add_run(f"Date: {date_val}")
        r_dt.font.name = "Calibri"
        r_dt.font.size = Pt(8.5)
        r_dt.font.color.rgb = COLOR_DARK

    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Successfully generated: {path}")

if __name__ == "__main__":
    create_ai_role_document()
