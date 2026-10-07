# G2 — Decision Papers D1–D8

**Document ID:** G2-POC-DEC-R3 · **Supersedes:** G2-DEC-PACK-R1 and R2
**Tabled at:** POC demonstration, **Thursday 15 October 2026**
**Prepared:** 6 October 2026 by Jerry Mokone, against the live system

---

## How to read this pack

Each paper states the question, a recommendation grounded in **verified evidence**, and what happens if no amendment is made on 15 October.

> **Standing rule:** *a decision not amended on 15 October is adopted as documented.* The POC proceeds on these positions; later amendments are change control.

| # | Decision | Owner | Recommendation | Status |
|---|---|---|---|---|
| D1 | `ai` schema target | Data Architect, DevOps | `ai` schema in the main database | ready |
| D2 | Estate-wide compliance disclosure | Compliance Analyst, AG liaison | Declare `ESTATE_WIDE` explicitly | **strengthened — proven live** |
| D3 | AG narrative inside the attestation | AG liaison | Keep separate | ready |
| D4 | `DEPARTMENT_NAMES` for `exec` | Compliance Analyst, AG liaison | Yes, as drafted | ready |
| D5 | `ai.report` audit retention | Compliance Analyst | Same as `audit.action_audit` | ready |
| **D6** | **Model hosting** | **Kagiso Mokgofa, Jerry Mokone** | **Self-hosted Ollama — no CAPEX, no procurement** | ✅ **now ANSWERED** |
| D7 | Phase 2 authorisation | Kagiso Mokgofa, Jerry Mokone | Authorise a re-estimate, not a date | new |
| **D8** | **Team allocation 7–14 Oct, incl. Saturday** | **Kagiso Mokgofa** | **Accept Takawira at 168% (94.0 h) with the solo Saturday, or cut `compliance_status` at Gate C** | 🆕 **new** |
| **D9** | **AI tooling — private local Ollama** | **Richard, Kagiso** | **Local private Ollama; sovereign cloud as DR only** | 🆕 **new, 7 Oct** |

---

## D1 — Approve the `ai` schema in the main database, or a separate reporting database?

| | |
|---|---|
| **Owner** | Data Architect (primary) · DevOps (primary) |
| **Source** | G2 §9 · Addendum A 12.3 |
| **POC ref** | Activity 2 — `init-ai-schema.sql`, day 1 |
| **Effort** | 0.5 PD · **Reversibility:** High |

### Verified state, 6 Oct 2026

The `ai` schema **does not exist**. Live inventory returns `warehouse` (16 tables) and `audit` (1 table).

### Question

G2 §9 requires AI artefacts to sit outside `warehouse`. A schema boundary achieves that. Does physical database separation do more?

### Recommendation: `ai` schema in the main database

1. **The isolation requirement is about tables.** G2 §9 says a new *schema*, not a new database. `ai.report` cannot appear in an existing reporting query without an explicit cross-schema reference.

2. **A separate database breaks audit atomicity.** G2 §7 requires one `audit.action_audit` row per generation, written alongside `ai.report`. `audit.action_audit` is in the main database (confirmed live). Across two databases that pair is no longer one atomic commit — the generation could be logged in one store and not the other, which is precisely the property the audit design exists to protect.

3. **A model has no SQL handle in either topology.** G2 §0 guarantees no tool, no SQL, no database handle. Isolation from a leak comes from `ReportScope` and the verifier, not from which server the process runs on.

### Cost of choosing a separate database

An estimated 4–6 PD of provisioning, migration and standing operational work — **none of it inside the 14.25 PD POC register**. It cannot be delivered by 15 October.

### Signature — D1

| Role | Name | Adopt main DB / Separate DB / Amend | Signature | Date |
|---|---|---|---|---|
| Data Architect | | | | |
| DevOps | | | | |
| PM (countersign) | Jerry Mokone | | | |

---

## D2 — Estate-wide compliance disclosure: declare it, or block the report?

| | |
|---|---|
| **Owner** | Compliance Analyst (primary) · AG liaison (contributing) |
| **Source** | G2 §2, §3.4 · Addendum A 12.4 |
| **POC ref** | Activity 6 — `disclosure.py`; demo item 3 |
| **Effort** | 0.5 PD · **Reversibility:** Medium |

### Verified state, 6 Oct 2026

| Caller | `tenant_filter()` on `compliance_snapshots` | Rows | Error |
|---|---|---:|---|
| `exec` | `None` | **456 / 456** | none |
| `compliance` | `None` | **456 / 456** | none |
| `transversal-admin` | `None` | **456 / 456** | none |
| `soc` (scoped) | raises | 0 | `AttributeError` |

Both tables carry **no tenancy columns** — 8 and 10 columns respectively, neither with `department_id` or `branch_id`.

### The correction

**G2 §3.4 describes the risk as an `AttributeError` crash. That is the harmless half.**

A nationwide caller short-circuits in `tenant_filter()` and returns `None` **before** touching `model.department_id`. `None` means no filter — every row returns. Those three roles are **exactly** the three the G2 §5 matrix grants `compliance_status` to.

> **The real exposure is a silent, total bypass of tenancy scoping for precisely the intended audience — 456 + 228 = 684 rows, unscoped, undeclared, no error.**

### Recommendation: proceed with typed `ESTATE_WIDE` disclosure — now the only control

1. **No code path will ever scope these tables.** The columns do not exist. This is not a fixable defect being mitigated; it is the control itself.
2. **Adding tenancy columns is a warehouse programme** — columns, backfill of historical rows, a tenancy source of truth for pre-existing snapshots, migration rehearsal, AG sign-off. It changes the reporting core and breaks G2's first guarantee.
3. **This does not widen any audience.** `compliance_status` is gated to `exec`, `compliance`, `transversal-admin`, all nationwide roles that already hold estate-wide view. Provincial and branch personas are denied at Gate 1. The change is that the figures are **labelled**.
4. **It is demonstrable on 15 October.** `disclosure: [{scope_class: "estate_wide", rows: 456}]` on real data.

### What the client is accepting

- Estate-wide compliance figures, **explicitly labelled**, in the envelope and in the generated prose.
- No provincial or branch-scoped user receives this report at all.
- Adding true tenancy to compliance data becomes a **separate approved change** with its own estimate.

### Signature — D2

| Role | Name | Adopt disclose / Hold report / Amend | Signature | Date |
|---|---|---|---|---|
| Compliance Analyst | | | | |
| AG liaison | | | | |
| PM (countersign) | Jerry Mokone | | | |

---

## D3 — Does the AG require an AI narrative inside the compliance attestation?

| | |
|---|---|
| **Owner** | AG liaison (primary) |
| **Source** | G2 §1, §12(2) · Addendum A 12.5 |
| **POC ref** | Out of scope — the POC touches nothing in the attestation |
| **Reversibility** | Very low once implemented |

### Question

G2 §1 places the AI narrative outside the attestation; G2 §12(2) makes an embedded narrative a separate approved change.

### Recommendation: keep the attestation separate and deterministic

`build_attestation()` is an ECDSA-signed legal artefact and a pure deterministic function, unit-tested without a database (`tests/test_exports_ag.py:71-109`). Injecting nondeterministic model output would make the signature attest to text nobody verified deterministically, and would break the byte-identical regression criterion in G2 §14.

**The POC reinforces this by construction:** because the POC modifies no existing file, `build_attestation()` is untouched. The separation is demonstrated, not merely asserted.

### Note for the record

The one decision where "no" costs nothing today and a great deal later. With a working model now in hand, the temptation to embed narrative is higher than it was when G2 was drafted — which is exactly why it should be settled at this meeting.

### Signature — D3

| Role | Name | Confirm separate / Amend | Signature | Date |
|---|---|---|---|---|
| AG liaison | | | | |
| PM (countersign) | Jerry Mokone | | | |

---

## D4 — Is `DEPARTMENT_NAMES` a safe claim class for an `exec` role?

| | |
|---|---|
| **Owner** | Compliance Analyst + AG liaison |
| **Source** | G2 §6 · Addendum A 12.6 |
| **POC ref** | Activity 7 — `claims.py`; demo item 5 |
| **Effort** | 1.0 PD · **Reversibility:** High |

### Question

With role-aware prompting, the caller's role determines which claim classes may appear **named** in the generated text. Is `DEPARTMENT_NAMES` acceptable for `exec` with estate-wide view, given provincial sensitivity?

### Recommendation: yes — as drafted, with no additions

1. **Not a new disclosure.** `exec` users already see department names in the existing `ExecDashboard` and benchmark surface. Removing the class reduces existing capability, not risk.
2. **The sensitive identifiers are already excluded.** `exec` holds `headline_metrics`, `risk_buckets`, `app_names`, `department_names`, `aggregate_compliance` — and **none** of `cve_ids`, `alert_ids`, `owner_names`, `rule_ids`. `aggregate_compliance` is defined as *"no control-level detail."*
3. **The scoping control is code, not prompt.** Department drill-down is a separate report type, tenant-scoped to one department, unavailable to `exec` under the §5 matrix.

### Condition of approval

`ROLE_CLAIMS` is signed **as drafted in G2 §6**. Any addition to the `exec` set requires fresh Compliance Analyst approval before implementation. This condition is what keeps R05 closed.

**Now material in a way it was not before:** with role-aware prompting, a claim class in the prompt is a class the model will *try* to use. Widening `exec` to include `rule_ids` "for completeness" would put control identifiers into executive prose on the next prompt iteration. The condition is the control.

### Signature — D4

| Role | Name | Adopt as drafted / Amend | Signature | Date |
|---|---|---|---|---|
| Compliance Analyst | | | | |
| AG liaison | | | | |
| PM (countersign) | Jerry Mokone | | | |

---

## D5 — Audit retention for `ai.report`

| | |
|---|---|
| **Owner** | Compliance Analyst |
| **Source** | G2 §9 · Addendum A 12.5 |
| **POC ref** | Activity 15 — `ActionAudit` + `ai.report` write |
| **Effort** | 0.5 PD · **Reversibility:** Medium |

### Question

`ai.report` is a new table. Same retention as `audit.action_audit`, or its own?

### Recommendation: the same as `audit.action_audit`

**One trail, one rule.** Two retention periods across two audit stores is the kind of divergence an audit finding is written about. Every generation writes to both tables, so one rule is the accurate model.

### The distinction to hold on to

Retention is **not** the control that protects `ai.report`. The table is append-only by convention; immutability hardening is **G1 Phase 0, item P0-5** — separate, earlier work. Approving a retention period does not approve immutability, and the two must not be conflated in the record.

With a live model, the audit row gains a new and material field set: `model_id`, `model_digest`, `prompt_version`, `latency_ms`, `fallback_used`. **A generated security report must be attributable to the exact model and prompt that produced it**, or it is not evidence. Retention must cover all of it.

### Verified

`audit.action_audit` exists in the live database and is the correct POC audit sink.

### Signature — D5

| Role | Name | Adopt / Amend | Signature | Date |
|---|---|---|---|---|
| Compliance Analyst | | | | |
| PM (countersign) | Jerry Mokone | | | |

---

## D6 — Model hosting: GPU CAPEX, or sovereign cloud?

| | |
|---|---|
| **Owner** | Kagiso Mokgofa (Sponsor) · Jerry Mokone (PM) |
| **Source** | G2 §13(6), carried from G1 |
| **POC ref** | Activity 1 — pull `qwen2.5:3b`; activity 10 — `gateway.py` |
| **Status** | ✅ **ANSWERED BY EVIDENCE — no longer a client decision** |

### Verified state, 6 Oct 2026

**Ollama 0.35.1 is installed and running on this machine**, PID 27452, serving on `localhost:11434`.

| Check | Result |
|---|---|
| Registry reachable | HTTP 200 |
| Disk free | 84.3 GB |
| RAM | 15.6 GB |
| CPU | i5-11400H, 6-core, **no GPU** |
| Models installed | **0 — `qwen2.5:3b` (~2 GB) to be pulled day 1** |

### Recommendation: self-hosted Ollama on existing hardware — no CAPEX, no procurement

R2 withdrew this decision because no model infrastructure could be found. **That was wrong.** The runtime was installed and serving; only the weights were absent.

1. **It satisfies G2 §12(6) directly** — no SaaS LLM, self-hosted, with sovereign cloud available later as DR behind the same redaction gate.
2. **Zero CAPEX, zero lead time.** R01 (GPU/hosting slip, Critical 16) does not apply to this window. There is nothing to procure and no budget cycle to enter.
3. **Reversibility is cheap.** `gateway.py` is an httpx client against an OpenAI-compatible endpoint. Moving to sovereign cloud or on-prem GPU later is configuration, not a rewrite.
4. **A 3B model on CPU is sufficient for the POC.** The claim here is not prose quality — it is that a role-aware prompt produces role-appropriate text over correctly scoped facts, and that the verifier catches what the model gets wrong.

### The remaining risk, stated plainly

**R20 — the model is not yet pulled.** A ~2 GB download sits on the critical path. If it fails, the deterministic fallback serves **the same fact pack and therefore the same numbers**, and the demonstration degrades to a template report. That degradation is pre-agreed, not a failure — and it is why the POC was designed with the fallback in the same scope rather than deferred.

### Signature — D6

| Role | Name | Acknowledge self-hosting / Amend | Signature | Date |
|---|---|---|---|---|
| Project Sponsor | Kagiso Mokgofa | | | |
| Project Manager | Jerry Mokone | | | |

---

## D7 — What is authorised beyond 15 October?

| | |
|---|---|
| **Owner** | Kagiso Mokgofa (Sponsor) · Jerry Mokone (PM) |
| **Effort** | 0.0 PD |

### The question

Addendum A committed **145.5 person-days over 18 weeks** to a **29 January 2027** go-live. The POC delivers a working role-aware prompting agent in **14.25 PD over 7 build days** — and does not deliver 5 of 7 report types, the cache, load testing, an independent security review, UAT, or production deployment.

**Is a Phase 2 date authorised now, or after the POC?**

### Recommendation: authorise a Phase 2 re-estimate, not a date

1. **29 January 2027 is not supported by the available evidence.** It came from an estimate whose largest components assumed a model hosting decision and a capacity position that did not exist. Now that Ollama resolves D6 at zero cost, that estimate is materially wrong in the client's favour on cost and materially wrong on scope.

2. **The POC changes the estimate.** It prices 2 of 7 report types for real, prices the authorisation core, and — most usefully — **proves or disproves whether a 3B local model produces acceptable narrative quality.** That last answer determines whether Phase 2 needs hosting investment at all. It cannot be known before 15 October.

3. **The alternative is worse.** Committing a date now means committing either to narrative quality nobody has seen, or to a scope the POC has not validated.

### What is being asked

| Option | Meaning |
|---|---|
| **Adopt (recommended)** | Phase 2 authorised in principle. A costed plan with a date follows **within 10 working days** of the POC. **29 Jan 2027 is withdrawn.** |
| Amend | A date is required on 15 October. It must then be set against the POC's demonstrated scope, with the gap to Addendum A's scope stated in writing. |

### Signature — D7

| Role | Name | Adopt / Amend | Signature | Date |
|---|---|---|---|---|
| Project Sponsor | Kagiso Mokgofa | | | |
| Project Manager | Jerry Mokone | | | |

---

## D8 — Allocation of the delivery team for 7–14 October, including Saturday 10 October

| | |
|---|---|
| **Owner** | Kagiso Mokgofa (Sponsor) |
| **Effort** | 0.0 PD — but it determines whether the POC exists |
| **Revised** | 7 October 2026 — see the table below. The original D8 asked for a balanced 100% split; the actual plan is not balanced. |

### The question

The POC requires **14.25 person-days (114.0 hours)** in the register, of which **13.25 PD / 106.0 h is build demand**, by **two builders** in **7 build days**.

| Allocation | Capacity | Build demand | Headroom |
|---|---:|---:|---:|
| **100%** | **14.00 PD / 112.0 h** | 13.25 PD / 106.0 h | **+0.75 PD / +6.0 h** |

**The register fits. The individual calendar does not.** That distinction is the substance of this decision:

| Resource | Tasks | Hours | Share of 56 h | Position |
|---|---:|---:|---:|---|
| **Takawira Mazando** | 34 | **94.0** | **168%** | **38.0 h overtime** |
| **Peter Rashaya** | 3 | 12.0 | 21% | — |
| Richard Masukume *(advisory)* | 1 | 4.0 | — | +4.0 h review outside the register |
| Jerry Mokone | 1 | 4.0 | — | evidence pack (DEL-19) |
| Victoria Nedombeloni *(support)* | — | 6.0 | — | all of it Fri 9 Oct |

The 6.0 h of float is Peter's unused capacity. It **cannot be lent to a 16.0 h gate day.**

**Saturday 10 October is a working day worked by Takawira alone** — 16.0 h, no peer on site, and Gate C's cut-trigger decision falls on it. Peter's tasks are Fri 9, Mon 12 and Tue 13; Victoria's support and Richard's review both move off the weekend.

### Recommendation

**Accept the plan as it now stands:** Takawira and Peter at 100% for 7–14 October including Saturday 10 October, Richard advisory, Jerry on the evidence pack. This asks the sponsor to accept **38.0 h of overtime and a single-person Saturday**, not to re-allocate them.

### What is being asked

Acknowledge the 168% loading and the solo Saturday, or instruct that `compliance_status` be dropped to bring Takawira inside a normal week.

### The alternative, stated honestly

If the overtime or the Saturday is declined, the correct response is to **cut scope now** — drop the `compliance_status` report type at Gate C — rather than discover it on 14 October. That decision is better made now than in a status meeting. The cost is real and should be named in advance: it removes demo item 3, the disclosure envelope, which is the strongest single demonstration that the design surfaces its own limits.

### Signature — D8

| Role | Name | Accept as planned / Decline / Amend | Signature | Date |
|---|---|---|---|---|
| Project Sponsor | Kagiso Mokgofa | | | |

---

## D9 — AI tooling for the proof of concept

| | |
|---|---|
| **Owner** | Richard Masukume, Kagiso Mokgofa |
| **Effort** | 0.0 PD — the default costs nothing; changing it costs 1.5–2.5 PD |
| **Status** | **new, 7 October 2026** |

### The question

Which model runtime does the POC use: the **private, local Ollama** already running on the build host, or an external / sovereign-cloud provider?

### Recommendation: private, local Ollama as the default

`qwen2.5:3b` on the existing 6-core host, no GPU, no API key, **no security data leaving the environment**. The model pull and latency measurement are Richard's T01, charged at 0.5 h on each non-Saturday day of the window.

Sovereign cloud and any SaaS API remain available **as disaster recovery only**, behind the same redaction gate.

### What changes if this is overturned

| Consequence | Why |
|---|---|
| Mandatory redaction becomes a build task, not a gate | A prompt leaving the network can carry PII from `Finding.raw_data` unless something strips it first |
| The gateway needs a provider abstraction | `gateway.py` currently targets one endpoint shape |
| POPIA DPA review becomes blocking | An external processor engages a data-protection obligation |
| **R21 retires and is replaced** | CPU latency stops being the constraint; network latency becomes it |

### Signature — D9

| Role | Name | Adopt local default / Amend | Signature | Date |
|---|---|---|---|---|
| Head of AI Research | Richard Masukume | | | |
| Project Sponsor | Kagiso Mokgofa | | | |

---

## Signature sheet — all nine

| # | Decision | Owner | Adopt / Amend | Signature | Date |
|---|---|---|---|---|---|
| D1 | `ai` schema target | Data Architect | | | |
| D1 | `ai` schema target | DevOps | | | |
| D2 | Estate-wide compliance disclosure | Compliance Analyst | | | |
| D2 | Estate-wide compliance disclosure | AG liaison | | | |
| D3 | AG attestation narrative | AG liaison | | | |
| D4 | `DEPARTMENT_NAMES` for `exec` | Compliance Analyst | | | |
| D4 | `DEPARTMENT_NAMES` for `exec` | AG liaison | | | |
| D5 | `ai.report` audit retention | Compliance Analyst | | | |
| D6 | Model hosting — self-hosted Ollama | Kagiso Mokgofa | | | |
| D6 | Model hosting — self-hosted Ollama | Jerry Mokone | | | |
| D7 | Phase 2 authorisation | Kagiso Mokgofa | | | |
| D7 | Phase 2 authorisation | Jerry Mokone | | | |
| **D8** | **Team allocation 7–14 Oct incl. Saturday (168% + overtime)** | **Kagiso Mokgofa** | | | |
| **D9** | **AI tooling — private local Ollama** | **Richard Masukume** | | | |
| **D9** | **AI tooling — private local Ollama** | **Kagiso Mokgofa** | | | |

**Countersigned by PM:** ................................................  **Date:** ................

**G2 plan approval:**  Approved ☐   Approved with amendment ☐   Deferred ☐

**Amendments raised on 15 October (logged as change control):**

............................................................................

............................................................................

---

*Prepared by Jerry Mokone, 6 October 2026. D1–D6 grounded in queries executed against the live system. D7–D9 are new. D8 and D9 revised 7 October 2026: the build window is 7–14 October with Saturday 10 October worked by Takawira alone, Takawira carries 94.0 h against 56 h available, Peter Rashaya returns to the three verification tasks, and Richard Masukume is advisory.*
