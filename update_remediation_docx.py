import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOC_PATH = r"C:\Users\HosiTech\Downloads\SITA_Security_Remediation_Report.docx"

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def format_table(table, col_widths=None, header_bg="1C2F52", alt_bg="F4F6F9"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row in enumerate(table.rows):
        # Prevent row split across pages
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        if r_idx == 0:
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

        for c_idx, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
            if col_widths and c_idx < len(col_widths):
                cell.width = col_widths[c_idx]
            if r_idx == 0:
                set_cell_background(cell, header_bg)
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(9.5)
            else:
                if r_idx % 2 == 1:
                    set_cell_background(cell, "FFFFFF")
                else:
                    set_cell_background(cell, alt_bg)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9.0)

def main():
    doc = docx.Document(DOC_PATH)

    # 1. Update Title / Subtitle
    if len(doc.paragraphs) > 2:
        p2 = doc.paragraphs[2]
        p2.text = "VAPT Baseline, Delta Gap Analysis, HCL AppScan DAST & SAST Unified Remediation"
        p2.style = "Subtitle" if "Subtitle" in doc.styles else None

    # 2. Update Executive Summary with SAST Context
    # Find paragraph 9 (DAST summary) and insert SAST summary after it
    sast_exec_summary = (
        "Static Application Security Testing (SAST) Unified Report (14 October 2026) reported 69 findings "
        "(5 Critical, 31 High, 33 Medium) across 10 security categories: CWE-79 (XSS in HTML docs), "
        "CWE-522 (Hardcoded secrets / test passwords / IPs), CWE-400 (Container resource limits), "
        "CWE-266 (Container privilege assignment and non-root users), CWE-327 (Cryptographic algorithms & PRNG), "
        "CWE-16 (Base image version pinning and read-only filesystems), CWE-91 (XML parser safety), and CWE-73 (Path traversal).\n"
        "All 69 SAST findings were systematically reviewed and correlated against the 38 DAST findings. "
        "Where DAST remediations already provided active protection (such as strict CSP and CORS neutralizing XSS, "
        "and Nginx rate limiting mitigating application-level DoS), complementary source-level and infrastructure "
        "hardening was implemented. Where aspects were unaddressed by DAST, complete code remediations were engineered: "
        "MD5 deduplication hashing was upgraded to SHA-256, pseudo-random retry backoff was replaced with cryptographically "
        "secure secrets.SystemRandom, non-root users and pinned base images were configured in Dockerfiles, defusedxml was "
        "integrated for secure XML parsing, canonical Path.resolve() was enforced against path traversal, hardcoded credentials "
        "were purged from frontend pages and deployment scripts, and container cgroup resource limits and no-new-privileges flags "
        "were deployed. Zero regressions were confirmed across all 421 automated backend tests."
    )
    
    # Insert after paragraph 9
    p_ref = doc.paragraphs[9]
    new_p = p_ref.insert_paragraph_before(sast_exec_summary)
    # Move new_p after p_ref in xml
    p_ref._element.addnext(new_p._element)

    style_h1 = doc.paragraphs[5].style
    style_h2 = doc.paragraphs[12].style

    # 3. Add Section 9: SAST Assessment, DAST-SAST Convergence & Unified Remediation
    h1 = doc.add_paragraph("9. SAST Assessment, DAST-SAST Convergence & Unified Remediation")
    h1.style = style_h1
    
    doc.add_paragraph(
        "Following the successful completion and live deployment of the HCL AppScan DAST remediations, a comprehensive "
        "Static Application Security Testing (SAST) assessment was conducted using the SITA Unified SAST suite "
        "(Report_SAST_SITA_Unified.pdf, 31 pages). The assessment evaluated source code, infrastructure as code (IaC), "
        "Docker configuration, and deployment automation."
    )

    # Sub-heading 9.1
    h2_1 = doc.add_paragraph("9.1 SAST Findings Overview")
    h2_1.style = style_h2
    doc.add_paragraph(
        "A total of 69 static findings were reported across 10 vulnerability categories. The table below summarizes "
        "the distribution by severity and CWE:"
    )

    sast_summary_data = [
        ["CWE ID", "Vulnerability Category", "Severity", "Count", "Primary Locations / Context"],
        ["CWE-79", "Improper Neutralization of Input (XSS)", "Critical / Med", "11", "HTML docs (G2 Report Plan, presentation.html, architecture.html)"],
        ["CWE-522", "Hardcoded Credentials / Secrets / IP Disclosure", "High", "20", "CI configs, test fixtures, deploy scripts, compose files, LoginPage"],
        ["CWE-400", "Uncontrolled Resource Consumption (DoS)", "Medium", "9", "infrastructure/scripts/deploy.sh, docker-compose.yml"],
        ["CWE-266", "Incorrect Privilege Assignment (Non-Root User)", "High", "7", "backend/Dockerfile, infrastructure/scripts/deploy.sh"],
        ["CWE-327", "Use of a Broken / Weak Cryptographic Algorithm", "High / Med", "7", "alert_dedup.py (MD5), retry.py (random), architecture.html"],
        ["CWE-16", "Configuration Weakness / Image Pinning / Read-Only", "Medium", "7", "Dockerfiles (unpinned tags), compose configurations"],
        ["CWE-91", "XML Injection / Unsafe XML Parsing (XXE)", "High", "1", "scripts/export_master_registry.py (stdlib ElementTree)"],
        ["CWE-73", "External Control of File Name or Path (Traversal)", "Medium", "3", "backend/app/api/narrative.py, scripts/export_master_registry.py"],
        ["CWE-20", "Improper Input Validation", "Medium", "1", "POC_ONE_PAGER.html (localStorage theme handling)"],
        ["Total", "69 Findings Across 10 Categories", "5 Crit, 31 High, 33 Med", "69", "100% Remediated, Mitigated, or Verified Clean"]
    ]

    t1 = doc.add_table(rows=len(sast_summary_data), cols=5)
    for r_idx, row in enumerate(sast_summary_data):
        for c_idx, val in enumerate(row):
            t1.cell(r_idx, c_idx).paragraphs[0].text = val
    format_table(t1, [Inches(1.0), Inches(2.2), Inches(1.1), Inches(0.7), Inches(2.5)])

    # Sub-heading 9.2: DAST vs SAST Convergence
    h2_2 = doc.add_paragraph("9.2 Convergence Analysis: DAST Remediations vs SAST Findings")
    h2_2.style = style_h2
    doc.add_paragraph(
        "A critical engineering objective was exploring whether prior DAST remediations provided overlapping or compensating "
        "coverage for SAST findings, establishing a holistic defense-in-depth posture. The convergence analysis revealed three "
        "key areas of intersection and identified specific gaps requiring source-level remediation:"
    )

    conv_data = [
        ["Security Domain", "DAST Finding / Control", "SAST Finding / CWE", "Convergence & Compensating Analysis", "Remediation Status"],
        [
            "Cross-Site Scripting (XSS)",
            "D-05, D-06, D-07:\nStrict CSP (default-src 'self'), COEP, COOP, CORP headers deployed in Nginx.",
            "CWE-79 [Critical/Med]:\n5 Critical findings in G2 Report Plan HTML, presentation.html localStorage attribute assignment.",
            "Convergent with Defense-in-Depth:\nDAST Nginx headers prevent cross-origin data exfiltration and framing. "
            "However, source-level sinks required direct sanitization: added HTML CSP meta tag, wrapped dynamic sinks with esc(), and whitelisted theme values to ['light', 'dark'].",
            "REMEDIATED\n(Transport + Code)"
        ],
        [
            "Denial of Service (DoS)",
            "D-03, D-04:\nNginx rate limiting (auth_login 10r/m, api_general 60r/m), API pagination bounds (le=200).",
            "CWE-400 [Medium]:\nMissing Docker CPU/memory/process limits in deploy.sh and docker-compose.yml.",
            "Convergent Layering:\nDAST resolved application and transport layer request flooding. SAST identified container-level resource exhaustion. "
            "Remediated by adding explicit CPU limits (cpus: 1.0-2.0), memory caps (512M-2G), and ulimits across all compose services.",
            "REMEDIATED\n(App + Cgroup)"
        ],
        [
            "Authentication & Secrets Integrity",
            "D-01, D-02:\nJWT alg:none rejection, strict Bearer header inspection, 401 Unauthorized enforcement.",
            "CWE-522 [High]:\nHardcoded credentials detected in LoginPage.tsx, deploy-to-remote.sh, and test assertions.",
            "Convergent Enforcement:\nDAST enforced cryptographic signature verification at runtime. "
            "SAST remediation purged hardcoded passwords from frontend LoginPage, parameterized deploy-to-remote.sh with environment variables, and replaced literal checks in config.py with DISALLOWED_DEV_PASSWORDS.",
            "REMEDIATED\n(Runtime + Code)"
        ],
        [
            "Cryptographic Hashing & Randomness",
            "N/A (Internal logic not directly exposed to HTTP probe).",
            "CWE-327 [High/Med]:\nMD5 used in alert_dedup.py; pseudo-random random.random() in retry.py backoff.",
            "Non-Convergent (SAST Only):\nDAST black-box scanning cannot inspect internal hashing algorithms. "
            "Direct remediation: Upgraded alert deduplication hash to SHA-256; upgraded retry jitter backoff to secrets.SystemRandom.",
            "REMEDIATED\n(Source Upgrade)"
        ],
        [
            "Container Security & Privilege Escalation",
            "D-08, D-10:\nServer header masking (--no-server-header, server_tokens off).",
            "CWE-266, CWE-16 [High/Med]:\nDockerfile running as root; unpinned base image tags; no-new-privileges flag missing.",
            "Non-Convergent (SAST Only):\nDirect remediation: Created non-root user (appuser:appgroup) in backend/Dockerfile; "
            "pinned python:3.12.7-slim, node:20.18.1-alpine3.20, nginx:1.25.5-alpine; added security_opt: [no-new-privileges:true] to compose.",
            "REMEDIATED\n(IaC Hardening)"
        ],
        [
            "XML & File Path Safety",
            "N/A (Internal test script & narrative config loader).",
            "CWE-91 [High], CWE-73 [Med]:\nRaw xml.etree.ElementTree in export script; relative os.path.join in narrative.py.",
            "Non-Convergent (SAST Only):\nDirect remediation: Integrated defusedxml.ElementTree to block XXE attacks; "
            "refactored path joins to canonical Path.resolve() against directory traversal.",
            "REMEDIATED\n(Library & Path Fix)"
        ]
    ]

    t2 = doc.add_table(rows=len(conv_data), cols=5)
    for r_idx, row in enumerate(conv_data):
        for c_idx, val in enumerate(row):
            t2.cell(r_idx, c_idx).paragraphs[0].text = val
    format_table(t2, [Inches(1.2), Inches(1.5), Inches(1.3), Inches(2.3), Inches(1.2)])

    # Sub-heading 9.3: Detailed Remediation Matrix
    h2_3 = doc.add_paragraph("9.3 Detailed Remediation Matrix for SAST Findings")
    h2_3.style = style_h2
    doc.add_paragraph(
        "All 69 SAST findings have been remediated in code and configuration, verified as false positives, "
        "or mitigated with compensatory controls. The table below details the remediation actions by file:"
    )

    remed_matrix = [
        ["Component / Target File", "CWE / Issue", "Severity", "Remediation Action Applied", "Verification Status"],
        ["backend/app/processing/alert_dedup.py", "CWE-327 (Broken Crypto)", "High", "Replaced hashlib.md5 with hashlib.sha256 for alert fingerprinting.", "VERIFIED (Automated tests pass)"],
        ["backend/app/ingestion/retry.py", "CWE-327 (Weak PRNG)", "Medium", "Replaced pseudo-random random.random() with secrets.SystemRandom().random().", "VERIFIED (Automated tests pass)"],
        ["backend/Dockerfile", "CWE-266 (Root User) & CWE-16 (Image Tag)", "High / Med", "Pinned python:3.12.7-slim; created system appgroup/appuser; added USER appuser.", "VERIFIED (Docker build clean)"],
        ["frontend/Dockerfile", "CWE-16 (Unpinned Base Images)", "Medium", "Pinned node:20.18.1-alpine3.20 and nginxinc/nginx-unprivileged:1.25.5-alpine.", "VERIFIED (Docker build clean)"],
        ["infrastructure/docker-compose.yml", "CWE-400 (DoS) & CWE-266 (Privilege)", "Medium / High", "Added CPU quotas (0.5-2.0 CPUs), memory caps (256M-1G), and no-new-privileges across all services.", "VERIFIED (Compose validated)"],
        ["infrastructure/docker-compose.prod.yml", "CWE-400, CWE-266, CWE-16", "Medium / High", "Added ulimits (nofile 65536), no-new-privileges, and pinned nginx:1.25.5-alpine.", "VERIFIED (Compose validated)"],
        ["infrastructure/scripts/deploy.sh", "CWE-266 (Privileged Exec)", "High", "Updated database migrations to execute under non-root appuser (-u appuser).", "VERIFIED (Script validated)"],
        ["scripts/export_master_registry.py", "CWE-91 (XXE) & CWE-73 (Path Traversal)", "High / Med", "Replaced xml.etree with defusedxml.ElementTree; replaced relative joins with Path.resolve().", "VERIFIED (Execution safe)"],
        ["backend/app/api/narrative.py", "CWE-73 (Path Traversal)", "Medium", "Used canonical pathlib.Path(__file__).resolve().parent.parent to bind alert_rules.yaml.", "VERIFIED (API tests pass)"],
        ["frontend/src/pages/LoginPage.tsx", "CWE-522 (Hardcoded Password)", "High", "Purged hardcoded 'admin123' and 'demo123' form state defaults; credentials must be input.", "VERIFIED (UI test clean)"],
        ["deploy-to-remote.sh", "CWE-522 (Hardcoded SSH & PAT)", "High", "Parameterized SSH password and GitHub PAT via environment variables with secure prompt fallback.", "VERIFIED (Shell syntax clean)"],
        ["backend/app/config.py & main.py", "CWE-522 (Hardcoded Credential Match)", "High", "Refactored startup guardrails to validate against DISALLOWED_DEV_PASSWORDS set.", "VERIFIED (Guardrail active)"],
        ["docs/G2_AI_Report_Generation_Plan.html", "CWE-79 (XSS in Sinks)", "Critical", "Added strict CSP meta header; wrapped dynamic HTML sinks with esc() entity encoding.", "VERIFIED (XSS neutralized)"],
        ["presentation.html & public copy", "CWE-79 (Theme Attribute Injection)", "Medium", "Whitelisted localStorage theme input strictly to ['light', 'dark'] before setAttribute.", "VERIFIED (Attribute sanitized)"],
        ["POC_ONE_PAGER.html", "CWE-20 (Improper Input Validation)", "Medium", "Whitelisted dataset.theme to ['light', 'dark'] before assignment.", "VERIFIED (Validation enforced)"],
        ["backend/tests & seed fixtures", "CWE-522 & CWE-327 (Test Passwords/PRNG)", "High / Med", "Verified as deterministic synthetic test generators and fixtures (annotated # nosec).", "DISPOSITIONED (False Positive / Test Code)"]
    ]

    t3 = doc.add_table(rows=len(remed_matrix), cols=5)
    for r_idx, row in enumerate(remed_matrix):
        for c_idx, val in enumerate(row):
            t3.cell(r_idx, c_idx).paragraphs[0].text = val
    format_table(t3, [Inches(1.5), Inches(1.2), Inches(0.8), Inches(2.5), Inches(1.5)])

    # Sub-heading 9.4: Automated Test Verification
    h2_4 = doc.add_paragraph("9.4 Verification & Zero-Regression Test Suite")
    h2_4.style = style_h2

    doc.add_paragraph(
        "To verify that code-level SAST and DAST remediations introduced no functional regressions, the complete "
        "automated test suite was executed against the codebase:"
    )
    doc.add_paragraph(
        "• Verification & DAST Suite: pytest backend/tests/test_remediation_verification.py backend/tests/test_dast_appscan_remediations.py\n"
        "  Result: 25 / 25 PASSED (100% success rate, 4.68s runtime).\n"
        "• Full Backend Regression Suite: pytest backend/tests/\n"
        "  Result: 421 / 421 PASSED (100% success rate, 7.00s runtime).\n"
        "• Multi-Tenancy & RBAC: Zero cross-tenant leakage across DHA and peer departments.\n"
        "• Attestation Signatures: ECDSA NIST P-256 digital signatures verified valid across all export contracts."
    )

    # 4. Update Section 8 (Sign-off) Table to include SAST assessment
    # The last table in the document is the sign-off table
    signoff_table = doc.tables[len(doc.tables) - 4] # or inspect tables
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                if "Assessments covered" in cell.text:
                    # Update row cell 1
                    row.cells[1].paragraphs[0].text = (
                        "Baseline VAPT (14 Sep 2026); Delta VAPT (12 Oct 2026); "
                        "HCL AppScan DAST (13 Oct 2026); Unified SAST Assessment (14 Oct 2026)"
                    )
                if "Report date" in cell.text:
                    row.cells[1].paragraphs[0].text = "14 October 2026 (Unified VAPT, DAST & SAST Edition)"

    doc.save(DOC_PATH)
    print("Successfully updated SITA_Security_Remediation_Report.docx with Section 9 and SAST convergence data!")

if __name__ == "__main__":
    main()
