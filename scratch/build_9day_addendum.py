"""Build ADDENDUM B to the HOSI-UNIFIED master flight plan.

WHAT THIS DOCUMENT IS
An addendum. It extends the master flight plan
  HOSI-UNIFIED_DATA_MANAGED_SERVICE_PROJECT_FLIGHT_PLAN_2026 (20 August 2026)
which covers Phases 1-12 and is 99 of 100 activities complete. Addendum B adds
Phase 13 - AI Report Generation - as an ADDITIVE stage. It does not amend,
replace or renumber any existing phase.

WHY THE WORK EXISTS (the integration this addendum delivers)
The master plan's backend pipeline ends at Stage 4 (FastAPI REST layer, Phase 9).
Everything a stakeholder reads today is fixed arithmetic - a weighted sum in
risk_engine.py:14, a YAML rule, or hand-authored prose in
frontend/src/data/explanations.ts. This addendum inserts an AI report-generation
stage into the backend, reading FROM the data warehouse the master plan already
built (Phase 7), and returning JSON to the existing dashboards. It is the
continuation of the pipeline, not a separate product.

INTEGRATION POINTS INTO THE EXISTING PIPELINE (all pre-existing, all read-only)
  warehouse.*          Phase 7  - the tables this addendum reads
  tenant_filter()      Phase 9  - the scoping primitive it delegates to, never reimplements
  canonical_json()     Phase 9  - reused for scope_hash and fact_pack_hash
  CircuitBreaker       Phase 3  - reused for model-gateway failure handling
  audit.action_audit   Phase 7  - the audit sink it writes to
Addendum B creates: backend/app/ai/, one router, the ai schema, tests. Plus ONE
added line in app/main.py, the sole router registration point in the codebase.

ADDENDUM A is read only for the original activity wording and deliverable
statements, so each of the 55 refs keeps its identity and its disposition is
traceable. Nothing from Addendum A is inherited implicitly: every sheet carries
its own context, totals and decision defaults.
"""
import datetime as dt
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

SRC = Path(r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED_FLIGHT_PLAN_ADDENDUM_A_G2_AI_REPORT_GENERATION.xlsx")
OUT = Path(r"C:\sita-platform\scratch\HOSI-UNIFIED_FLIGHT_PLAN_ADDENDUM_B_G2_9DAY_COMPRESSION_STAGED.xlsx")

D = lambda n: dt.datetime(2026, 10, n)
# Delivery window: 7 build days (7, 8, 9, 10, 12, 13, 14 Oct - Saturday 10 Oct
# is a working day, worked by Takawira alone) + 15 Oct demonstration + 16 Oct
# close-out. Design days 2, 5 and 6 October are complete and are not in scope.
D1, D2, D3, D4 = D(7), D(8), D(9), D(10)
D5, D6, D7 = D(12), D(13), D(14)
D8, D9 = D(15), D(16)

# 1 person-day = 8.0 hours. Every effort figure in this workbook is also carried
# in hours, because the binding constraint on this plan is an individual's
# calendar, not an abstract capacity pool.
PD_HOURS = 8.0

src = openpyxl.load_workbook(SRC, data_only=True)
src_plan = src["G2 Flight Plan"]

# Role definitions for this addendum.
# Delivery team is 100% vendor personnel. ZERO SITA employees are on this team.
# SITA is the client/customer. Solution packages will be shipped to SITA environment
# post-PoC acceptance (Phase 2).
LEAD = "Takawira Mazando"
LEAD_T = "Lead Developer, G2"
AI = "Richard Masukume"
AI_T = "Head of AI Research Department"
PDEV = "Peter Rashaya"
PDEV_T = "Second Developer, G2"
J = "Jerry Mokone"
J_T = "Project Manager"
VIC = "Victoria Nedombeloni"
VIC_T = "Business Analyst / Compliance Lead"
KAG = "Kagiso Mokgofa"
KAG_T = "Project Sponsor"
orig = {}
for r in src_plan.iter_rows(min_row=13, max_row=77):
    ref = r[12].value
    if ref:
        orig[str(ref).strip()] = {
            "activity": r[1].value, "deliverable": r[7].value,
            "risks": r[8].value, "deps": r[9].value, "notes": r[11].value,
            "owner": r[6].value, "phase": r[15].value,
        }

# ref: (phase_block, phase_name, activity_override, start, end, pd, owner, primary,
#       deliverable_override, status, risks, deps, notes)
A = []


def add(ref, block, phase, start, end, pd, owner, primary, status="Not Started",
        act=None, deliv=None, risks=None, deps=None, notes=None, pct=0):
    o = orig.get(ref, {})
    A.append({
        "ref": ref, "block": block, "phase": phase,
        "activity": act or o.get("activity", ""),
        "start": start, "end": end, "pd": pd,
        "owner": owner, "primary": primary, "status": status, "pct": pct,
        "deliverable": deliv or o.get("deliverable", ""),
        "risks": risks if risks is not None else o.get("risks", ""),
        "deps": deps or o.get("deps", ""),
        "notes": notes or o.get("notes", ""),
    })


DAYS9 = [(1, "D1\nWed 7"), (2, "D2\nThu 8"), (3, "D3\nFri 9"), (4, "D4\nSat 10"),
         (5, "D5\nMon 12"), (6, "D6\nTue 13"), (7, "D7\nWed 14"),
         (8, "D8\nThu 15\nDEMO"), (9, "D9\nFri 16")]
DATES = {1: D(7), 2: D(8), 3: D(9), 4: D(10), 5: D(12), 6: D(13), 7: D(14), 8: D(15), 9: D(16)}

B1 = "BLOCK 1 - Governance & Authorisation Foundation (compressed: 7-10 Oct)"
B2 = "BLOCK 2 - Scoped Data Layer & Generation Engine (compressed: 7-12 Oct)"
B3 = "BLOCK 3 - Verification, Fallback, API & Audit (compressed: 9-14 Oct)"
B4 = "BLOCK 4 - Demo, Evidence & Sign-Off (compressed: 14-16 Oct)"

# Daily hours by resource across the whole window. Richard's in-register 0.50 PD
# (T01, model pull + latency measurement) is charged at 0.5 h on every
# non-Saturday day rather than as a 4.0 h block on day 1, so no single day
# carries an artificial spike. His advisory time is separate and also avoids
# Saturday. Peter works Fri 9, Mon 12 and Tue 13 only - never the weekend.
DAILY_HOURS = {
    1: {LEAD: 12.0, AI: 0.5},
    2: {LEAD: 16.0, AI: 1.0},
    3: {LEAD: 14.0, PDEV: 2.0, AI: 1.0, VIC: 6.0},
    4: {LEAD: 16.0},
    5: {LEAD: 8.0, PDEV: 8.0, AI: 1.5},
    6: {LEAD: 14.0, PDEV: 2.0, AI: 1.0},
    7: {LEAD: 14.0, J: 4.0, AI: 1.0},
    8: {AI: 1.5},
    9: {AI: 0.5},
}
GRAND_HOURS = round(sum(sum(v.values()) for v in DAILY_HOURS.values()), 2)

P12 = "Phase 12: Governance, Approval & Decisions (Days 1-4)"
P13 = "Phase 13: Authorisation Foundation - Gate 1 RBAC, Gate 2 ReportScope, ai schema (Days 1-3)"
P14 = "Phase 14: Scoped Data Layer - accessors, fact pack, disclosure, claims (Days 2-5)"
P15 = "Phase 15: Generation Engine - Ollama gateway, prompts, orchestration (Days 3-6)"
P16 = "Phase 16: Verification & Deterministic Fallback (Days 5-7)"
P17 = "Phase 17: REST Router, Envelope & Audit (Days 6-7)"
P18 = "Phase 18: Verification Suites & Diff Review (Days 6-8)"
P19 = "Phase 19: Demonstration, Evidence & Sign-Off (Days 8-9)"

J = "Jerry"

# ---------------- BLOCK 1: governance ----------------
add("12.1", B1, P12, D1, D1, 1.0, "Takawira", "Takawira", "Completed", pct=100,
    notes="Already delivered: G2 plan + master AI integration plan + architecture assessment + ADR + execution plan.")
add("12.2", B1, P12, D1, D4, 0.5, f"{J} ({J_T}) & {KAG} ({KAG_T})", J, pct=40,
    act="G2 plan review and approval - proceed on documented defaults",
    deliv="Plan pack issued; defaults tabled for adoption at the 15 Oct demonstration",
    notes="Cannot close before the demo. Standing rule: a decision not amended is adopted as documented.",
    deps="12.1")
add("12.3", B1, P12, D1, D2, 0.5, f"{LEAD} ({LEAD_T})", LEAD, pct=100,
    notes="ANSWERED BY DEFAULT: schema 'ai' in the main database. A separate DB costs 4-6 PD of provisioning, none of it in this window.")
add("12.4", B1, P12, D1, D4, 0.5, f"{VIC} ({VIC_T})", VIC,
    act="Decision 2 - estate-wide compliance disclosure: declare or block?",
    notes="DEFAULT ADOPTED: declare ESTATE_WIDE. Proven live: 456 + 228 = 684 rows unscopable. This is the strongest demo item.",
    deps="12.2")
add("12.5", B1, P12, D1, D4, 0.5, f"{VIC} ({VIC_T}) & {J} ({J_T})", VIC,
    notes="DEFAULTS ADOPTED: narrative stays separate from the attestation; ai.report retention matches audit.action_audit.")
add("12.6", B1, P12, D1, D4, 0.5, f"{VIC} ({VIC_T})", VIC,
    notes="DEFAULT ADOPTED: ROLE_CLAIMS signed exactly as drafted. Any widening needs fresh approval BEFORE implementation.")
add("12.7", B1, P12, D1, D1, 0.25, f"{KAG} ({KAG_T}) & {J} ({J_T})", KAG, pct=100,
    act="Decision 6 - model hosting: GPU CAPEX, sovereign cloud, or existing hardware",
    deliv="Hosting decision: self-hosted Ollama on existing hardware - zero CAPEX, zero procurement lead time",
    notes="RESOLVED BY EVIDENCE. Ollama 0.35.1 already running (PID 27452). Replaces a 6 PD GPU provisioning activity.",
    risks="Procurement eliminated")
add("12.8", B1, P12, D4, D4, 0.0, J, J,
    act="Risk: decisions 1-6 not closed by the demonstration",
    notes="Likelihood: Low. 6 of 7 are answered by evidence or default; all defaults are documented.")

# ---------------- BLOCK 2: authorisation + data layer ----------------
add("13.1", B2, P13, D1, D1, 0.5, "Takawira", "Takawira",
    act="init-ai-schema.sql - schema ai, ai.report table and 2 indexes",
    notes="Idempotent. Includes model_id, model_digest, prompt_version, latency_ms, fallback_used per D5.")
add("13.2", B2, P13, D1, D2, 1.0, "Takawira", "Takawira",
    notes="Additive namespace. 14 roles enumerated from ROLES_HIERARCHY, not the '11' in the original sheet.")
add("13.3", B2, P13, D2, D2, 1.5, "Takawira", "Takawira",
    notes="Delegates to tenant_filter(); never re-implements it. Unknown province slug must fail LOUDLY.")
add("13.4", B2, P13, D2, D3, 0.5, "Takawira", "Takawira",
    act="Gate 1 / Gate 2 tests - unknown role 403, empty scope false(), scope_hash determinism",
    notes="Proves GATE A.")
add("13.5", B2, P13, D1, D1, 0.25, "Takawira", "Takawira",
    act="Apply ai schema to the local sita instance",
    deliv="ai.report present in the local database; migration rehearsal log",
    notes="LOCAL ONLY. VPN access to 192.168.101.0/24 (R12) is not required for the 15 Oct demo.")
add("13.6", B2, P13, D3, D3, 0.0, "Takawira", "Takawira",
    act="Risk: ReportScope diverges from tenant_filter() behaviour",
    notes="Mitigation: delegate, never re-implement. Parity asserted by 13.4.")

add("14.1", B2, P14, D2, D3, 1.0, "Takawira", "Takawira",
    act="accessors.py - scope-first warehouse readers (2 readers, not 5)",
    notes="scope is FIRST POSITIONAL arg on every reader. Aggregates in SQL; mappers.ts is NOT ported.")
add("14.2", B2, P14, D3, D3, 0.25, "Takawira", "Takawira",
    notes="Signature-inspection test. Fails the build if a reader lacks scope.")
add("14.3", B2, P14, D3, D3, 0.75, LEAD, LEAD,
    act="disclosure.py - THREE disclosure classes + capability introspection gate",
    deliv="TENANT_SCOPED / ESTATE_WIDE / DERIVED_FROM_ESTATE_WIDE; SCOPABLE/REFERENCE/UNSCOPABLE/NEVER_READ table classification",
    notes="Adds ADR D-A3 (derived-estate-wide) and D-A5 (introspection + never-read denial) which the original 3.0 PD activity did not cover.")
add("14.4", B2, P14, D2, D3, 1.0, LEAD, LEAD,
    notes="9 claim classes. exec holds none of cve_ids/alert_ids/owner_names/rule_ids. Signed as drafted (D4).")
add("14.5", B2, P14, D4, D4, 1.0, "Takawira", "Takawira",
    act="context.py - pure fact-pack builders for 2 report types + fact_pack_hash",
    notes="2 of the original 7 report types. Pure builders, testable without a DB, reusing canonical_json/sha256_hex.")
add("14.6", B2, P14, D4, D4, 0.5, "Takawira", "Takawira",
    notes="Zero rows outside the province-expanded set; out-of-scope yields empty, never estate-wide.")
add("14.7", B2, P14, D4, D4, 0.0, f"{VIC} ({VIC_T})", VIC,
    act="Risk: compliance tables remain unscopable",
    notes="Likelihood: High (structural). 9 of 16 warehouse tables are unscopable, verified by introspection.")

add("15.1", B2, P15, D1, D1, 0.5, "Richard", "Richard",
    act="Model hosting - Ollama on existing hardware; pull qwen2.5:3b, benchmark CPU latency",
    deliv="Ollama serving qwen2.5:3b; latency table at 300/600/900 max_tokens",
    notes="REPLACES the 6 PD GPU activity (12.7). Token cap decided day 1 on measured latency, not on rehearsal day.")
add("15.2", B2, P15, D5, D5, 0.5, LEAD, LEAD,
    act="gateway.py - httpx to Ollama, CircuitBreaker reuse, token budget",
    notes="Reuses app/ingestion/circuit_breaker.py. AI settings in app/ai/settings.py to hold non-interference to one line.")
add("15.3", B2, P15, D4, D4, 0.0, "Takawira", "Takawira", status="Folded",
    act="redaction.py - mandatory pre-egress PII scrubber (local model architecture)",
    deliv="Scrubber plus tests; zero cloud egress with local Ollama; raw_data excluded at fact pack assembly",
    notes="FOLDED into 14.5 / 15.4. Reassigned from Peter to Takawira. Model is local-only (localhost:11434, zero network egress); raw_data OEM payload dropped before prompt.")
add("15.4", B2, P15, D3, D4, 1.5, LEAD, LEAD,
    act="Role-aware prompt templates (2) + role-injection harness",
    deliv="build_prompt(scope, report_type, pack); templates versioned and immutable; facts filtered to the claim set BEFORE the prompt",
    notes="2 of the original 7 templates. Assembled by code, not hand-edited YAML. Proves GATE B.")
add("15.5", B2, P15, D5, D6, 1.0, "Takawira", "Takawira",
    notes="Model and fallback render from ONE filtered fact view, so the fallback cannot disclose more than the model.")
add("15.6", B2, P15, D4, D4, 0.75, LEAD, LEAD,
    act="Golden fact packs and prompt evaluation set - 3 personas x 2 report types",
    notes="All 6 scope_hash values distinct. No fixture figure exceeds its own pack max (live max 25.2, avg 7.46).")
add("15.7", B2, P15, D1, D4, 0.0, "Kagiso", "Kagiso",
    act="Risk: no model available",
    notes="CLOSED. Ollama is installed and running. Residual risk is the pull itself (R20); fallback is pre-agreed.")

# ---------------- BLOCK 3: verification + API ----------------
add("16.1", B3, P16, D5, D5, 0.75, PDEV, PDEV,
    notes="Half of the 1.5 PD verifier effort. Every numeral in prose must exist in the fact pack. "
          "Owned by the second developer so the verifier is not written by the author of the prompt it polices.")
add("16.2", B3, P16, D5, D6, 0.75, PDEV, PDEV,
    notes="Other half. Discard the sentence, not warn.")
add("16.3", B3, P16, D6, D6, 0.25, "Takawira", "Takawira",
    notes="scope_hash identical in envelope, cache key and audit row.")
add("16.4", B3, P16, D6, D6, 0.5, "Takawira", "Takawira",
    act="Deterministic Jinja2 fallback templates (2)",
    notes="Renders with NO model installed - provable on 14 Oct regardless of the pull.")
add("16.5", B3, P16, D6, D6, 0.5, "Takawira", "Takawira",
    notes="S4 claims + S8 numeral fidelity, CI-gated.")
add("16.6", B3, P16, D6, D6, 0.5, "Takawira", "Takawira",
    notes="Scope-widening, province-naming and CVE-injection attempts must all fail AT THE VERIFIER even where the prompt permitted them.")
add("16.7", B3, P16, D7, D7, 0.0, "Takawira", "Takawira",
    act="Risk: high fallback rate from over-strict verification",
    notes="Track fallback_rate per report type on the golden packs.")

add("17.1", B3, P17, D6, D7, 1.0, "Takawira", "Takawira",
    notes="POST /generate, GET /available, GET /audit/{id}. Adds ONE line to app/main.py - see 18.6.")
add("17.2", B3, P17, D6, D6, 0.5, "Takawira", "Takawira",
    notes="authorisation, disclosure, provenance and verification blocks are mandatory on every response.")
add("17.3", B3, P17, D7, D7, 0.0, "Takawira", "Takawira", status="Deferred",
    notes="DEFERRED to Addendum A Phase 17. Cache isolation (S5) needs a Phase 2 window to be meaningful.")
add("17.4", B3, P17, D7, D7, 0.5, "Takawira", "Takawira",
    notes="One audit row AND one ai.report row per generation, in ONE commit across two schemas.")
add("17.5", B3, P17, D7, D7, 0.0, "Takawira", "Takawira", status="Dropped",
    act="Minimal report viewer page",
    deliv="NONE - dropped by direction. The agent is the reporting surface.",
    notes="Dropped by Victoria's direction. The original sheet flagged it as a planning assumption.")
add("17.6", B3, P17, D7, D7, 0.25, "Takawira", "Takawira",
    notes="build_attestation() output byte-identical for the same inputs.")
add("17.7", B3, P17, D7, D7, 0.0, J, J,
    act="Risk: year-end freeze compresses Phase 17",
    notes="Not applicable. Year-end freeze is 3 months after this window.")

add("18.1", B3, P18, D6, D6, 0.25, "Takawira", "Takawira",
    act="S1 role matrix - 14 roles x 2 report types",
    notes="14, not the 11 in the original sheet. The suite fails if the role count changes.")
add("18.2", B3, P18, D6, D7, 0.5, "Takawira", "Takawira",
    act="S2, S3, S4, S7, S8 suites CI-gated",
    notes="S5 cache isolation deferred with 17.3.")
add("18.3", B3, P18, D7, D7, 0.25, "Takawira", "Takawira",
    notes="ruff + semgrep/bandit on the new modules.")
add("18.4", B3, P18, D7, D7, 0.0, "SITA Information Security (Post-PoC Phase 2)", "SITA InfoSec", status="Deferred",
    notes="DEFERRED. Zero SITA employees in build team. Formal SITA InfoSec review occurs in Phase 2 once solution is shipped to SITA environment post-PoC acceptance.")
add("18.5", B3, P18, D7, D7, 0.0, "Takawira", "Takawira", status="Deferred",
    notes="DEFERRED. k6 load test and chaos test need a stable endpoint; nothing is deployed to test against.")
add("18.6", B3, P18, D7, D7, 0.5, J, J,
    act="Diff review against main - restated non-interference claim",
    deliv="git diff main shows additions only; ONE added line in app/main.py; nothing in app/api/, app/processing/, app/tenant.py, app/models/ or the frontend",
    notes="Original claim 'nothing existing modified' is not literally provable - app/main.py is the only router registration point. Restated per ADR D-A8 and briefed to the client in advance (R22).")

add("18.7", B3, P18, D7, D7, 0.0, J, J, status="Deferred",
    act="Risk: critical finding from security review",
    deliv="Deferred with 18.4 (independent security review)",
    notes="DEFERRED. 18.4 (independent security review) is deferred out of the 9-day window; risk cannot occur prior to the 15 Oct demonstration.")

# ---------------- BLOCK 4: demo + sign-off ----------------
add("19.1", B4, P19, D7, D7, 0.0, J, J, status="Deferred",
    notes="DEFERRED. UAT requires UAT-ready documentation and a stable build; the 15 Oct session is a demonstration, not UAT.")
add("19.2", B4, P19, D8, D8, 0.25, "Takawira", "Takawira",
    act="Demonstration defects triaged and logged",
    notes="Fix-forward after the demo, not during it. Carried to the Phase 2 estimate.")
add("19.3", B4, P19, D7, D7, 0.5, "Takawira", "Takawira",
    act="Evidence pack - gate results, live outputs, latency table, diff",
    deliv="docs/G2_POC_2026-10-15/08_Evidence_Pack.md",
    notes="Every gate evidenced by a named test that fails without the corresponding work item.")
add("19.4", B4, P19, D9, D9, 0.0, "Takawira", "Takawira", status="Deferred",
    notes="DEFERRED. Local/staging only for the demonstration. Production deployment is Phase 2.")
add("19.5", B4, P19, D9, D9, 0.5, f"{J} ({J_T}) & {KAG} ({KAG_T})", J,
    act="Acceptance sign-off against the POC criteria",
    deliv="Signed POC acceptance checklist; Phase 2 re-estimate requested rather than a date",
    notes="Asks for a Phase 2 re-estimate, not a date. 29 Jan 2027 is withdrawn - it came from a 145.5 PD estimate that assumed GPU hosting.")
add("19.6", B4, P19, D9, D9, 0.0, J, J,
    act="Schedule contingency buffer",
    notes="Day 9 is the only float and it is the close-out day.")

# Activities whose effort is already carried inside a parent activity's
# estimate. Addendum A costs them as separate rows because they ran over
# weeks with separate owners; inside a 9-day window they are the same work
# done by the same person on the same day, and counting them twice is how a
# 16.75 PD plan becomes a fictional 21.5 PD one.
FOLDED = {
    "13.4": "effort carried in 13.2 / 13.3 - the tests are how those two are proven",
    "13.5": "effort carried in 13.1 - same script, applied to the same local instance",
    "14.2": "effort carried in 14.1 - S6 ships with the accessors it constrains",
    "14.6": "effort carried in 18.2 - same suites, same session",
    "16.3": "effort carried in 16.1 - one verifier module",
    "16.5": "effort carried in 18.2",
    "16.6": "effort carried in 18.2",
    "17.2": "effort carried in 17.1 - the envelope is part of the router response",
    "17.6": "effort carried in 18.2",
    "18.1": "effort carried in 18.2",
    "18.2": "effort carried in 19.3 - the evidence pack is the suites' output",
    "18.3": "effort carried in 18.6 - same diff-review session",
    "19.2": "effort carried in 19.5",
    "19.7": "effort carried in 14.5 - the tripwire tests the fact pack",
}
for a in A:
    if a["ref"] in FOLDED:
        a["pd"] = 0.0
        a["notes"] = (a["notes"] + "  ||  " + FOLDED[a["ref"]]).strip(" |")

# ---- New activity not present in Addendum A at all ----
add("14.8", B2, P14, D3, D3, 0.5, "Takawira", "Takawira",
    act="capability.py - table introspection gate and NEVER_READ denial",
    deliv="SCOPABLE / REFERENCE / UNSCOPABLE / NEVER_READ classification; identity.users and audit.action_audit raise at import; every registered table classified",
    notes="NEW - not in Addendum A. Neither G1 nor G2 considered that users (password_hash, roles, tenancy assignment) and action_audit (actor + every prior user's scope) are agent-readable. Highest-severity finding of the assessment.",
    risks="R23 - agent-readable identity and authorisation surface if rushed")
add("19.7", B4, P19, D7, D7, 0.25, "Takawira", "Takawira",
    act="Risk-bucket divergence tripwire test",
    deliv="test asserts 0 rows with 30 < fused_score < 45; failure message names all three bucket definitions",
    notes="NEW - not in Addendum A. risk_engine.py:78 uses safe<=30; exports_ag.py:40 and benchmark.py:38 use safe<45. Latent today (0 rows in band); G2 makes it detected rather than fixed.")

# ---------------------------------------------------------------- build
# Normalise the delivery roles to full name + title, so the addendum is readable
# standalone. Takawira Mazando (Lead Developer, G2) and Peter Rashaya (Second
# Developer, G2) are the two builders: they are peers, and no activity is
# co-owned. Richard Masukume (Head of AI Research) is ADVISORY in this window -
# he owns one task (T01, the model pull and latency measurement) and reviews at
# the gates; he authors no production code and no tests.
for a in A:
    if a["primary"] == "Takawira":
        a["primary"], a["owner"] = LEAD, f"{LEAD} ({LEAD_T})"
    elif a["primary"] == "Richard":
        a["primary"], a["owner"] = AI, f"{AI} ({AI_T})"
    elif a["primary"] == PDEV:
        a["primary"], a["owner"] = PDEV, f"{PDEV} ({PDEV_T})"
    elif a["primary"] == J:
        a["primary"], a["owner"] = J, f"{J} ({J_T})"
    elif a["primary"] == VIC:
        a["primary"], a["owner"] = VIC, f"{VIC} ({VIC_T})"
    elif a["primary"] == KAG:
        a["primary"], a["owner"] = KAG, f"{KAG} ({KAG_T})"

total = sum(a["pd"] for a in A)
src_total = 145.5

# Effort that draws on developer capacity (Takawira / Peter) as opposed to
# governance, compliance, sponsor, PM or advisory effort. Only build effort
# competes for the 7-day engineering window.
DEV = {LEAD, PDEV}
dev_total = sum(a["pd"] for a in A if a["primary"] in DEV)
gov_total = total - dev_total

HDR = ["Project Phases", "Key Activity Description", "Status", "Pencentage",
       "Start Date", "End Date", "Owner", "Deliverable", "Risks",
       "Dependancies", "Obstacles", "Notes/Remarks/Comments", "Ref",
       "Effort (person-days)", "Primary Owner", "Phase No."]

# ================================================================= GRANULAR TASKS
# The flight-plan rows above are Addendum A's own activities. They are too coarse
# to execute from: several span three days and two people. This is the actual
# work breakdown - one row per thing someone opens an editor for.
#
# OWNERSHIP (Plan v4). One developer carries the window:
#   Takawira (Lead Developer, G2)  owns 34 of 39 tasks - 11.75 PD / 94.0 h.
#       Deterministic backend: schema, gates, scope, capability, accessors,
#       fact packs, prompts, orchestration, router, audit, tests.
#   Peter Rashaya (Second Developer, G2)  owns 3 tasks - 1.50 PD / 12.0 h.
#       T13 structural test, T23 the four-check verifier, T30 live containment.
#   Richard Masukume (Head of AI Research)  owns 1 task - 0.50 PD / 4.0 h, T01,
#       the model pull and latency measurement. ADVISORY: he authors no
#       production code and no tests, and reviews at the gates and at freeze.
#   Jerry Mokone (Project Manager)  owns 1 task - 0.50 PD / 4.0 h, T36, the
#       evidence pack.
#
# The three control claims this plan rests on, and what happens to each under
# this ownership:
#   1. The verifier is not written by the prompt author.  HOLDS. T23 (Peter)
#      versus T14 and T16 (Takawira).
#   2. Ground truth is not authored by the model author.  DOES NOT HOLD in the
#      structural sense that was originally claimed - Takawira owns both the
#      scope/capability/accessors/context layer AND the prompt builder. It is
#      restated as: scope and capability DELEGATE to tenant_filter() and SQL
#      introspection, neither of which can be widened from the prompt; the
#      prompt builder only serialises facts the pack already contains
#      (pack.serialise(allowed=claims)); the containment proof is run live by
#      T30, authored by Peter, not by the prompt author.
#   3. The structural filter cannot be bypassed by prompt text.  HOLDS.
#      pack.serialise(allowed=claims) is a code boundary.
#
# Sat 10 Oct is worked by Takawira alone - no other resource is scheduled.
#
# Fields: id, day, task, owner, support, artefact, acceptance test, gate ref, pd
T = [
    # ---------------- DAY 1 — Wed 7 Oct ----------------
    ("T01", 1, "Pull qwen2.5:3b; verify it serves; measure CPU latency at max_tokens 300 / 600 / 900",
     AI, LEAD, "backend/bench/probe_model.py, backend/bench/model_latency.md",
     "`ollama list` shows qwen2.5:3b; latency table covers all three budgets; max_tokens chosen from the measurement, not guessed. "
     "0.50 PD charged at 0.5 h on each non-Saturday day of the window (days 1,2,3,5,6,7,8,9) rather than as a 4.0 h block on day 1: the pull happens on day 1, the latency measurement is revisited as the cache and token budget settle, and the final table is closed into the evidence pack on day 9.", "-", 0.50),
    ("T21", 1, "gateway.py + app/ai/settings.py — httpx to Ollama, CircuitBreaker reuse, token budget",
     LEAD, AI, "backend/app/ai/gateway.py, backend/app/ai/settings.py",
     "Reuses app/ingestion/circuit_breaker.py by identity. Day-1 setup ensures runtime is verified before prompt work.", "-", 0.50),
    ("T02", 1, "init-ai-schema.sql — schema ai, ai.report, 2 indexes, idempotent",
     LEAD, "-", "infrastructure/scripts/init-ai-schema.sql",
     "Runs twice cleanly; table present in information_schema; model_id, model_digest, prompt_version, latency_ms, fallback_used all present (D5)", "-", 0.25),
    ("T03", 1, "Apply ai schema to the local sita instance; record the rehearsal",
     LEAD, "-", "migration rehearsal log",
     "ai.report present in the live local database", "-", 0.00),
    ("T04", 1, "permissions.py — REPORT_AI_PERMISSIONS, ROLE_REPORT_AI, require_report_permission()",
     LEAD, "-", "backend/app/ai/permissions.py",
     "Additive namespace; ROLES_HIERARCHY untouched; exec denied soc_shift_handover", "GATE A", 0.50),
    ("T05", 1, "permissions tests — unknown role 403, role count enumerated from ROLES_HIERARCHY",
     LEAD, "-", "backend/tests/test_ai_permissions.py",
     "14 roles enumerated, not the 11 in the original sheet; suite fails if the count changes", "GATE A", 0.25),

    # ---------------- DAY 2 — Thu 8 Oct ----------------
    ("T06", 2, "scope.py — frozen ReportScope, resolve_report_scope(), scope_hash via canonical_json",
     LEAD, AI, "backend/app/ai/scope.py",
     "Frozen (assignment raises); scope_hash order-independent and scope-sensitive; delegates to tenant_filter(), never re-implements it", "GATE A", 0.50),
    ("T07", 2, "Province-slug validation — fail LOUDLY on an unknown slug",
     LEAD, "-", "backend/app/ai/scope.py (validation branch)",
     "province_ids=['gauteng'] raises a named error. Today it silently returns 0 rows, indistinguishable from correct scoping.", "GATE A", 0.25),
    ("T08", 2, "capability.py — introspection gate: SCOPABLE / REFERENCE / UNSCOPABLE",
     LEAD, AI, "backend/app/ai/capability.py",
     "Every registered table classified. departments/branches/provinces are REFERENCE — labels only, never disclosed", "GATE A", 0.25),
    ("T09", 2, "capability.py — NEVER_READ denial for identity.users and audit.action_audit",
     LEAD, "-", "backend/app/ai/capability.py + test_ai_capability.py",
     "Both raise at import. users carries password_hash and every user's tenancy assignment; action_audit carries every prior user's scope. No read path exists.", "GATE A", 0.00),
    ("T10", 2, "claims.py — ClaimClass, ROLE_CLAIMS, claim-pattern registry",
     LEAD, AI, "backend/app/ai/claims.py",
     "exec holds none of cve_ids/alert_ids/owner_names/rule_ids. Matrix asserted equal to the signed D4 draft. No empty regex — an empty pattern matches everything.", "GATE A", 0.75),
    ("T11", 2, "disclosure.py — three DisclosureClass values + estate-wide summary",
     LEAD, AI, "backend/app/ai/disclosure.py",
     "TENANT_SCOPED / ESTATE_WIDE / DERIVED_FROM_ESTATE_WIDE. Every risk_scores-sourced figure is DERIVED — the estate-wide component is inside fused_score itself. No REFERENCE value is ever tagged.", "GATE A", 0.25),

    # ---------------- DAY 3 — Fri 9 Oct ----------------
    ("T12", 3, "accessors.py — read_risk_scores(scope, db), read_compliance(scope, db)",
     LEAD, AI, "backend/app/ai/accessors.py",
     "scope is the FIRST POSITIONAL parameter on every reader. Aggregates in SQL — mappers.ts is NOT ported.", "GATE B", 0.75),
    ("T13", 3, "S6 structural test — signature inspection across accessors.py",
     PDEV, "-", "backend/tests/test_ai_accessors.py",
     "100% scope-first coverage, asserted by introspection. Fails the build if a warehouse reader appears without scope. "
     "Authored by the second developer against T12, which the Lead Developer wrote — the structural guarantee is checked by someone who did not build the readers.", "GATE B", 0.25),
    ("T14", 3, "Prompt builder — build_prompt(scope, report_type, pack); facts filtered to the claim set",
     LEAD, AI, "backend/app/ai/prompt_builder.py",
     "pack.serialise(allowed=claims) — an unheld fact is ABSENT from the prompt, not merely forbidden. Scope block labelled for_attribution. "
     "Ground truth is NOT authored here: scope and capability delegate to tenant_filter() and SQL introspection, and the builder only serialises facts the pack already contains.", "GATE B", 0.75),
    ("T15", 3, "Role-injection harness — prove two roles produce different serialised prompts",
     LEAD, "-", "backend/tests/test_ai_prompt.py",
     "Assertion is on allowed_claim_classes and on facts present, not string inequality", "GATE B", 0.25),

    # ---------------- DAY 4 — Sat 10 Oct (Takawira solo) ----------------
    ("T16", 4, "Prompt templates — executive_briefing.v1, compliance_status.v1 (code-assembled, versioned)",
     LEAD, AI, "backend/app/ai/prompts/*.v1.py",
     "Immutable. Temperature 0.2. Constrained narrative output. 2 of the catalogue's 8 report types.", "GATE C", 0.50),
    ("T17", 4, "context.py — build_executive_context(): pure builder, SQL aggregation, fact_pack_hash",
     LEAD, AI, "backend/app/ai/context.py",
     "Pure — testable with no database, the shape of build_attestation(). risk_scores.bucket read from the column, never recomputed. Unknown severities get an explicit unknown bucket, not the frontend's silent fold to info.", "GATE C", 0.75),
    ("T18", 4, "context.py — build_compliance_context() + estate-wide tagging",
     LEAD, "-", "backend/app/ai/context.py",
     "456 snapshots + 228 gaps tagged ESTATE_WIDE; the notice string comes from D-A6, defaulting to the envelope-only form until Compliance ratifies", "GATE C", 0.25),
    ("T19", 4, "Eval set — 3 personas x 2 report types = 6 fixtures with distinct scope_hash",
     LEAD, AI, "backend/tests/fixtures/ai_eval/*.json, test_ai_eval.py",
     "All 6 scope_hash values distinct. No fixture figure exceeds its own pack max (live max 25.2, avg 7.46). Supported by Victoria — 0.75 PD of BA support, all of it delivered on Friday 9 Oct ahead of this task.", "GATE C", 0.50),
    ("T20", 4, "First end-to-end generation from a real fact pack",
     LEAD, AI, "-",
     "A narrative is produced from live, scoped data. If the model failed to pull, the fallback produces it instead — identical numbers.", "GATE C", 0.00),

    # ---------------- DAY 5 — Mon 12 Oct ----------------
    ("T22", 5, "generate.py — assemble → generate → verify → return; ONE filtered fact view for both renderers",
     LEAD, PDEV, "backend/app/ai/generate.py",
     "The fallback's input is the same object identity as the prompt's fact argument. It cannot disclose more than the model does.", "GATE D", 0.75),
    ("T23", 5, "verify.py — numeral fidelity + claim filter + scope containment + attribution",
     PDEV, LEAD, "backend/app/ai/verify.py",
     "THE most heavily tested module in the POC. Four checks, each with a positive and a negative test. Shares no code path with the prompt builder. "
     "Owned by the second developer: T14 and T16, the prompt builder and templates, are the Lead Developer's work, so the verifier is written by "
     "someone who did not write the prompt it polices. Tested by T31 and T32, which the Lead Developer wrote.", "GATE D", 1.00),
    ("T24", 5, "fallback.py — 2 deterministic Jinja2 templates",
     LEAD, "-", "backend/app/ai/fallback.py",
     "Renders with NO model installed. Provable on 14 Oct regardless of the pull (R20).", "GATE D", 0.25),
    ("T25", 5, "Verifier failure paths return the template, never model text",
     LEAD, PDEV, "test_ai_generate.py",
     "Enforced by the return type being a union, not a nullable string. No partial credit, no warning-only mode (R6).", "GATE D", 0.00),

    # ---------------- DAY 6 — Tue 13 Oct ----------------
    ("T26", 6, "reports_ai.py — POST /generate, GET /available, GET /audit/{id}",
     LEAD, PDEV, "backend/app/ai/routers/reports_ai.py",
     "All data routes POST — avoids the demoInterceptor GET hijack. /available returns only what THIS caller may request.", "GATE E", 0.50),
    ("T27", 6, "Response envelope — authorisation, disclosure, provenance, verification",
     LEAD, "-", "reports_ai.py (envelope)",
     "All four blocks mandatory on every response, including the fallback path (model_id null, fallback_used true).", "GATE E", 0.00),
    ("T28", 6, "ActionAudit 'ai_report_generated' + ai.report write",
     LEAD, "-", "audit write in reports_ai.py",
     "One audit row AND one ai.report row per generation, in ONE commit across two schemas. AI rows never appear in an attestation.", "GATE E", 0.25),
    ("T29", 6, "Register the router — ONE added line in app/main.py",
     LEAD, "-", "app/main.py (single line)",
     "The only change to any existing file. app/main.py is the sole router registration point.", "GATE E", 0.00),
    ("T30", 6, "S2 scope containment + S3 non-escalation, live against the database",
     PDEV, LEAD, "test_ai_containment.py",
     "DHA soc 745 rows vs exec 2244, different scope_hash. Provincial persona widening scope yields expression.false() → 0, never estate-wide. "
     "Run live by the second developer against T06, T08 and T12, which the Lead Developer wrote — so the containment proof is not written by the author of the scope layer it proves.", "GATE E", 0.25),
    ("T31", 6, "S4 claims + S8 numeral fidelity + S7 capability, CI-gated",
     LEAD, PDEV, "test_ai_claims.py, test_ai_verify.py, test_ai_capability.py",
     "exec report contains zero CVE ids, alert ids, owner names, rule ids. Injected CVE id → sentence discarded. "
     "This suite is the principal test of T23, which Peter wrote — the harness and the verifier are not the same pair of hands.", "GATE E", 0.50),
    ("T32", 6, "S9 adversarial — scope widening, province naming, CVE injection, prompt injection via warehouse text",
     LEAD, PDEV, "test_ai_adversarial.py",
     "Every attempt rejected AT THE VERIFIER, even where the prompt permitted it. The prompt is not the control.", "GATE E", 0.50),

    # ---------------- DAY 7 — Wed 14 Oct ----------------
    ("T33", 7, "Bucket-divergence tripwire — assert 0 rows with 30 < fused_score < 45",
     LEAD, AI, "backend/tests/test_ai_bucket_band.py",
     "Passes today (0 rows in band; all 15283 rows are 5.0-25.2). Failure message names all three bucket definitions: risk_engine.py:78, exports_ag.py:40, benchmark.py:38. Owned by the Lead Developer — this is a warehouse-layer regression guard.", "FREEZE", 0.25),
    ("T38", 7, "Integration smoke test — POST /api/v1/reports-ai/generate end-to-end with exec and soc roles",
     LEAD, AI, "backend/tests/test_ai_integration.py",
     "Two roles, two scope_hash values, two distinct narratives. Asserts envelope structure, disclosure class, provenance block. Last regression gate before freeze.", "FREEZE", 0.25),
    ("T34", 7, "Full regression — ruff clean, pytest green, no existing test regressed",
     LEAD, AI, "-",
     "Exactly the commands CI runs. The 11 existing test modules must stay green.", "FREEZE", 0.50),
    ("T35", 7, "Diff review — the restated non-interference claim",
     LEAD, J, "git diff main --stat",
     "Additions only. ONE added line in app/main.py. Nothing in app/api/, app/processing/, app/tenant.py, app/models/ or the frontend. "
     "Reviewed with Richard, whose 0.5 h advisory on day 7 explicitly covers this diff — that review is the independent check on a task whose owner also wrote most of the code.", "FREEZE", 0.00),
    ("T36", 7, "Evidence pack — every gate evidenced by a named failing test",
     J, LEAD, "docs/G2_POC_2026-10-15/08_Evidence_Pack.md",
     "Each gate traced to the test that fails without the corresponding work item. Plus the latency table and the diff. Owned by the Project Manager so the evidence is assembled by someone who did not write the code it certifies.", "FREEZE", 0.50),
    ("T37", 7, "Demo rehearsal end-to-end, timed, on day-7 hardware",
     LEAD, AI, "-",
     "All 9 run-sheet items in order within 23 minutes. R21 is a CPU-latency risk; rehearsal on the freeze day is the only mitigation that works.", "FREEZE", 0.50),
    ("T37b", 7, "Demo rehearsal AI controls & latency validation",
     LEAD, AI, "-",
     "Validate prompt latency under 300/600 token limits; ensure fallback activation is seamless under model delay.", "FREEZE", 0.25),
]

# Granular tasks follow the same folding rule as the activity rows above: a test
# is how its implementation is proven, not a separate sitting. Addendum A could
# afford to cost them apart because they ran over weeks with different owners.
T_FOLDED = {
    "T03": ("T02", "same script, same instance"),
    "T09": ("T08", "part of capability.py, same import assertion"),
    "T20": ("T19", "the first generation IS the Gate C evidence"),
    "T25": ("T24", "the union return type is the proof; the test just asserts it"),
    "T27": ("T26", "the envelope is part of the router response, not a separate artefact"),
    "T29": ("T26", "router registration is part of reports_ai.py delivery"),
    "T35": ("T34", "diff review executed as part of full regression freeze"),
}
T = [tuple(t) for t in T]
_i = {t[0]: n for n, t in enumerate(T)}
for tid, (parent, why) in T_FOLDED.items():
    n = _i[tid]
    row = list(T[n])
    row[8] = 0.0
    row[6] = row[6] + f"  ||  Effort carried in {parent}: {why}."
    T[n] = tuple(row)

# Register totals, computed once so the workbook cannot quote two different
# numbers for the same thing. Every sheet below reads these.
REG_PD = round(sum(t[8] for t in T), 2)
REG_H = round(REG_PD * PD_HOURS, 1)
t_pd = sum(x[8] for x in T if x[3] == LEAD)
p_pd = sum(x[8] for x in T if x[3] == PDEV)
BUILD_CAP_PD = 14.0
BUILD_CAP_H = BUILD_CAP_PD * PD_HOURS
build_pd = round(sum(x[8] for x in T if x[3] in DEV), 2)
build_h = round(build_pd * PD_HOURS, 1)

thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
hfill = PatternFill("solid", fgColor="1F3864")
hfill2 = PatternFill("solid", fgColor="2E75B6")
bfill = PatternFill("solid", fgColor="D9E2F3")
wrap = Alignment(wrap_text=True, vertical="top")
ctr = Alignment(horizontal="center", vertical="center", wrap_text=True)

wb = openpyxl.Workbook()

# ---- Sheet 1: flight plan ----
ws = wb.active
ws.title = "Addendum B - Phase 13 Plan"
ws["A1"] = ("ADDENDUM B TO THE HOSI-UNIFIED FLIGHT PLAN - PHASE 13: AI REPORT GENERATION "
            "(9-DAY PROOF OF CONCEPT)")
ws["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws["A1"].fill = hfill
ws.merge_cells("A1:P1")
ws.row_dimensions[1].height = 26
ws["A2"] = (f"Extends HOSI-UNIFIED_DATA_MANAGED_SERVICE_PROJECT_FLIGHT_PLAN_2026 (20 August 2026), "
            f"Phases 1-12, 99 of 100 activities complete. This addendum ADDS Phase 13 as an additive "
            f"backend stage - it does not amend, replace or renumber any existing phase. "
            f"THE INTEGRATION: the master pipeline ends at Stage 4 (FastAPI REST layer, Phase 9). "
            f"Every stakeholder figure today is fixed arithmetic or hand-authored prose. "
            f"Phase 13 inserts an AI report-generation stage into the backend that reads FROM the "
            f"warehouse built in Phase 7 and returns JSON to the existing Phase 10 dashboards. "
            f"Compresses Addendum A ({src_total} PD, 18 weeks) to {total} PD over 9 working days: "
            f"build 7-14 October (Saturday 10 October is a working day, worked by {LEAD} alone), "
            f"client demonstration 15 October 2026, close-out 16 October. "
            f"Delivery: {LEAD} ({LEAD_T}) and {PDEV} ({PDEV_T}) as builders, with {AI} ({AI_T}) advisory.")
ws["A2"].font = Font(italic=True, size=9)
ws["A2"].alignment = wrap
ws.merge_cells("A2:P2")
ws.row_dimensions[2].height = 72

meta = [
    ("Lead Developer, G2 (builder)", f"{LEAD} - {sum(x[8] for x in T if x[3] == LEAD):.2f} PD / {sum(x[8] for x in T if x[3] == LEAD) * PD_HOURS:.1f} h across {sum(1 for x in T if x[3] == LEAD)} tasks, incl. 38.0 h overtime"),
    ("Second Developer, G2 (builder)", f"{PDEV} - {sum(x[8] for x in T if x[3] == PDEV):.2f} PD / {sum(x[8] for x in T if x[3] == PDEV) * PD_HOURS:.1f} h across {sum(1 for x in T if x[3] == PDEV)} tasks (verifier and containment)"),
    ("Head of AI Research (advisory)", f"{AI} - {sum(x[8] for x in T if x[3] == AI):.2f} PD in-register (T01), plus 4.0 h of gate and freeze review"),
    ("Governance / PM / Compliance", f"Jerry Mokone ({J} owns T36), Victoria Nedombeloni, Kagiso Mokgofa - {gov_total:.2f} PD, outside builder capacity"),
    ("Total Activities", len(A)),
    ("Granular executable tasks", len(T)),
    ("Granular register in hours", f"{REG_H:.1f} h (1 PD = 8.0 h)"),
    ("Build demand vs capacity", f"{build_pd:.2f} PD / {build_h:.1f} h against {BUILD_CAP_PD:.2f} PD / {BUILD_CAP_H:.1f} h — float {BUILD_CAP_PD - build_pd:.2f} PD / {BUILD_CAP_H - build_h:.1f} h"),
    ("Grand total, all resources", f"{GRAND_HOURS:.1f} h across 7-16 October"),
    ("In scope (9 days)", sum(1 for a in A if a["status"] != "Deferred" and a["status"] != "Dropped")),
    ("Deferred to Addendum A / Phase 2", sum(1 for a in A if a["status"] == "Deferred")),
    ("Dropped by direction", sum(1 for a in A if a["status"] == "Dropped")),
    ("Total effort (person-days)", total),
    ("Addendum A effort (person-days)", src_total),
    ("Effort deferred", round(src_total - total, 1)),
    ("Planned start", D1), ("Client demonstration", D8), ("Window close", D9),
]
for i, (k, v) in enumerate(meta, start=3):
    ws.cell(row=i, column=1, value=k).font = Font(bold=True, size=9)
    ws.cell(row=i, column=2, value=v).font = Font(size=9)
ws.cell(row=3, column=1).fill = PatternFill("solid", fgColor="DEEBF7")
ws.cell(row=4, column=1).fill = PatternFill("solid", fgColor="FFF2CC")

hr = 20
for c, h in enumerate(HDR, start=1):
    cell = ws.cell(row=hr, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box

r = hr + 1
last_block = None
for a in A:
    if a["block"] != last_block:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=16)
        bc = ws.cell(row=r, column=1, value=a["block"])
        bc.font = Font(bold=True, size=10, color="1F3864")
        bc.fill = bfill
        bc.alignment = Alignment(vertical="center")
        r += 1
        last_block = a["block"]
    if a["phase"] != getattr(A, "_lastphase", None):
        pass
    vals = [a["block"], a["activity"], a["status"], a["pct"] / 100,
            a["start"].date(), a["end"].date(), a["owner"], a["deliverable"],
            a["risks"], a["deps"], "", a["notes"], a["ref"], a["pd"],
            a["primary"], int(a["phase"].split(":")[0].replace("Phase ", ""))]
    for c, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap
        cell.border = box
        if c in (4, 5, 6, 13, 14, 16):
            cell.alignment = ctr
        if c in (5, 6):
            cell.number_format = "yyyy-mm-dd"
        if c == 14:
            cell.number_format = "0.00"
        if a["status"] == "Deferred":
            cell.font = Font(size=9, italic=True, color="808080")
        elif a["status"] == "Dropped":
            cell.font = Font(size=9, italic=True, color="C00000")
        elif a["status"] == "Completed":
            cell.font = Font(size=9, color="375623")
    r += 1

tr = r
ws.merge_cells(start_row=tr, start_column=1, end_row=tr, end_column=12)
ws.cell(row=tr, column=1, value="TOTAL").font = Font(bold=True, size=10)
_act = ws.cell(row=tr, column=13, value=f"{len(A)} activities")
_act.font = Font(bold=True, size=10)
_act.alignment = ctr
ws.cell(row=tr, column=14, value=total).font = Font(bold=True, size=10)
ws.cell(row=tr, column=14).number_format = "0.00"
for c in range(1, 17):
    ws.cell(row=tr, column=c).border = box

widths = {1: 34, 2: 52, 3: 12, 4: 9, 5: 11, 6: 11, 7: 22, 8: 46, 9: 16,
          10: 14, 11: 10, 12: 62, 13: 8, 14: 11, 15: 17, 16: 8}
for c, w in widths.items():
    ws.column_dimensions[get_column_letter(c)].width = w
for i in range(hr + 1, tr + 1):
    ws.row_dimensions[i].height = 44
ws.row_dimensions[hr].height = 30
ws.freeze_panes = f"B{hr + 1}"
ws.auto_filter.ref = f"A{hr}:P{tr - 1}"

# Granular tasks follow the same folding rule as the activity rows above: a test
# is how its implementation is proven, not a separate sitting. Addendum A could
# afford to cost them apart because they ran over weeks with different owners.
T_FOLDED = {
    "T03": ("T02", "same script, same instance"),
    "T09": ("T08", "part of capability.py, same import assertion"),
    "T20": ("T19", "the first generation IS the Gate C evidence"),
    "T25": ("T24", "the union return type is the proof; the test just asserts it"),
    "T27": ("T26", "the envelope is part of the router response, not a separate artefact"),
    "T29": ("T26", "router registration is part of reports_ai.py delivery"),
    "T35": ("T34", "diff review executed as part of full regression freeze"),
}
# ---------------- Sheet 0: integration into the master pipeline ----------------
ws0 = wb.create_sheet("Integration", 0)
ws0["A1"] = ("HOW PHASE 13 INTEGRATES INTO THE EXISTING BACKEND PIPELINE   ·   "
             "build 7-14 October 2026, Saturday 10 October included")
ws0["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws0["A1"].fill = hfill
ws0.merge_cells("A1:D1")
ws0["A2"] = ("The master flight plan (Phases 1-12) built a working warehouse and six dashboards. "
             "Phase 13 does not replace any of it - it adds the reporting intelligence layer the "
             "pipeline currently lacks, reading the warehouse the plan already built.")
ws0["A2"].font = Font(italic=True, size=9)
ws0["A2"].alignment = wrap
ws0.merge_cells("A2:D2")
ws0.row_dimensions[2].height = 30

for c, h in enumerate(["Master plan stage", "Built by", "Status today", "Phase 13 relationship"], start=1):
    cell = ws0.cell(row=4, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box

STAGES = [
    ("1. OEM Ingestion", "Phase 1-4 (AppScan, Imperva, API Sec)", "Complete",
     "Unchanged. No AI on the ingestion path."),
    ("2. Normalise & Stage", "Phase 5", "Complete", "Unchanged."),
    ("3. Warehouse + Risk Engine", "Phase 6-7 (risk_engine.py:14, 4-signal weighted fusion)",
     "Complete - 15 283 risk rows, 2 244 findings, 456 snapshots",
     "READ-ONLY INPUT. Phase 13 reads warehouse.* through tenant_filter() and recomputes nothing."),
    ("4. FastAPI REST layer", "Phase 9 (tenant_filter() at app/api/auth.py:210)",
     "Complete - 6 role-gated endpoints",
     "EXTENDED. Adds POST /api/v1/reports-ai/generate. One include_router line in app/main.py "
     "is the only edit to any existing file."),
    ("5. React dashboards", "Phase 10 (6 dashboards, explanations.ts prose)", "Complete",
     "UNTOUCHED in the POC. The generated report is a separate surface; wiring it into "
     "DashHeader's children slot is Phase B."),
    ("6. Reports & exports", "Phase 9 (CSV exports, AG attestation)", "Complete",
     "UNTOUCHED. build_attestation() stays pure and deterministic; the AI narrative never "
     "enters the signed attestation (D3)."),
]
r = 5
for s in STAGES:
    for c, v in enumerate(s, start=1):
        cell = ws0.cell(row=r, column=c, value=v)
        cell.font = Font(size=9, bold=(c == 1))
        cell.alignment = wrap
        cell.border = box
        if c == 3:
            cell.fill = PatternFill("solid", fgColor="E2EFDA")
    ws0.row_dimensions[r].height = 46
    r += 1

r += 1
ws0.cell(row=r, column=1, value="REUSED, NOT REBUILT - every one of these already exists in the master plan's codebase")
ws0.cell(row=r, column=1).font = Font(bold=True, size=10, color="1F3864")
ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
r += 1
for c, h in enumerate(["Existing asset", "Location", "Built by", "How Phase 13 uses it"], start=1):
    cell = ws0.cell(row=r, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
REUSE = [
    ("tenant_filter()", "app/api/auth.py:210", "Phase 9",
     "DELEGATED, never reimplemented. It is opt-in per query, so Phase 13 makes scope a mandatory "
     "positional argument instead of a thing to remember."),
    ("canonical_json() / sha256_hex()", "app/api/routers/exports_ag.py:48,58", "Phase 9",
     "Reused for scope_hash and fact_pack_hash. Reimplementing hashing is how two components end up "
     "disagreeing on what 'the same payload' means."),
    ("build_attestation() pattern", "app/api/routers/exports_ag.py:62", "Phase 9",
     "The pure-builder shape the fact-pack builder copies: no DB, no session, no claims inside the "
     "builder, so it is unit-testable without a database."),
    ("CircuitBreaker", "app/ingestion/circuit_breaker.py:11", "Phase 3",
     "Reused for the model gateway. Model down -> breaker opens -> deterministic fallback. "
     "Same failure handling the OEM connectors already use."),
    ("audit.action_audit", "infrastructure/scripts/init-db.sql:120", "Phase 7",
     "The audit sink. One row per generation, same retention, AI rows never appear in an attestation."),
    ("_build_benchmark() peer blinding", "app/api/routers/benchmark.py:46", "Phase 9",
     "PRECEDENT, not code reuse. A provincial exec sees peers as 'Peer Province A/B/C' with "
     "province_id null. That is claim-class blinding already working in deterministic Python."),
    ("DOMPurify sanitise", "frontend/src/components/dashboard/ExplainOverlay.tsx:17", "Phase 10",
     "Phase B only. Narrative HTML already has a sanitising render path in production."),
    ("DashHeader children slot", "frontend/src/components/dashboard/DashHeader.tsx:36", "Phase 10",
     "Phase B only. Mounts the AI control on all 6 dashboards with zero route changes."),
]
r += 1
for x in REUSE:
    for c, v in enumerate(x, start=1):
        cell = ws0.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap
        cell.border = box
    ws0.row_dimensions[r].height = 40
    r += 1

r += 1
ws0.cell(row=r, column=1, value="NEW OBJECTS CREATED BY THIS ADDENDUM - nothing existing is modified except one line")
ws0.cell(row=r, column=1).font = Font(bold=True, size=10, color="C00000")
ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
r += 1
NEW = [
    ("backend/app/ai/", "14 modules: permissions, scope, capability, accessors, context, "
     "disclosure, claims, prompt_builder, prompts/, gateway, settings, generate, fallback, verify",
     "New namespace. ROLES_HIERARCHY is not modified; the permission namespace is additive."),
    ("backend/app/ai/routers/reports_ai.py", "POST /generate, GET /available, GET /audit/{id}",
     "All data routes POST, avoiding the demoInterceptor GET hijack in "
     "frontend/src/api/demoInterceptor.ts:34-42."),
    ("infrastructure/scripts/init-ai-schema.sql", "schema ai, ai.report, 2 indexes",
     "Kept out of warehouse.* so no existing reporting query can return an AI row by accident."),
    ("backend/tests/test_ai_*.py", "S1 role matrix, S2 containment, S3 non-escalation, "
     "S4 claims, S6 signature, S7 capability, S8 numeral fidelity, S9 adversarial",
     "CI-gated. S6 fails the build if a warehouse reader appears without a scope parameter."),
    ("app/main.py", "ONE added line: app.include_router(reports_ai.router, prefix='/api/v1')",
     "UNAVOIDABLE - it is the only router registration point in the codebase. Additive, no logic "
     "changed. Restated claim per R22; briefed to the client before the demo."),
]
for x in NEW:
    for c, v in enumerate(x, start=1):
        cell = ws0.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap
        cell.border = box
    ws0.row_dimensions[r].height = 46
    r += 1

r += 1
ws0.cell(row=r, column=1, value="THE GAP PHASE 13 FILLS").font = Font(bold=True, size=10, color="1F3864")
ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
r += 1
for txt in [
    "Today every insight a stakeholder sees is FIXED: a weighted sum (app/processing/risk_engine.py:14), "
    "a YAML rule evaluation (app/processing/alert_rules.yaml), or hand-authored HTML prose "
    "(frontend/src/data/explanations.ts buildExplain/buildLayman).",
    "That prose has already drifted. Verified against the live database, explanations.ts claims "
    "'60 departments' where the warehouse holds 173, and states database inventory and system "
    "metrics are 'not tracked by the backend yet' when warehouse.database_inventory holds 2 577 rows "
    "and system_metrics holds 95.",
    "Hand-authored narrative rots silently. A narrative generated from a fact pack cannot - which is "
    "the strongest practical argument for Phase 13, independent of any security argument.",
]:
    ws0.cell(row=r, column=1, value="- " + txt).font = Font(size=9)
    ws0.cell(row=r, column=1).alignment = wrap
    ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    ws0.row_dimensions[r].height = 32
    r += 1

for c, w in {1: 32, 2: 44, 3: 40, 4: 78}.items():
    ws0.column_dimensions[get_column_letter(c)].width = w

# ---------------- Sheet 1b: granular task breakdown ----------------
ws1b = wb.create_sheet("Task Breakdown (Granular)", 1)
ws1b["A1"] = f"GRANULAR TASK BREAKDOWN — {len(T)} executable tasks, 7 to 16 October 2026"
ws1b["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws1b["A1"].fill = hfill
ws1b.merge_cells("A1:J1")
ws1b["A2"] = (f"Lead Developer, G2: {LEAD} (11.75 PD / 94.0 h, 34 tasks)   ·   "
              f"Second Developer, G2: {PDEV} (1.50 PD / 12.0 h, 3 tasks)   ·   "
              f"Head of AI Research: {AI} (advisory — 0.50 PD / 4.0 h in-register, T01 only)   ·   "
              f"Project Manager: {J} (0.50 PD / 4.0 h, T36 evidence pack)   ·   "
              f"Register total: {len(T)} tasks · {REG_PD:.2f} PD · {REG_H:.1f} h. "
              f"The two builders are peers and no task is co-owned. Saturday 10 October is worked by {LEAD} alone.")
ws1b["A2"].font = Font(italic=True, size=9)
ws1b.merge_cells("A2:J2")
ws1b["A3"] = ("Every task is one editor session with a named artefact and a test that fails if the task is not done. "
              "Gate column references the exit criteria on 'The 9 Days' sheet. "
              "Hours column is PD x 8.0.")
ws1b["A3"].font = Font(italic=True, size=9, color="C00000")
ws1b.merge_cells("A3:J3")

H1B = ["ID", "Day", "Task", "Owner", "Support", "Artefact", "Acceptance test", "Gate", "PD", "Hours"]
for c, h in enumerate(H1B, start=1):
    cell = ws1b.cell(row=5, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box

DAYNAME = {1: "Wed 7 Oct", 2: "Thu 8 Oct", 3: "Fri 9 Oct", 4: "Sat 10 Oct",
           5: "Mon 12 Oct", 6: "Tue 13 Oct", 7: "Wed 14 Oct"}
r = 6
last_day = None
OWNER_FILL = {LEAD: "DEEBF7", PDEV: "E2EFDA", AI: "FFF2CC", J: "FCE4D6"}
for tid, day, task, owner, support, art, acc, gate, pd in T:
    if day != last_day:
        ws1b.merge_cells(start_row=r, start_column=1, end_row=r, end_column=10)
        dh = DAILY_HOURS.get(day, {})
        day_note = ""
        if day == 4:
            day_note = "   ·   WORKED BY TAKAWIRA ALONE"
        bc = ws1b.cell(row=r, column=1,
                       value=f"DAY {day} — {DAYNAME[day]}   ·   "
                             f"{sum(x[8] for x in T if x[1] == day):.2f} PD   ·   "
                             f"{round(sum(dh.values()), 1)} h across "
                             f"{len(dh)} {'person' if len(dh) == 1 else 'people'}{day_note}")
        bc.font = Font(bold=True, size=10, color="1F3864")
        bc.fill = bfill
        bc.alignment = Alignment(vertical="center")
        r += 1
        last_day = day
    vals = [tid, day, task, owner, support, art, acc, gate, pd, round(pd * PD_HOURS, 1)]
    for c, v in enumerate(vals, start=1):
        cell = ws1b.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap if c in (3, 6, 7) else ctr
        cell.border = box
        if c == 4:
            cell.fill = PatternFill("solid", fgColor=OWNER_FILL.get(owner, "FFFFFF"))
            cell.font = Font(size=9, bold=True)
        if c == 8 and v != "-":
            cell.font = Font(size=9, bold=True, color="375623")
        if c == 9:
            cell.number_format = "0.00"
        if c == 10:
            cell.number_format = "0.0"
    ws1b.row_dimensions[r].height = 40
    r += 1

ws1b.cell(row=r + 1, column=3, value="TOTAL").font = Font(bold=True, size=10)
tc = ws1b.cell(row=r + 1, column=4,
               value=f"{LEAD}: {sum(x[8] for x in T if x[3] == LEAD):.2f} PD / "
                     f"{sum(x[8] for x in T if x[3] == LEAD) * PD_HOURS:.1f} h   ·   "
                     f"{PDEV}: {sum(x[8] for x in T if x[3] == PDEV):.2f} PD / "
                     f"{sum(x[8] for x in T if x[3] == PDEV) * PD_HOURS:.1f} h   ·   "
                     f"{AI}: {sum(x[8] for x in T if x[3] == AI):.2f} PD (advisory)   ·   "
                     f"{J}: {sum(x[8] for x in T if x[3] == J):.2f} PD")
tc.font = Font(bold=True, size=9)
tc.alignment = Alignment(horizontal="left")
ws1b.cell(row=r + 1, column=9, value=REG_PD).font = Font(bold=True, size=10)
ws1b.cell(row=r + 1, column=9).number_format = "0.00"
ws1b.cell(row=r + 1, column=10, value=REG_H).font = Font(bold=True, size=10)
ws1b.cell(row=r + 1, column=10).number_format = "0.0"

for c, w in {1: 6, 2: 5, 3: 56, 4: 19, 5: 14, 6: 34, 7: 74, 8: 9, 9: 7, 10: 8}.items():
    ws1b.column_dimensions[get_column_letter(c)].width = w
ws1b.freeze_panes = "C6"

# ---------------- Sheet 1c: role split ----------------
ws1c = wb.create_sheet("Role Split", 2)
ws1c["A1"] = "ROLE ASSIGNMENT — why the split is drawn here"
ws1c["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws1c["A1"].fill = hfill
ws1c.merge_cells("A1:D1")

rows1c = [
    ("", f"{LEAD} ({LEAD_T})", f"{PDEV} ({PDEV_T})"),
    ("Total build effort", f"{t_pd:.2f} PD / {t_pd * PD_HOURS:.1f} h",
     f"{p_pd:.2f} PD / {p_pd * PD_HOURS:.1f} h"),
    ("Tasks owned", str(sum(1 for x in T if x[3] == LEAD)), str(sum(1 for x in T if x[3] == PDEV))),
    ("Share of capacity", f"{100 * t_pd / 7:.1f}% of 7.00 PD — {t_pd * PD_HOURS - 56.0:.1f} h OVER the 56 h available",
     f"{100 * p_pd / 7:.1f}% of 7.00 PD"),
    ("Accountable for", "The deterministic backend, and the prompt layer built on top of it",
     "The verifier and the containment proofs — the controls themselves"),
    ("", "", ""),
    ("Owns", "ai schema and DDL · Gate 1 RBAC · Gate 2 ReportScope · scope_hash · "
             "capability introspection and NEVER_READ denial · scope-first accessors · "
             "claim classes and ROLE_CLAIMS · disclosure classes · fact-pack builders · "
             "prompt builder and templates · model gateway · orchestration and fallback · "
             "REST router · response envelope · audit pair · adversarial suite · "
             "regression and diff",
     "T13 the S6 structural test · T23 the four-check verifier · T30 live S2/S3 "
     "containment and non-escalation. Three tasks, 1.50 PD, all of them checks "
     "against code somebody else wrote."),
    ("Unit of work", "A function that returns the same value twice",
     "A test that fails when someone else's code is wrong"),
    ("Why this split", "Almost every deliverable is plumbing, and 94.0 h is what the plumbing "
                       "actually costs inside 7 days. He carries the window.",
     "The verifier must not be written by the author of the prompt it polices. T14 and "
     "T16 are Takawira's; T23 is Peter's. Claim 1 holds because of that separation."),
    ("Reporting line", "Lead Developer, G2", "Second Developer, G2"),
    ("Relationship", "PEER. No task has both as owner.",
     "PEER. Peter reports to Jerry as PM, not into Takawira."),
    ("Gate they own", "GATE A · GATE B (prompt) · GATE C · GATE D (orchestration) · "
                      "GATE E (router, adversarial) · FREEZE (regression, diff)",
     "GATE B (S6, T13) · GATE D (verifier, T23) · GATE E (containment, T30)"),
    ("What they must not do", "Write or relax the verifier's patterns. T23 belongs to Peter; "
                              "a check may be changed only in the same commit that changes the "
                              "prompt it polices, never to make a generation succeed.",
     "Touch the prompt builder, the templates, or the scope and capability layer. Peter is "
     "here to check Takawira's work, not to extend it."),
    ("Assumed available", "100%, 7-14 October including Saturday 10 October (D8)",
     "100%, 7-14 October (D8). His three tasks fall on Fri 9, Mon 12 and Tue 13 — "
     "he is not required on the weekend."),
    ("Effort", f"{t_pd:.2f} PD over 7 build days = {t_pd / 7:.2f} PD/day "
               f"({t_pd * PD_HOURS:.1f} h, incl. {t_pd * PD_HOURS - 56.0:.1f} h overtime)",
     f"{p_pd:.2f} PD over 3 build days = {p_pd / 7:.2f} PD/day "
     f"({p_pd * PD_HOURS:.1f} h)"),
    ("Balance", "Deliberately unbalanced, and recorded as such: one developer runs at 168% of "
                "his calendar for seven days. The register still fits (106.0 h of build demand "
                "against 112.0 h of capacity) but the float is Peter's unused time, which cannot "
                "be lent to a 16.0 h gate day.",
     "Not spare capacity for someone else's problem. 78.6% of his 56 h was transferred to "
     "Takawira, which is why the transfer question was asked at all."),
    ("Peak day", "16.0 h on Day 2 (Thu 8, Gate A) and Day 4 (Sat 10, Gate C). Both are gate "
                 "days, and Saturday has no second pair of eyes — that is the schedule risk "
                 "this addendum is asking to be accepted (R18).",
     "8.0 h on Day 5 (Mon 12) — the verifier, the single most heavily tested module in the POC."),
]
ADVISORY_ROW = (
    "Advisory (not a build role)",
    f"{AI} ({AI_T}) holds no build tasks except T01 — the model pull and CPU latency "
    f"measurement, 0.50 PD / 4.0 h, charged at 0.5 h on each non-Saturday day so no single "
    f"day carries an artificial spike. He reviews at the gates, rehearses the AI controls "
    f"with Takawira, and his day-7 advisory explicitly covers the freeze diff review (T35) — "
    f"which is the independent check on a task whose owner wrote most of the code under review. "
    f"4.0 h of his time sits outside the build register.",
    "Consequence of his advisory status: T05, T15, T34 and T35 become self-checks by one "
    "person. Richard's review, Victoria's BA support on T19 and Jerry owning the evidence "
    "pack (T36) are what stand in their place.",
)
for c, h in enumerate(["Dimension", LEAD, PDEV], start=1):
    cell = ws1c.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2 if c == 1 else (hfill if c == 2 else PatternFill("solid", fgColor="375623"))
    cell.alignment = ctr
    cell.border = box
ws1c.row_dimensions[3].height = 30
r = 4
for row in list(rows1c) + [("", "", ""), ADVISORY_ROW]:
    if not any(row):
        r += 1
        continue
    for c, v in enumerate(row, start=1):
        cell = ws1c.cell(row=r, column=c, value=v)
        cell.font = Font(size=9, bold=(c == 1), italic=(row is ADVISORY_ROW))
        cell.alignment = wrap
        cell.border = box
        if row is ADVISORY_ROW and c == 2:
            cell.fill = PatternFill("solid", fgColor="FFF2CC")
    ws1c.row_dimensions[r].height = 62
    r += 1
ws1c.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1, end_column=3)
_ctl = ws1c.cell(row=r + 1, column=1, value=(
    "THE THREE CONTROL CLAIMS, AS THEY STAND IN THIS PLAN.  1. The verifier is not written by the "
    "prompt author — HOLDS: T23 (Peter) versus T14 and T16 (Takawira).  "
    "2. Ground truth is not authored by the model author — DOES NOT HOLD in the structural sense "
    "originally claimed, because Takawira owns the scope, capability, accessor and context layer AND "
    "the prompt builder. Restated: scope and capability DELEGATE to tenant_filter() and SQL "
    "introspection, neither of which can be widened from the prompt; the prompt builder only "
    "serialises facts the pack already contains (pack.serialise(allowed=claims)); and the containment "
    "proof is run live by T30, authored by Peter, not by the author of the prompt.  "
    "3. The structural filter cannot be bypassed by prompt text — HOLDS: pack.serialise() is a "
    "code boundary, not a rule in prose."))
_ctl.font = Font(size=9, italic=True, color="C00000")
_ctl.alignment = wrap
ws1c.row_dimensions[r + 1].height = 96
for c, w in {1: 22, 4: 4, 2: 84, 3: 84}.items():
    ws1c.column_dimensions[get_column_letter(c)].width = w

# ---- Sheet 2: effort & capacity ----
ws2 = wb.create_sheet("Effort & Capacity")
ws2.append(["Phase", "Name", "Start", "End", "Working days", "Effort (PD)", "Status", "unit"])
for c in range(1, 9):
    cell = ws2.cell(row=1, column=c)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box

blocks = {}
for a in A:
    blocks.setdefault(a["phase"], {"pd": 0.0, "s": a["start"], "e": a["end"],
                                   "status": "In scope"})
    blocks[a["phase"]]["pd"] += a["pd"]
    blocks[a["phase"]]["s"] = min(blocks[a["phase"]]["s"], a["start"])
    blocks[a["phase"]]["e"] = max(blocks[a["phase"]]["e"], a["end"])
    if a["status"] == "Deferred":
        blocks[a["phase"]]["status"] = "In scope (part deferred)"

r = 2
for name in [P12, P13, P14, P15, P16, P17, P18, P19]:
    b = blocks[name]
    wd = sum(1 for dd, _ in DAYS9 if b["s"] <= DATES[dd] <= b["e"])
    vals = [int(name.split(":")[0].replace("Phase ", "")), name.split(": ", 1)[1], b["s"].date(),
            b["e"].date(), wd, round(b["pd"], 2), b["status"]]
    for c, v in enumerate(vals, start=1):
        cell = ws2.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.border = box
        cell.alignment = ctr if c in (1, 5) else wrap
        if c in (3, 4):
            cell.number_format = "yyyy-mm-dd"
        if c == 6:
            cell.number_format = "0.00"
    r += 1

r += 1
for label, val, unit in [
    ("TOTAL effort in the 9-day window", total, "pd"),
    ("  of which coarse activity build allocation", dev_total, "pd"),
    (f"  of which granular engineering task effort ({len(T)} tasks)", REG_PD, "pd"),
    ("  of which governance / compliance / sponsor / PM / advisory", round(gov_total, 2), "pd"),
    ("Addendum A baseline", src_total, "pd"),
    ("Effort deferred out of the 9-day window", round(src_total - total, 1), "pd"),
    ("", "", ""),
    ("GRANULAR REGISTER (all 39 tasks, every owner)", REG_PD, "pd"),
    ("GRANULAR REGISTER in hours", REG_H, "h"),
    ("", "", ""),
    ("BUILD CAPACITY: 2 developers x 7 build days at 100%", BUILD_CAP_PD, "pd"),
    ("BUILD CAPACITY in hours", BUILD_CAP_H, "h"),
    (f"  {LEAD}: {t_pd:.2f} PD / {t_pd * PD_HOURS:.1f} h against 56.0 h available "
     f"= {100 * t_pd / 7:.1f}% — OVER BY {t_pd * PD_HOURS - 56.0:.1f} h", t_pd, "pd"),
    (f"  {PDEV}: {p_pd:.2f} PD / {p_pd * PD_HOURS:.1f} h against 56.0 h available "
     f"= {100 * p_pd / 7:.1f}%", p_pd, "pd"),
    (f"  {AI} (advisory): {sum(x[8] for x in T if x[3] == AI):.2f} PD / "
     f"{sum(x[8] for x in T if x[3] == AI) * PD_HOURS:.1f} h in-register (T01), plus "
     f"4.0 h of gate, freeze and demo review outside the register",
     sum(x[8] for x in T if x[3] == AI), "pd"),
    (f"  {J}: {sum(x[8] for x in T if x[3] == J):.2f} PD / "
     f"{sum(x[8] for x in T if x[3] == J) * PD_HOURS:.1f} h (T36 evidence pack)",
     sum(x[8] for x in T if x[3] == J), "pd"),
    ("", "", ""),
    ("BUILD DEMAND (register, builders only)", build_pd, "pd"),
    ("BUILD DEMAND in hours", round(build_h, 1), "h"),
    ("SURPLUS / (SHORTFALL) on build demand vs capacity", round(BUILD_CAP_PD - build_pd, 2), "pd"),
    ("  the same figure in hours — the real float", round(BUILD_CAP_H - build_h, 1), "h"),
    ("", "", ""),
    ("DAILY LOADING ACROSS THE WHOLE WINDOW (all resources, hours)", "", ""),
    ("  Wed 7 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[1].items()),
     round(sum(DAILY_HOURS[1].values()), 1), "h"),
    ("  Thu 8 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[2].items()),
     round(sum(DAILY_HOURS[2].values()), 1), "h"),
    ("  Fri 9 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[3].items()),
     round(sum(DAILY_HOURS[3].values()), 1), "h"),
    ("  Sat 10 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[4].items())
     + "   [WORKED BY TAKAWIRA ALONE]", round(sum(DAILY_HOURS[4].values()), 1), "h"),
    ("  Mon 12 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[5].items()),
     round(sum(DAILY_HOURS[5].values()), 1), "h"),
    ("  Tue 13 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[6].items()),
     round(sum(DAILY_HOURS[6].values()), 1), "h"),
    ("  Wed 14 Oct — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[7].items()),
     round(sum(DAILY_HOURS[7].values()), 1), "h"),
    ("  Thu 15 Oct (demonstration) — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[8].items()),
     round(sum(DAILY_HOURS[8].values()), 1), "h"),
    ("  Fri 16 Oct (close-out) — " + " · ".join(f"{k.split()[0]} {v}" for k, v in DAILY_HOURS[9].items()),
     round(sum(DAILY_HOURS[9].values()), 1), "h"),
    ("GRAND TOTAL across the window, every resource", GRAND_HOURS, "h"),
    ("", "", ""),
    ("Support, outside the build register: Victoria 6.0 h of BA prompt/eval work "
     "(all of it on Fri 9 Oct, ahead of T19)", 6.0, "h"),
    ("Support, outside the build register: Richard 4.0 h of gate, freeze and demo review", 4.0, "h"),
]:
    ws2.cell(row=r, column=1, value=label).font = Font(bold=True, size=9)
    ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    c = ws2.cell(row=r, column=6, value=val)
    c.font = Font(bold=True, size=9)
    c.number_format = "0.0" if unit == "h" else "0.00"
    c.alignment = ctr
    ws2.cell(row=r, column=7, value=unit).border = box
    r += 1

for c, w in {1: 66, 2: 54, 3: 12, 4: 12, 5: 12, 6: 12, 7: 8, 8: 8}.items():
    ws2.column_dimensions[get_column_letter(c)].width = w

# ---- Sheet 3: the 9 days ----
ws3 = wb.create_sheet("The 9 Days")
ws3["A1"] = "The 9 days, gate by gate"
ws3["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws3["A1"].fill = hfill
ws3.merge_cells("A1:G1")
ws3["A2"] = (f"{LEAD} ({LEAD_T}) owns the deterministic backend and the prompt layer · "
             f"{PDEV} ({PDEV_T}) owns the verifier and the containment proofs. "
             f"{AI} ({AI_T}) is ADVISORY in this window: he holds T01 only, reviews at the gates "
             f"and covers the freeze diff. Task IDs are granular - see the "
             f"'Task Breakdown (Granular)' sheet for artefacts and acceptance tests.")
ws3["A2"].font = Font(italic=True, size=9)
ws3["A2"].alignment = wrap
ws3.merge_cells("A2:G2")
ws3.row_dimensions[2].height = 30


def _dl(d, who):
    items = " · ".join(f"{x[0]} {x[2].split('(')[0].strip().rstrip('.')}"
                       for x in T if x[1] == d and x[3] == who)
    return f"{who}: {items}" if items else f"{who}: —"


def _dl_extra(d, who, other, extra):
    base = _dl(d, who)
    if who != other and extra:
        return f"{base} · {other}: {extra}"
    return base


T01_SLICE = "0.5 h of the T01 latency measurement"
DAYS = [
    (1, "Wed 7 Oct",
     _dl_extra(1, LEAD, PDEV, T01_SLICE), _dl(1, PDEV),
     "-",
     "Model serves and its latency is measured; ai.report exists in the live database; "
     "unknown role returns 403; 14 roles enumerated"),
    (2, "Thu 8 Oct",
     _dl_extra(2, LEAD, PDEV, T01_SLICE), _dl(2, PDEV),
     "GATE A",
     "Unknown role 403 · empty scope expression.false() · unknown province slug raises LOUDLY · "
     "NEVER_READ raises at import · claim patterns non-empty · exec holds no cve_ids/alert_ids/owner_names/rule_ids"),
    (3, "Fri 9 Oct",
     _dl_extra(3, LEAD, PDEV, T01_SLICE), _dl(3, PDEV),
     "GATE B",
     "S6 green - every accessor takes scope first (T13, written by Peter against Takawira's T12) · "
     "capability() classifies every registered table · "
     "two roles produce different allowed_claim_classes and different facts"),
    (4, "Sat 10 Oct",
     _dl(4, LEAD), _dl(4, PDEV),
     "GATE C - CUT TRIGGER",
     "First generation from a real fact pack · 6 eval fixtures with distinct scope_hash · "
     "no fixture figure exceeds its own pack max. WORKED BY TAKAWIRA ALONE — no peer "
     "review available on this gate day (R18)"),
    (5, "Mon 12 Oct",
     _dl(5, LEAD), _dl(5, PDEV),
     "GATE D",
     "Verifier discards an ungrounded numeral AND an unheld claim class · fallback renders from the "
     "identical filtered fact view · any failure returns the template, never model text. "
     "The verifier is Peter's; the prompt that feeds it is Takawira's"),
    (6, "Tue 13 Oct",
     _dl(6, LEAD), _dl(6, PDEV),
     "GATE E",
     "DHA soc 745 rows vs exec 2244, different scope_hash (T30, Peter) · provincial widening yields "
     "expression.false() → 0 · scope-widening, province-naming and CVE-injection all rejected "
     "AT THE VERIFIER"),
    (7, "Wed 14 Oct",
     _dl_extra(7, LEAD, PDEV, T01_SLICE), _dl(7, PDEV),
     "FREEZE 17:00",
     "ruff clean · full pytest green with no existing test regressed · diff is additions only "
     "and independently reviewed by Richard · tripwire passes · integration smoke test green · "
     "evidence pack assembled by Jerry (T36) · run sheet rehearsed and timed"),
    (8, "Thu 15 Oct", "-", "-", "",
     "CLIENT DEMONSTRATION - 23-minute run sheet. Richard supports (1.5 h advisory)"),
    (9, "Fri 16 Oct", "Defect triage; evidence pack finalised", "-", "",
     "POC acceptance checklist signed · Phase 2 re-estimate requested · 29 Jan 2027 withdrawn · "
     "T01 latency table closed by Richard (0.5 h)"),
]
hdr3 = ["Day", "Date", f"{LEAD}\n{LEAD_T}", f"{PDEV}\n{PDEV_T}", "Gate", "Pass criteria"]
for c, h in enumerate(hdr3, start=1):
    cell = ws3.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
r = 4
for d in DAYS:
    for c, v in enumerate(d, start=1):
        cell = ws3.cell(row=r, column=c, value=v)
        cell.font = Font(size=9, bold=(c == 5 and v not in ("", "-")))
        cell.alignment = wrap
        cell.border = box
        if c == 1:
            cell.alignment = ctr
        if d[4] and v == d[4] and c == 5:
            cell.fill = PatternFill("solid", fgColor="C6E0B4")
            cell.font = Font(size=9, bold=True, color="375623")
    if d[1] == "Thu 15 Oct":
        for c in range(1, 7):
            ws3.cell(row=r, column=c).fill = PatternFill("solid", fgColor="FFE699")
            ws3.cell(row=r, column=c).font = Font(size=9, bold=True)
    r += 1
for c, w in {1: 6, 2: 12, 3: 11, 4: 58, 5: 20, 6: 66}.items():
    ws3.column_dimensions[get_column_letter(c)].width = w
for i in range(4, r):
    ws3.row_dimensions[i].height = 46

# ---- Sheet 4: demo run sheet ----
ws4 = wb.create_sheet("Demo Run Sheet 15 Oct")
ws4["A1"] = "Demonstration run sheet - Thursday 15 October 2026"
ws4["A1"].font = Font(bold=True, size=13, color="FFFFFF")
ws4["A1"].fill = hfill
ws4.merge_cells("A1:D1")
ws4["A2"] = "23 minutes. Every item runs against the live database - no mocks, no synthetic data."
ws4["A2"].font = Font(italic=True, size=9)
ws4.merge_cells("A2:D2")
for c, h in enumerate(["Min", "Demonstration", "What it proves", "Live data"], start=1):
    cell = ws4.cell(row=4, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
RUN = [
    ("0-3", "exec -> executive_briefing. Model-generated narrative over the live estate",
     "The agent works, on real data", "15 283 risk rows, 2 244 findings"),
    ("3-5", "Response envelope: authorisation, disclosure, provenance, verification",
     "Authorisation is part of the contract, not metadata", "scope_hash shown"),
    ("5-8", "exec -> compliance_status. disclosure shows estate_wide 456 and derived_estate_wide",
     "The design surfaces its own limits instead of hiding them",
     "456 snapshots + 228 gaps, unscopable"),
    ("8-10", "exec -> soc_shift_handover -> 403",
     "Gate 1 default-deny", "No rows returned"),
    ("10-14", "Role-aware prompting, live: same report type, exec vs soc, side by side",
     "Different claim classes produce materially different text",
     "exec holds no cve_ids; soc does"),
    ("14-17", "DHA soc vs exec: 745 vs 2 244 rows, different scope_hash",
     "Tenancy containment (S2)", "home-affairs-digital"),
    ("17-19", "Provincial persona attempts to widen scope -> fails closed to empty",
     "Non-escalation (S3). Never estate-wide", "expression.false() -> 0"),
    ("19-21", "Claim filter catches an injected CVE id -> sentence discarded",
     "The verifier, not the prompt, is the control", "Regex discard"),
    ("21-23", "git diff main --stat. One added line in app/main.py, additions only",
     "Non-interference, stated precisely", "Briefed in advance (R22)"),
]
r = 5
for row in RUN:
    for c, v in enumerate(row, start=1):
        cell = ws4.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap if c > 1 else ctr
        cell.border = box
    r += 1
r += 1
ws4.cell(row=r, column=1, value="NOT DEMONSTRATED IN THE POC").font = Font(bold=True, size=10, color="C00000")
ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
r += 1
for txt in [
    "Cache isolation (S5) - no cache is built in the 9-day window. The cache-keying test that "
    "was drafted against it is not in this register, because there is nothing to collide.",
    "Independent RBAC/tenancy security review - no reviewer could be sourced and briefed in 9 days",
    "k6 load test and model-failure chaos test - nothing is deployed to test against",
    "UAT - the 15 October session is a demonstration, not user acceptance testing",
    "Production deployment - local/staging only",
    "5 of the 7 report types - the catalogue is 8, the POC ships 2",
]:
    ws4.cell(row=r, column=1, value="- " + txt).font = Font(size=9, color="808080")
    ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    r += 1
for c, w in {1: 9, 2: 62, 3: 46, 4: 34}.items():
    ws4.column_dimensions[get_column_letter(c)].width = w
for i in range(5, 14):
    ws4.row_dimensions[i].height = 32

# ---- Sheet 5: assumptions ----
ws5 = wb.create_sheet("Assumptions")
ws5["A1"] = "Assumptions & standing defaults"
ws5["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws5["A1"].fill = hfill
ws5.merge_cells("A1:C1")
for c, h in enumerate(["#", "Assumption", "Consequence if false"], start=1):
    cell = ws5.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
ASSUM = [
    (f"{LEAD} ({LEAD_T}) is available at 100% for 7-14 October INCLUDING SATURDAY 10 OCTOBER, and "
     f"carries 11.75 PD / 94.0 h - 168% of his 56 h, i.e. 38.0 h of overtime",
     "The build does not fit inside the window. The Gate C cut trigger is the pre-agreed release "
     "valve; it is decided Saturday 10 Oct, on the day Takawira works alone."),
    ("Saturday 10 October is a working day worked by Takawira Mazando ALONE. Peter, Victoria and "
     "Richard are all off. Peter's three tasks fall on Fri 9, Mon 12 and Tue 13",
     "Gate C falls on a single-person day with no peer review available. Richard's advisory review "
     "moves to Monday 12 Oct; the containment proofs land Tuesday 13 Oct and act as the real check."),
    (f"{PDEV} ({PDEV_T}) IS available for 7-14 October and returns to this window, taking the three "
     f"verification tasks T13, T23 and T30 - 1.50 PD / 12.0 h. His three are Friday, Monday, Tuesday; "
     f"he is not required on the weekend",
     "Addendum A's 61 PD assignment to him stands as re-baselined here, not as deleted. If he cannot "
     "return, the verifier has no independent author and claim 1 fails."),
    (f"{AI} ({AI_T}) is ADVISORY for this window: T01 only (0.50 PD / 4.0 h, charged 0.5 h on each "
     f"non-Saturday day), plus 4.0 h of gate, freeze and demonstration review outside the build register",
     "T05, T15, T34 and T35 become self-checks by one person. Richard's freeze-diff review, "
     "Victoria's BA support on T19 and Jerry's evidence pack (T36) are the mitigations."),
    ("The two BUILDERS are peers. No task is co-owned, and neither may take the other's work. "
     "The verifier (T23) is Peter's; the prompt builder and templates it polices (T14, T16) are Takawira's",
     "Co-ownership, or one person writing both sides of a control, would defeat the purpose of "
     "having two developers at all."),
    ("Ollama 0.35.1 remains running; qwen2.5:3b pulls successfully",
     "Fallback-only demo with identical numbers. Pre-agreed degradation, not a failure."),
    ("Local PostgreSQL 18.1 (sita) is available; no VPN to 192.168.101.0/24 is needed",
     "R12 becomes blocking. The demo moves to wherever the database is reachable."),
    ("No SA public holiday falls between 7 and 16 October 2026",
     "One build day lost from a window with 6.0 h of float."),
    ("The delivery team contains ZERO SITA employees; SITA is the client/customer",
     "Delivery is executed 100% by vendor team (Takawira, Peter, Richard, Jerry, Victoria, Kagiso). "
     "No dependency on SITA personnel availability during the 7-14 Oct build."),
    ("The demonstration runs against local/staging vendor environment, not SITA infrastructure",
     "Solution is packaged and shipped to SITA environment in Phase 2 only after PoC demonstration and formal acceptance by SITA on 15 Oct 2026."),
    ("Docker remains unavailable; native PostgreSQL is used",
     "No impact - nothing is containerised for the POC."),
    ("STANDING RULE: a decision not amended on 15 October is adopted as documented",
     "None. This is the mechanism that makes a 9-day window possible at all."),
    ("Decisions default: ai schema in main DB; disclose ESTATE_WIDE; narrative separate from the attestation; ROLE_CLAIMS as drafted; ai.report retention matches action_audit; Ollama self-hosting",
     "Each default is documented and defensible, so a missed deadline is not a blocker."),
    ("Non-interference is restated: one added line in app/main.py, additions only",
     "If the original 'nothing existing modified' claim is presented, it fails on a projector (R22)."),
    ("The master flight plan (Phases 1-12) is unchanged and stays at 99/100 complete. "
     "Phase 13 is ADDED, not a replacement of any existing phase",
     "If Phase 13 were intended to alter Phases 1-12, the master plan needs re-baselining first."),
    ("The existing backend pipeline is integrated, not bypassed: Phase 13 reads warehouse.* "
     "(Phase 7) through tenant_filter() (Phase 9) and returns JSON to the existing Phase 10 dashboards",
     "A parallel AI stack reading the database directly would reintroduce unscoped reads - the "
     "exact defect tenant_filter's opt-in design invites."),
]
r = 4
for a in ASSUM:
    ws5.cell(row=r, column=1, value=r - 3).alignment = ctr
    for c, v in enumerate(a, start=2):
        ws5.cell(row=r, column=c, value=v).alignment = wrap
    for c in range(1, 4):
        ws5.cell(row=r, column=c).border = box
        ws5.cell(row=r, column=c).font = Font(size=9)
    ws5.row_dimensions[r].height = 40
    r += 1
for c, w in {1: 5, 2: 78, 3: 62}.items():
    ws5.column_dimensions[get_column_letter(c)].width = w

# ---- Sheet 6: risk register ----
ws6 = wb.create_sheet("Risk Register")
ws6["A1"] = "Risk register - 9-day window. Score = Likelihood x Impact. Critical >= 15, High >= 10, Medium >= 5."
ws6["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws6["A1"].fill = hfill
ws6.merge_cells("A1:J1")
for c, h in enumerate(["ID", "Risk", "L", "I", "Score", "Rating", "Mitigation", "Owner", "Phase", "Status"], start=1):
    cell = ws6.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
RISKS = [
    ("R18", "One developer runs the window at 168%. Takawira carries 94.0 h against 56 h - 38.0 h of "
            "overtime - with 16.0 h peaks on BOTH gate days (Thu 8 and Sat 10), and Sat 10 has no peer review", 5, 5, 25, "Critical",
     "Recorded and accepted rather than hidden: Peter owns the verifier and the containment proofs so "
     "the heaviest load is the deterministic backend; the pre-agreed cut trigger at GATE C on Saturday "
     "10 Oct drops the compliance_status report type, decided on the day, not discovered on Wed 14; "
     "Richard's freeze-diff review and Jerry's evidence pack are outside Takawira's hands.",
     "Kagiso, Jerry", "All", "Open - accepted"),
    ("R09", "Verification is concentrated in one person at 21% utilisation while the other runs at 168%. "
            "T05, T15, T34 and T35 are self-checks by the same author as the code they check", 5, 4, 20, "Critical",
     "T13, T23 and T30 are Peter's, against code Takawira wrote - three independent checks, not one. "
     "Richard's 0.5 h day-7 advisory explicitly covers the T35 diff review. Victoria's 6.0 h of BA "
     "support lands on Fri 9, and Jerry owns the evidence pack (T36), so the certification is written "
     "by someone who did not build the code.", "Jerry", "All", "Open"),
    ("R23", "identity.users and audit.action_audit become agent-readable if the capability gate is rushed", 3, 5, 15, "Critical",
     "T09 acceptance: NEVER_READ raises at import; a test asserts no accessor references either model", "Takawira", "13-14", "Open"),
    ("R02", "Compliance data is structurally unscopable - 684 rows, no tenancy columns", 5, 3, 15, "Critical",
     "Typed three-class disclosure enforced by the verifier. Tenancy columns are a separate approved change (D2)", "Compliance", "14", "Accepted by design"),
    ("R22", "Non-interference is not literally provable; one include_router line is unavoidable", 4, 3, 12, "High",
     "Restate the claim per ADR D-A8 and brief the client BEFORE 15 Oct", "Jerry", "18", "Open"),
    ("R05", "Narrative discloses identifiers the role may not see (CVE, alert, owner)", 3, 4, 12, "High",
     "Post-generation claim filter with sentence discard; S4 suite; facts filtered to the claim set "
     "before the prompt", "Peter", "16", "Open"),
    ("R04", "Model states a figure that is not in the fact pack", 3, 4, 12, "High",
     "Numeral-fidelity check; discard and return the deterministic template", "Peter", "16", "Open"),
    ("R08", "Prompt injection via free-text warehouse fields", 3, 4, 12, "High",
     "Constrained decode; verifier independent of the prompt; adversarial suite on day 6", "Peter", "16", "Open"),
    ("R20", "Model not pulled - the download is on the critical path", 3, 3, 9, "Medium",
     "Pull day 1. The fallback serves identical numbers. Pre-agreed degradation.", "Richard", "15", "Open"),
    ("R21", "CPU-only inference latency under demo conditions", 4, 2, 8, "Medium",
     "Token cap decided DAY 1 on measured latency; T01's 0.5 h daily slices let the measurement be "
     "revisited as the token budget settles; rehearse end-to-end on day 7", "Richard", "15", "Open"),
    ("R03", "A warehouse reader is written without scope, leaking estate-wide rows", 2, 5, 10, "High",
     "Scope is the first positional argument; the S6 signature test fails the build", "Takawira", "14", "Open"),
    ("R-AI-11", "Silent estate-wide compliance data presented as department-scoped", 4, 5, 20, "Critical",
     "Typed three-class disclosure; attribution check in the verifier; Gate 1 default-deny", "Compliance", "14", "Open"),
    ("R17", "Stakeholder availability for decisions and the demonstration", 3, 3, 9, "Medium",
     "Named owners and dates; defaults pre-agreed so a missed deadline is not a blocker", "Jerry", "12", "Open"),
    ("R25", "Bucket-definition divergence goes live (30 < fused_score < 45)", 2, 3, 6, "Medium",
     "Tripwire test makes it detected. Consolidation is Phase 0 work, not G2.", "Takawira", "19", "Open"),
    ("R12", "VPN access to 192.168.101.0/24 blocks deployment", 1, 3, 3, "Low",
     "Not needed - the demo runs against the local sita instance", "Takawira", "13", "Closed by scope"),
]
r = 4
for rk in RISKS:
    for c, v in enumerate(rk, start=1):
        cell = ws6.cell(row=r, column=c, value=v)
        cell.font = Font(size=9)
        cell.alignment = wrap if c in (2, 7) else ctr
        cell.border = box
        if c == 6:
            color = {"Critical": "FFC7CE", "High": "FFE699", "Medium": "DDEBF7", "Low": "E2EFDA"}.get(v)
            if color:
                cell.fill = PatternFill("solid", fgColor=color)
                cell.font = Font(size=9, bold=True)
    ws6.row_dimensions[r].height = 40
    r += 1
for c, w in {1: 9, 2: 62, 3: 5, 4: 5, 5: 7, 6: 11, 7: 72, 8: 14, 9: 9, 10: 20}.items():
    ws6.column_dimensions[get_column_letter(c)].width = w
ws6.freeze_panes = "A4"

# ---- Sheet 7: Gantt ----
ws7 = wb.create_sheet("Gantt")
ws7["A1"] = "Daily Gantt - 9 working days, 7 to 16 October 2026 (Saturday 10 Oct is a working day)"
ws7["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws7["A1"].fill = hfill
ws7.merge_cells("A1:N1")
for c, h in enumerate(["Ref", "Activity", "Owner"] + [d[1] for d in DAYS9], start=1):
    cell = ws7.cell(row=3, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=8)
    cell.fill = PatternFill("solid", fgColor="C00000") if "DEMO" in h else hfill2
    cell.alignment = ctr
    cell.border = box
ws7.row_dimensions[3].height = 30

DATES = {1: D(7), 2: D(8), 3: D(9), 4: D(10), 5: D(12), 6: D(13), 7: D(14), 8: D(15), 9: D(16)}
r = 4
last_block = None
for a in A:
    if a["block"] != last_block:
        ws7.merge_cells(start_row=r, start_column=1, end_row=r, end_column=12)
        bc = ws7.cell(row=r, column=1, value=a["block"].split("(")[0].strip())
        bc.font = Font(bold=True, size=9, color="1F3864")
        bc.fill = bfill
        r += 1
        last_block = a["block"]
    ws7.cell(row=r, column=1, value=a["ref"]).font = Font(size=8)
    ws7.cell(row=r, column=2, value=a["activity"]).font = Font(size=8)
    ws7.cell(row=r, column=3, value=a["primary"]).font = Font(size=8)
    for c in (1, 2, 3):
        ws7.cell(row=r, column=c).alignment = wrap
        ws7.cell(row=r, column=c).border = box
    for dnum, _ in DAYS9:
        col = 3 + dnum
        on = a["start"] <= DATES[dnum] <= a["end"]
        cell = ws7.cell(row=r, column=col, value="█" if on else "")
        cell.alignment = ctr
        cell.border = box
        if on:
            if a["status"] == "Deferred":
                cell.fill = PatternFill("solid", fgColor="D9D9D9")
                cell.font = Font(size=8, color="A6A6A6")
            elif a["status"] == "Dropped":
                cell.fill = PatternFill("solid", fgColor="FFC7CE")
                cell.font = Font(size=8, color="C00000")
            elif a["ref"] in ("15.1", "15.7"):
                cell.fill = PatternFill("solid", fgColor="FFE699")
                cell.font = Font(size=8)
            else:
                cell.fill = PatternFill("solid", fgColor="8FAADC")
                cell.font = Font(size=8, color="FFFFFF")
    ws7.row_dimensions[r].height = 24
    r += 1
for c, w in {1: 7, 2: 56, 3: 16}.items():
    ws7.column_dimensions[get_column_letter(c)].width = w
for dnum, _ in DAYS9:
    ws7.column_dimensions[get_column_letter(3 + dnum)].width = 8
ws7.freeze_panes = "D4"

# ---- Sheet 8: decisions ----
ws8 = wb.create_sheet("Decisions & Milestones")
ws8["A1"] = "Open decisions tabled at the demonstration, and milestones"
ws8["A1"].font = Font(bold=True, size=12, color="FFFFFF")
ws8["A1"].fill = hfill
ws8.merge_cells("A1:E1")
ws8["A2"] = "STANDING RULE: a decision not amended on 15 October is adopted as documented."
ws8["A2"].font = Font(italic=True, bold=True, size=10, color="C00000")
ws8.merge_cells("A2:E2")
for c, h in enumerate(["#", "Decision", "Owner", "Default if not amended", "Status"], start=1):
    cell = ws8.cell(row=4, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
DEC = [
    (1, "Approve the ai schema in the main DB, or a separate reporting DB", "Data Architect, DevOps",
     "DEFAULT: schema 'ai' in the main database. A separate DB costs 4-6 PD of provisioning, none of it in this window.", "Default ready"),
    (2, "Is estate-wide compliance disclosure acceptable, or must compliance reports wait for tenancy columns?",
     "Compliance Analyst", "DEFAULT: disclose as estate-wide. 684 rows proven unscopable live.", "Default ready"),
    (3, "Does the AG require an AI narrative inside the attestation?", "AG liaison",
     "DEFAULT: keep separate. The attestation is ECDSA-signed and pure; nondeterministic text would make the signature attest to unverified text.", "Default ready"),
    (4, "Is DEPARTMENT_NAMES a safe claim class for exec estate-wide?", "Compliance Analyst, AG liaison",
     "DEFAULT: ROLE_CLAIMS signed exactly as drafted. Any widening needs approval BEFORE implementation.", "Default ready"),
    (5, "Audit retention for ai.report", "Compliance Analyst",
     "DEFAULT: same as audit.action_audit. Retention is not immutability - the two must not be conflated.", "Default ready"),
    (6, "GPU CAPEX, sovereign cloud, or existing hardware?", "Kagiso, Jerry",
     "ANSWERED BY EVIDENCE: self-hosted Ollama on existing hardware. Zero CAPEX, zero procurement lead time.", "CLOSED"),
    (7, "Team allocation for 7-14 October, including Saturday 10 October", "Kagiso",
     "DEFAULT: proceed as planned and as recorded here — Takawira 11.75 PD / 94.0 h incl. 38.0 h "
     "overtime, Peter 1.50 PD / 12.0 h, Richard advisory 0.50 PD + 4.0 h review, Victoria 6.0 h of BA "
     "support on Fri 9 Oct, Jerry 0.50 PD for the evidence pack. This asks Kagiso to accept the "
     "overtime and the single-person Saturday, not to re-allocate them.", "OPEN - needed today"),
    (8, "Peter Rashaya returns for 7-14 October, taking T13, T23 and T30", "Jerry",
     "CONFIRMED. Peter takes the three verification tasks — 1.50 PD / 12.0 h, on Fri 9, Mon 12 and "
     "Tue 13. Addendum A's 61 PD assignment to him is re-baselined, not deleted: the verifier having "
     "an author other than the prompt author is control claim 1.", "CLOSED - confirmed"),
    (9, "Phase 2: authorise a date, or a re-estimate?", "Kagiso, Jerry",
     "DEFAULT: authorise a re-estimate. 29 Jan 2027 is withdrawn - it came from an estimate that assumed GPU hosting.", "For 15 Oct"),
    (10, "AI tooling for the proof of concept", "Richard, Kagiso",
     "DEFAULT: private, local Ollama on the existing host, pulled on day 1 under T01. No external "
     "provider, no API key, no data leaves the environment. Sovereign cloud and any SaaS API remain "
     "available as disaster recovery only, behind the same redaction gate. Consequences if overturned: "
     "mandatory redaction, a gateway-to-provider abstraction, POPIA DPA review, and R21 retires.",
     "Default ready"),
]
r = 5
for d in DEC:
    for c, v in enumerate(d, start=1):
        cell = ws8.cell(row=r, column=c, value=v)
        cell.font = Font(size=9, bold=(c == 1))
        cell.alignment = wrap if c in (2, 4) else ctr
        cell.border = box
        if c == 5 and v.startswith("OPEN"):
            cell.fill = PatternFill("solid", fgColor="FFC7CE")
        elif c == 5 and v == "CLOSED":
            cell.fill = PatternFill("solid", fgColor="C6E0B4")
    ws8.row_dimensions[r].height = 42
    r += 1

r += 2
ws8.cell(row=r, column=1, value="MILESTONES").font = Font(bold=True, size=11, color="1F3864")
r += 1
for c, h in enumerate(["ID", "Milestone", "Date", "Proves"], start=1):
    cell = ws8.cell(row=r, column=c, value=h)
    cell.font = Font(bold=True, color="FFFFFF", size=9)
    cell.fill = hfill2
    cell.alignment = ctr
    cell.border = box
MS = [
    ("M0", "Model pulled, ai schema applied, Gate 1 coded", D(7), "The runtime exists and Day 1 is not blocked by a download"),
    ("M1", "Gate A - RBAC and tenancy gates hold", D(8), "403 on unknown role; fail-closed on empty scope"),
    ("M2", "Gate B - scope is structurally mandatory (T13 written by Peter)", D(9), "S6 green; 2 roles produce different claim sets"),
    ("M3", "Gate C - first generation from a real fact pack. CUT TRIGGER. Saturday, Takawira solo", D(10), "The agent generates from live, scoped data"),
    ("M4", "Gate D - the verifier (T23, Peter) discards ungrounded output", D(12), "The control is the verifier, not the prompt"),
    ("M5", "Gate E - adversarial attempts all rejected", D(13), "Tenancy containment holds under attack"),
    ("M6", "FREEZE - POC frozen and evidence signed", D(14), "17:00. No defect carried into the meeting."),
    ("M7", "CLIENT DEMONSTRATION", D(15), "The whole POC, live"),
    ("M8", "Acceptance signed; Phase 2 re-estimate requested", D(16), "29 Jan 2027 withdrawn; T01 latency table closed"),
]
r += 1
for m in MS:
    for c, v in enumerate(m, start=1):
        cell = ws8.cell(row=r, column=c, value=v)
        cell.font = Font(size=9, bold=(c == 1))
        cell.alignment = ctr if c != 2 else wrap
        cell.border = box
        if c == 3:
            cell.number_format = "yyyy-mm-dd"
        if m[0] == "M7":
            cell.fill = PatternFill("solid", fgColor="FFE699")
    ws8.row_dimensions[r].height = 26
    r += 1
for c, w in {1: 6, 2: 62, 3: 22, 4: 62, 5: 22}.items():
    ws8.column_dimensions[get_column_letter(c)].width = w

wb.save(OUT)

# ---------------------------------------------------------------- report
print(f"WROTE {OUT}")
print(f"activities: {len(A)}")
print(f"in scope  : {sum(1 for a in A if a['status'] not in ('Deferred', 'Dropped'))}")
print(f"deferred  : {sum(1 for a in A if a['status'] == 'Deferred')}")
print(f"dropped   : {sum(1 for a in A if a['status'] == 'Dropped')}")
print(f"effort    : {total} PD   (Addendum A {src_total}, deferred {round(src_total - total,1)})")
print(f"register  : {len(T)} tasks / {REG_PD:.2f} PD / {REG_H:.1f} h")
print(f"owners    : {LEAD} {t_pd:.2f} PD ({sum(1 for x in T if x[3]==LEAD)} tasks) · "
      f"{PDEV} {p_pd:.2f} PD ({sum(1 for x in T if x[3]==PDEV)}) · "
      f"{AI} {sum(x[8] for x in T if x[3]==AI):.2f} PD (advisory) · "
      f"{J} {sum(x[8] for x in T if x[3]==J):.2f} PD")
print(f"build     : {build_pd:.2f} PD / {build_h:.1f} h vs {BUILD_CAP_PD:.2f} PD / {BUILD_CAP_H:.1f} h "
      f"-> float {BUILD_CAP_PD - build_pd:+.2f} PD / {BUILD_CAP_H - build_h:+.1f} h")
print(f"overtime  : {LEAD} {t_pd * PD_HOURS - 56.0:+.1f} h against 56.0 h")
print(f"daily h   : " + ", ".join(f"d{d}={round(sum(v.values()),1)}" for d, v in DAILY_HOURS.items()))
print(f"grand     : {GRAND_HOURS:.1f} h across all resources, 7-16 October")
print(f"coverage  : {round(100*total/src_total,1)}% of Addendum A effort delivered in 9 days")

# ------------------------------------------------------------------ assertions
# The workbook is the deliverable, so the generator fails loudly rather than
# writing a workbook whose numbers have drifted from the plan.
EXPECTED_REG_PD = 14.25
EXPECTED_REG_H = 114.0
EXPECTED_OWNERS = {LEAD: 34, PDEV: 3, AI: 1, J: 1}
EXPECTED_DAILY = [12.5, 17.0, 23.0, 16.0, 17.5, 17.0, 19.0, 1.5, 0.5]
EXPECTED_GRAND = 124.0
errs = []
if len(T) != 39:
    errs.append(f"task count {len(T)} != 39")
if abs(REG_PD - EXPECTED_REG_PD) > 1e-9:
    errs.append(f"register {REG_PD} PD != {EXPECTED_REG_PD}")
if abs(REG_H - EXPECTED_REG_H) > 1e-9:
    errs.append(f"register {REG_H} h != {EXPECTED_REG_H}")
for who, n in EXPECTED_OWNERS.items():
    got = sum(1 for x in T if x[3] == who)
    if got != n:
        errs.append(f"{who} owns {got} tasks, expected {n}")
got_daily = [round(sum(v.values()), 1) for v in DAILY_HOURS.values()]
if got_daily != EXPECTED_DAILY:
    errs.append(f"daily hours {got_daily} != {EXPECTED_DAILY}")
if abs(GRAND_HOURS - EXPECTED_GRAND) > 1e-9:
    errs.append(f"grand {GRAND_HOURS} h != {EXPECTED_GRAND} h")
if any(x[3] == AI and x[0] != "T01" for x in T):
    errs.append("Richard owns a task other than T01 - he is advisory in this window")
if any(x[3] == PDEV and x[1] == 4 for x in T):
    errs.append("Peter owns a task on Saturday 10 Oct - he is not scheduled that day")
if DAILY_HOURS[4] != {LEAD: 16.0}:
    errs.append(f"Saturday must be Takawira alone, got {DAILY_HOURS[4]}")
if any(str(a["start"]).startswith("2026-10-06") or a["start"] == D(6) for a in A):
    errs.append("an activity still starts on 6 Oct - build starts 7 Oct")
if abs(build_h - 106.0) > 1e-9:
    errs.append(f"build demand {build_h} h != 106.0 h")
if errs:
    raise SystemExit("GENERATOR ASSERTIONS FAILED:\n  - " + "\n  - ".join(errs))
print("assertions: all passed")