"""Generate the AVP requirements Word document.

A single executive-facing artefact that covers all twelve value propositions and
isolates the five that cannot be produced by engineering.

Follows the conventions in ``generate_system_doc.py`` — Calibri, the same accent
colour, the same heading scale and the same ``Light Grid Accent 1`` table style —
so the document set renders as one set.

Source of truth for the classification is
``app.processing.intel.capability``: the residue of each proposition is read from
the registry rather than retyped here, so the Word document cannot drift from
the code that enforces the boundary. If a proposition gains or loses its
residue, the next run reflects it.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x59, 0x59, 0x59)
RED = RGBColor(0xB3, 0x26, 0x1E)
GREEN = RGBColor(0x1E, 0x6B, 0x3A)

OUT = Path(__file__).resolve().parent.parent / "markdown_docs" / "AVP_REQUIREMENTS.docx"

#: Requirement text for the five that carry a residue. Kept short: the full case
#: for and against each is in docs/AI_INTEGRATION_REQUIREMENTS.md.
REQS = {
    "AVP-2": {
        "name": "Authoring alerting rules for received telemetry",
        "req": "For an attacker technique present in received telemetry and lacking alerting, produce a "
               "rule that alerts on it, in the platform's own alert_rules.yaml vocabulary, "
               "with severity, throttle and dispatch channel, delivered as a reviewable change "
               "to the existing rule file.",
        "scope": "The platform does not scan, does not host sensors and does not perform "
                 "vulnerability testing. It receives findings from four OEM sources and alerts "
                 "on them. Sigma, Suricata, Wazuh and YARA rules are NOT requested: they run "
                 "against telemetry this platform never receives and belong to the client's "
                 "own SIEM or IDS estate.",
        "why": [
            "Rules generated for a technique select on fields this platform does not have. "
            "Verified: a live technique probe returned predicates on three fields, and none "
            "of them exist in the block table. The gap is larger than a rename - a rule for "
            "this platform targets a normalised, tenant-scoped finding record, not log fields.",
            "The hard problem is deciding which received signal evidences a technique - which "
            "OEM source, which normalised field, at what threshold - and expressing it in the "
            "shape the rule engine actually evaluates.",
            "Coverage is fixed at nine hand-written rules covering eleven techniques. Every "
            "new weakness class arriving through a new CWE is a rule nobody has written.",
            "The obligation scales with techniques and with new weakness classes, for as "
            "long as the platform runs.",
        ],
    },
    "AVP-3": {
        "name": "Attributing threat campaigns to this estate",
        "req": "For a vulnerability present in the estate, determine whether a named, currently "
               "active campaign targets this sector and whether its technique set matches this "
               "estate's exposure.",
        "why": [
            "A threat-feed count measures global popularity, not relevance here. A count that "
            "is high may be entirely unrelated to government targets; a low count may be an "
            "active campaign aimed squarely at this sector.",
            "The deliverable is extraction from unstructured threat reporting into a technique "
            "set that is not published in queryable form. That is interpretation, not lookup.",
            "The platform holds no external threat intelligence at all. This is an absence, not "
            "a weak capability.",
            "Campaign intelligence changes weekly. Re-reading current reporting is a recurring "
            "cost; re-writing rules against stale reporting is a treadmill with no end date.",
        ],
    },
    "AVP-5": {
        "name": "Judging whether a breach is notifiable under POPIA s.22",
        "req": "Given a detected compromise, assess whether the notification duty is triggered; "
               "if so, assemble a complete, evidenced, signed notification packet for a named "
               "human to review.",
        "why": [
            "Both errors are expensive. Missing a reportable breach is a regulatory finding; "
            "notifying the Regulator unnecessarily is itself a compliance event. No threshold "
            "is correct in both directions.",
            "Severity is the wrong axis. The archetypal breach for an identity platform is bulk "
            "unauthorised read access through legitimate credentials, which produces no "
            "critical event at all.",
            "What constitutes adequate notification is defined by case law, not by "
            "configuration.",
            "Blast radius is zero by design. The platform assembles and signs; a named human "
            "decides whether to send. The capability has no transmit function.",
        ],
    },
    "AVP-8": {
        "name": "Explaining what caused a risk-score movement",
        "req": "When the fused risk score moves, attribute the movement to named external threat "
               "activity, alongside the signal decomposition already computed.",
        "why": [
            "A decomposition is not an explanation. The deterministic layer reports that a "
            "signal moved by a number; it cannot say which vulnerability, how recently it "
            "arrived, or whether anyone is exploiting it.",
            "The causal evidence sits outside the platform: publication date, known-exploited "
            "status, campaign membership.",
            "When two signals move together, separating the driver from its downstream effect "
            "requires reasoning across both signals and external corroboration.",
        ],
        "note": "The signal decomposition is already built and live. Only the causal attribution "
                "needs this requirement. If the narrative is not wanted, withdraw this "
                "requirement and no AI is required for the decomposition.",
    },
    "AVP-11": {
        "name": "Reading privileged-action sequences",
        "req": "Read the signed privileged-action trail and identify behavioural patterns that "
               "individually authorised actions only reveal in combination.",
        "why": [
            "Thresholds are defeated by adaptation. An actor who learns a volume rule operates "
            "just below it. Every volume-only detection has this property.",
            "The signal is in the order, not the events. A sequence of individually defensible "
            "actions can be damning in combination, and no per-action rule can represent that.",
            "The substrate is already excellent and entirely unused: append-only, signed, "
            "recording actor, role and scope for every privileged action. Verified: nothing "
            "outside the export path reads it.",
            "The output must be an explanation an auditor can rely on, not a score.",
        ],
        "note": "No administrator at any tier may hold this capability. Review requires a second "
                "named person.",
    },
}

#: One-line purpose for the at-a-glance table. The registry residue is the
#: authoritative field but runs to several sentences, and truncating it mid-word
#: in a four-column table reads as sloppiness. These are written to fit.
AIM = {
    "AVP-2": "Alert on an attacker technique the vendor data shows but the platform is silent on",
    "AVP-3": "Decide whether an active campaign actually targets this sector and this estate",
    "AVP-5": "Decide whether a detected compromise meets the statutory duty to notify",
    "AVP-8": "Say what moved the risk score, and which external activity caused it",
    "AVP-11": "Spot behavioural patterns across privileged actions that no single rule catches",
}

#: The seven that need no model. Short by design.
ENG = {
    "AVP-1": ("Compliance scoring from telemetry", "Built",
              "The scoring engine already existed with zero callers. Binding a control to "
              "evidence is a join; summing weighted percentages is arithmetic."),
    "AVP-4": ("Cross-vendor contradiction detection", "5 of 6 built",
              "Every check is a group-by or set difference over columns already held."),
    "AVP-6": ("Estate ownership and concentration graph", "Built",
              "Counting distinct owners over six columns already denormalised onto every row."),
    "AVP-7": ("Prescriptive peer contrast", "Built",
              "A set difference between the caller's estate and the existing blinded peer "
              "aggregate. No peer findings are read."),
    "AVP-9": ("Coverage-driven hunts", "Built",
              "A query from curated column bindings plus an expected-result count the platform "
              "already computes."),
    "AVP-10": ("Vendor coverage and agreement attestation", "3 of 4 built",
              "Counts and ratios over findings and alerts. The fourth needs an asset inventory, "
              "which is an engineering gap, not an AI gap."),
    "AVP-12": ("Dispute-ready evidence packets", "Built",
              "The platform already signs, hashes and verifies offline for the Auditor-General "
              "attestation. A packet is those primitives applied to different rows."),
}


def set_base_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12
    for name, size, color in (
        ("Heading 1", 16, ACCENT),
        ("Heading 2", 12.5, ACCENT),
        ("Heading 3", 11, ACCENT),
    ):
        st = doc.styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = color


def cover(doc, ai_count, demoted_count):
    for _ in range(4):
        doc.add_paragraph()
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Value Proposition Requirements")
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = ACCENT
    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run("SITA Consolidated Security Reporting")
    r.font.size = Pt(14)
    r.font.color.rgb = GREY
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run(
        f"{ai_count} require AI  ·  {demoted_count} are engineering"
    )
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = RED if ai_count else GREY
    m = doc.add_paragraph()
    m.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = m.add_run(
        f"{date.today().strftime('%d %B %Y')} · For executive approval · "
        "Internal — Commercial in Confidence"
    )
    r.font.size = Pt(9)
    r.font.color.rgb = GREY
    doc.add_page_break()


def table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, hh in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.paragraphs[0].add_run(hh).bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    if widths:
        for r in t.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Inches(w)
    return t


def main() -> None:
    from app.processing.intel import capability

    reg = capability.REGISTRY
    ai = sorted((a for a, p in reg.items() if p.residue), key=lambda s: int(s.split("-")[1]))
    eng = sorted((a for a, p in reg.items() if not p.residue), key=lambda s: int(s.split("-")[1]))

    doc = Document()
    set_base_styles(doc)
    cover(doc, len(ai), len(eng))

    # -- 1. purpose ------------------------------------------------------
    doc.add_heading("1. Purpose", level=1)
    doc.add_paragraph(
        "This document sets out twelve value propositions for the platform and identifies which "
        "of them cannot be delivered by engineering."
    )
    doc.add_paragraph(
        "What the platform is: a consuming platform. It receives findings from four OEM sources, "
        "reconciles their vocabularies, scores the estate, alerts on received data and reports. "
        "It does not scan, does not host sensors and does not perform vulnerability testing."
    )
    doc.add_paragraph(
        "Twelve were written. Each was then reduced to the single deliverable that cannot be "
        f"produced by code the platform already owns, applying a strict test: {chr(8212)} a "
        "deliverable a template can emit is not AI, however much prose it contains."
    )
    doc.add_paragraph(
        f"Five propositions carry such a deliverable. Seven do not, and are ordinary "
        "engineering. Five of those seven are already built and in production. This document "
        f"requests approval for the {len(ai)} requirements in section 3 only."
    )
    pos = doc.add_paragraph()
    pr = pos.add_run(
        "Supporting position: 33 of 43 deterministic components are shipped and live, which is "
        "what makes adding AI an additive change rather than a rewrite."
    )
    pr.font.italic = True
    pr.font.color.rgb = GREY

    # -- 2. the split ----------------------------------------------------
    doc.add_heading("2. The split at a glance", level=1)
    rows = []
    for a in ai:
        rows.append([a, REQS[a]["name"], "AI required", AIM[a]])
    for a in eng:
        rows.append([a, ENG[a][0], "Engineering", ENG[a][2]])
    table(doc, ["Ref", "Proposition", "Route", "Basis"], rows, [0.6, 2.0, 0.9, 3.6])
    doc.add_paragraph()

    # -- 3. the five ------------------------------------------------------
    doc.add_heading("3. Requirements that cannot be engineered or built", level=1)
    doc.add_paragraph(
        f"These {len(ai)} carry a deliverable with no deterministic route to it. For each: the "
        "requirement, and why an engineering build does not reach it."
    )
    for i, a in enumerate(ai, 1):
        spec = REQS[a]
        doc.add_heading(f"R{i} · {a} — {spec['name']}", level=2)
        if spec.get("scope"):
            sc = doc.add_paragraph()
            sc.add_run("Scope. ").bold = True
            sc.add_run(spec["scope"])
        q = doc.add_paragraph()
        q.add_run("Requirement. ").bold = True
        q.add_run(spec["req"])
        w = doc.add_paragraph()
        w.add_run("Why not the engineering route.").bold = True
        for item in spec["why"]:
            para = doc.add_paragraph(style="List Bullet")
            para.paragraph_format.space_after = Pt(3)
            para.add_run(item)
        if spec.get("note"):
            n = doc.add_paragraph()
            n.add_run("Note. ").bold = True
            r = n.add_run(spec["note"])
            r.font.color.rgb = GREY
            r.font.italic = True

    # -- 4. the seven -----------------------------------------------------
    doc.add_heading("4. Propositions that need no AI", level=1)
    built = sum(1 for a in eng if ENG[a][1] == "Built")
    doc.add_paragraph(
        f"Listed so the boundary is visible. None of these is funded as AI. {built} of the "
        f"{len(eng)} are complete and in production."
    )
    table(
        doc,
        ["Ref", "Proposition", "State", "Why no model is required"],
        [[a, ENG[a][0], ENG[a][1], ENG[a][2]] for a in eng],
        [0.6, 2.2, 0.9, 3.4],
    )
    doc.add_paragraph()

    # -- 5. governance ----------------------------------------------------
    doc.add_heading("5. Conditions on all five", level=1)
    for c in [
        "Advisory only. None may alter a severity, a risk score, a bucket, an alert status or a "
        "block. Every output is a recommendation for a named human to accept or reject.",
        "The deterministic pipeline is unchanged and remains provable with every model "
        "disconnected. A model failure degrades one capability, not the platform.",
        "The existing role and permission structure is not modified. Capabilities are additive.",
        "No component sits in the ingestion or dispatch path.",
        "No model text enters the signed attestation body.",
        "Outbound data is limited to public identifiers — vulnerability identifiers, technique "
        "identifiers, regulatory queries. No warehouse row and no personal information.",
        "Each capability can be disabled without a release.",
        "Every model call is recorded with its confidence, version and prompt identifier.",
    ]:
        para = doc.add_paragraph(style="List Bullet")
        para.paragraph_format.space_after = Pt(3)
        para.add_run(c)

    # -- 6. approval ------------------------------------------------------
    doc.add_heading("6. Approval", level=1)
    doc.add_paragraph(
        f"Approval is sought for the {len(ai)} requirements in section 3. The {len(eng)} "
        "propositions in section 4 are not funded as AI."
    )
    table(
        doc,
        ["Role", "Name", "Decision", "Date"],
        [
            ["Executive sponsor", "", "Approve / Decline / Defer", ""],
            ["Compliance", "", "Approve / Decline", ""],
            ["Technology", "", "Approve / Decline", ""],
            ["Finance", "", "Approve / Decline", ""],
        ],
        [1.5, 1.5, 2.0, 1.1],
    )
    doc.add_paragraph()
    r = doc.add_paragraph()
    r.add_run(
        "Recommendation: approve "
        + ", ".join(a for a in ai if a != "AVP-8")
        + ". AVP-8 is optional — its deterministic half is already in production."
    ).bold = True

    doc.add_paragraph()
    f = doc.add_paragraph()
    fr = f.add_run(
        "Basis: verified against the platform codebase and database schema at commit eca4852. "
        "Supporting detail in docs/AI_INTEGRATION_REQUIREMENTS.md; full proposition record in "
        "docs/AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md."
    )
    fr.font.size = Pt(8.5)
    fr.font.color.rgb = GREY

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"saved: {OUT} ({OUT.stat().st_size:,} bytes) · {len(ai)} AI / {len(eng)} engineering")


if __name__ == "__main__":
    main()