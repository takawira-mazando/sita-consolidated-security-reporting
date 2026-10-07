# G2 — RBAC-Guided Prompting Report Agent
## POC Demonstration · Thursday 15 October 2026

**Document ID:** G2-POC-DECK-R4 · **Supersedes:** R3, R1, R2
**Takawira Mazando** — Senior Full Stack Developer, Lead Developer · **Peter Rashaya** — Second Developer · **Richard Masukume** — Head of AI Research *(advisory)*
**Jerry Mokone** — Project Manager · **Victoria Nedombeloni** — Business Analyst · **Kagiso Mokgofa** — Sponsor
**Rendering:** `03_G2_POC_Client_Deck_2026-10-15.html` — arrow keys, space, `F` for fullscreen

---

### Slide 1 — Title

# RBAC-Guided Prompting
## Report Agent — POC Demonstration

Client meeting · Thu 15 Oct 2026

| 7 | 14.25 | 2 244 | 684 |
|---|---|---|---|
| Build days (incl. Sat 10 Oct) | Person-days in register | Findings in scope, live | Rows now disclosed as estate-wide |

**A self-hosted AI agent that writes a security report by prompting a local model — with the prompt assembled from the caller's role and frozen tenancy scope.**

---

### Slide 2 — The team

| Name | Role | G2 responsibility |
|---|---|---|
| **Takawira Mazando** | Senior Full Stack Developer — **Lead Developer** | Scope object, RBAC gate, accessors, claim classes, **role-aware prompts**, router, envelope, audit |
| **Peter Rashaya** | **Second Developer** | The **verifier** and the **containment proofs** — the structural scope test, live tenancy containment. Checks Takawira's code |
| **Richard Masukume** | **Head of AI Research** *(advisory)* | Model pull and latency measurement; gate, freeze and demo review |
| **Jerry Mokone** | Project Manager | Governance, decisions D1–D9, **evidence pack**, sponsor liaison |
| **Victoria Nedombeloni** | Business Analyst | Role/persona definitions, requirement trace, BA support, demo narrative |
| Kagiso Mokgofa | Project Sponsor | Hosting position, Phase 2 authorisation, allocation |

**Register: 14.25 PD / 114.0 h. Build demand 13.25 PD / 106.0 h against 14.00 PD / 112.0 h available — float 0.75 PD / 6.0 h.**

Two things said plainly, because the client will ask:

- **Takawira carries 94.0 h against 56 h available — 168%, i.e. 38.0 h of overtime.** Peter carries 12.0 h. The float is Peter's unused time and cannot be lent to a 16.0 h gate day.
- **Saturday 10 October is worked by Takawira alone**, and Gate C falls on it.

> **Plan hygiene:** the master flight plan lists *Peter Rashaya* as Technical Lead and "Project Lead Takawira and Peter"; Addendum A assigns him 61 PD. **Peter returns to this window** and takes the three verification tasks. Richard Masukume is advisory here. Jerry to align both workbooks.

---

### Slide 3 — Continuation: where this sits

The master plan runs P1–P12. **P10/P11** built the six role dashboards. **P12 (UAT & Go-Live)** sits at 0% with no dates — the critical path.

| | |
|---|---|
| **Today** | Six role-gated React dashboards, CSV exports, AG attestation. **Every figure is hand-authored.** Narrative is fixed text, identical for every reader of that role |
| **The gap** | Stakeholders read the same words regardless of who they are |
| **G2** | A narrative **generated per request**, scoped to the caller's tenancy, written within their permitted claim classes |

**Direction change, per Victoria's requirement:** G2 activity **17.5 — report viewer page — is dropped.** Reports are no longer another React page. **The Vite frontend is not modified.**

---

### Slide 4 — The pipeline

```
POST /api/v1/reports-ai/generate        JWT → claims
        │
        ├─ GATE 1 · RBAC         require_report_permission("executive_briefing")
        │                        default-deny — absent role gets NOTHING
        │
        ├─ GATE 2 · TENANCY      resolve_report_scope(claims) → ReportScope (frozen)
        │                        scope_hash = sha256(canonical scope)
        │
        ├─ RETRIEVAL             scope is FIRST POSITIONAL arg on every accessor
        │                        delegates to tenant_filter() — never re-implemented
        │                        empty scope → expression.false() → fail closed
        │
        ├─ DISCLOSURE            every fact tagged TENANT_SCOPED | ESTATE_WIDE
        │
        ├─ FACT PACK             pure builder + fact_pack_hash
        │                        identical pack feeds BOTH model and fallback
        │
        ├─ PROMPT  ◄── THE POINT  allowed_claim_classes injected FROM THE ROLE
        │                        temperature 0.2, constrained narrative_html
        │                        model gets facts only — no DB, no SQL, no tools
        │
        └─ VERIFY                ① numerals grounded in fact pack
                                 ② claim filter — DISCARD unheld-class sentences
                                 ③ scope_hash match
                                 failure → deterministic template, never model text
```

---

### Slide 5 — Role-aware prompting: the core of the request

`ClaimClass` governs what a role may see **named in the output** — a second RBAC layer on the *text*, not the request.

| ClaimClass | exec | compliance | soc | appsec | dbsec |
|---|:---:|:---:|:---:|:---:|:---:|
| `headline_metrics` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `risk_buckets` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `app_names` | ✓ | — | ✓ | ✓ | ✓ |
| `department_names` | ✓ | ✓ | ✓ | — | — |
| `aggregate_compliance` | ✓ | ✓ | — | — | — |
| `cve_ids` | — | — | ✓ | ✓ | — |
| `alert_ids` | — | — | ✓ | — | — |
| `owner_names` | — | — | ✓ | — | — |
| `rule_ids` | — | — | ✓ | — | — |

```yaml
constraints:
  figures_only_from_facts: true
  allowed_claim_classes: [headline_metrics, risk_buckets, app_names,
                         department_names, aggregate_compliance]   # ← FROM THE ROLE
  estate_wide_attribution: required
```

**Same report type. Same fact pack. Two roles. Materially different text.**

---

### Slide 6 — The prompt is not the control

The prompt *states* the restriction. The verifier *enforces* it, independently.

| Attack | Prompt says | Verifier does |
|---|---|---|
| "Also mention Western Cape" | scope restricted | scope_hash mismatch → **discard** |
| CVE id appears in prose | class not held | sentence-level regex match → **discard sentence** |
| Figure not in the fact pack | "never estimate" | numeral not found → **discard whole output** |
| Province named outside scope | "do not name" | containment test → **discard** |

**Enforcement is discard, never warn.** A failed verification returns the deterministic template.

The adversarial suite runs on day 6 and every attempt must fail at the verifier — that is demo item 8.

**Who writes what.** The verifier is written by **Peter Rashaya**; the prompt builder and templates it polices are **Takawira's**. The two are never merged under one owner.

**One claim, restated.** We do not say "the ground truth is not authored by the model author" — under this delivery split it would not be literally true, and the Lead Developer does own the prompt layer. What is true, and provable: scope and capability **delegate** to `tenant_filter()` and SQL introspection, neither of which can be widened from a prompt; the prompt builder only serialises facts the fact pack already contains; and the live containment proof is run by the second developer, not by the prompt's author.

---

### Slide 7 — Model hosting: resolved, no CAPEX

**Ollama 0.35.1 is installed and running on this machine** — PID 27452, port 11434. Verified 6 Oct.

| Check | Result |
|---|---|
| Registry reachable | HTTP 200 |
| Disk free | 84.3 GB |
| RAM | 15.6 GB |
| CPU | i5-11400H, 6-core, no GPU |
| **Model** | **`qwen2.5:3b` (~2 GB) — pulled day 1** |

**This satisfies G2 §12(6) — no SaaS LLM, self-hosted — with zero CAPEX and zero procurement lead time.**

R01 (GPU/hosting slip, **Critical 16**) **does not apply to this window.** D6 was withdrawn in the last draft for want of evidence; it is now **answered**.

**If the pull fails:** the fallback serves the same fact pack and therefore **the same numbers**. The demo degrades to a template report. Pre-agreed, not a failure.

---

### Slide 8 — Gate 2 verified live, before we wrote anything

`tenant_filter()` applied to `warehouse.findings`:

| Persona | Resolved scope | Rows |
|---|---|---:|
| `exec` | nationwide | **2 244** |
| `compliance` | nationwide | **2 244** |
| `soc` @ Home Affairs | 1 department | **745** |
| `province-soc-lead` @ Gauteng | 15 provincial depts | scoped set |
| `dept-admin` — **no scope** | `expression.false()` | **0** |

**The last row is the important one.** A department role with no assigned scope gets **zero rows, not the whole estate.** Fail-closed is real today.

`scope_hash` is deterministic — order-independent, and it changes the moment scope changes.

---

### Slide 9 — A correction we must make

**G2 §3.4 told you compliance data fails with an `AttributeError`. That is the harmless half.**

| Caller | `tenant_filter()` | Rows | Error? |
|---|---|---:|---|
| `exec` | `None` — no filter | **456 / 456** | **none** |
| `compliance` | `None` — no filter | **456 / 456** | **none** |
| `transversal-admin` | `None` — no filter | **456 / 456** | **none** |
| `soc` (scoped) | raises | 0 | `AttributeError` |

A nationwide caller short-circuits **before** the code touches `department_id`. `None` means no filter — every row returns. Those three roles are **exactly** the three §5 grants `compliance_status` to.

> **The real exposure is not a crash. It is a silent, complete bypass of tenancy scoping for precisely the intended audience — 684 rows, unscoped, undeclared.**

---

### Slide 10 — Why D2 is now the most important decision

Both compliance tables have **no tenancy columns** — 8 and 10 columns, neither carrying `department_id` or `branch_id`.

**There is no code path that will ever scope them.** The columns do not exist.

| Option | Consequence |
|---|---|
| **Declare `ESTATE_WIDE` explicitly** | 684 rows, labelled estate-wide, disclosed in **every** generated response. **The only control available.** |
| Wait for tenancy columns | Warehouse change: columns, backfill, tenancy source of truth for historical snapshots, migration rehearsal, AG sign-off |
| Infer tenancy at query time | **Rejected** — guessing scope in a compliance figure is worse than declaring its absence |

**And it is now generated text.** An unlabelled estate-wide figure in a *model-written* narrative is materially worse than in a fixed dashboard string — the reader cannot tell it was authored under different rules.

---

### Slide 11 — The response envelope

```json
{
  "report_type": "compliance_status",
  "narrative_html": "<h3>Estate compliance posture</h3>…",
  "authorisation": {
    "granted_by_role": "exec",
    "permission": "report_ai:compliance",
    "scope_class": "estate_wide",
    "scope_hash": "sha256:1a99b011a25ec26e",
    "departments_in_scope": 173,
    "claim_classes_applied": ["headline_metrics","risk_buckets",
                               "app_names","department_names",
                               "aggregate_compliance"]
  },
  "disclosure": [
    { "scope_class": "estate_wide", "source": "compliance_snapshots",
      "rows": 456, "reason": "no tenancy columns on table" }
  ],
  "provenance": { "model_id": "qwen2.5:3b", "model_digest": "sha256:…",
                  "prompt_id": "executive_briefing", "prompt_version": 1,
                  "latency_ms": 6120 },
  "verification": { "numerals_checked": 47, "ungrounded": 0,
                    "claims_violations": 0, "passed": true },
  "fallback_used": false
}
```

**A generated security report must be attributable to the exact model and prompt that produced it — or it is not evidence.**

---

### Slide 12 — Demonstration run sheet

| Min | Demonstration | Proves |
|---|---|---|
| 0–3 | `exec` → `executive_briefing`. **Model-generated narrative**, estate rollup, live figures | The agent works |
| 3–5 | Envelope: authorisation, disclosure, provenance with `model_id` + digest | Attribution |
| 5–8 | `exec` → `compliance_status`. `disclosure: [{estate_wide, 456}]` | **Gap declared, not hidden** |
| 8–10 | `exec` → `soc_shift_handover` → **403** | Gate 1 default-deny |
| 10–14 | **Role-aware prompting live:** same report, `exec` vs `soc`. Side-by-side prompt + output | Claim classes drive the text |
| 14–17 | DHA `soc` vs `exec`: 745 vs 2 244, different `scope_hash` | Containment (S2) |
| 17–19 | Provincial persona attempts to widen scope → **fails closed** | Non-escalation (S3) |
| 19–21 | Injected CVE id → **sentence discarded** | Verifier, not prompt, is the control |
| 21–23 | `git diff main` — **nothing existing modified** | Non-interference |
| 23–27 | Phase 2 scope and decisions D1–D9 | Governance |

---

### Slide 13 — Seven days, five gates

| Day | Date | Takawira | Peter | Richard | Gate |
|---|---|---|---|---|---|
| 1 | Wed 7 Oct | `ai` schema; Gate 1 | — | Pull `qwen2.5:3b`, latency | model responds |
| 2 | Thu 8 Oct | `scope.py`; `claims.py`; `disclosure.py` | — | review | **A** — unknown role → 403 |
| 3 | Fri 9 Oct | Accessors; prompt templates + role injection | **S6 scope test** | review; Victoria BA support | **B** — 2 roles → different prompts |
| 4 | **Sat 10 Oct** | Fact packs + hash; eval set — **16.0 h, alone** | — | — | **C — first real generation, cut trigger** |
| 5 | Mon 12 Oct | `generate.py`; fallbacks; `gateway.py` | **`verify.py` — 8.0 h** | review + demo controls | **D** — ungrounded numeral discarded |
| 6 | Tue 13 Oct | Router, envelope, audit; adversarial | **S2/S3 live containment** | review | **E** — all attempts rejected |
| 7 | Wed 14 Oct | Regression; diff review; integration smoke | — | **independently reviews the diff**; Jerry: evidence pack | **FREEZE 17:00** |
| 8 | **Thu 15 Oct** | **POC DEMONSTRATION** | **POC DEMONSTRATION** | demo support | 🏁 |

**14.25 PD of register, 106.0 h of build demand against 112.0 h of capacity. Takawira runs at 94.0 h — 168%, 38.0 h overtime — and Saturday is a solo day. Day 7 is the only buffer and it is also the freeze.**

---

### Slide 14 — Three things that could go wrong

| Risk | Score | What it means | Treatment |
|---|:---:|---|---|
| **R18** — **one developer at 168%** | 25 | Takawira 94.0 h against 56 h; 16.0 h peaks on both gate days; **Saturday worked alone** | Stated, not hidden. Peter owns the verifier so the heaviest load is the deterministic backend. Gate C cut trigger on Sat 10. Richard reviews the freeze diff; Jerry packs the evidence |
| **R09** — **verification concentrated in one person** | 20 | Peter at 21% while Takawira runs at 168%; four tests become self-checks | Three independent checks: the scope test, the verifier and live containment are Peter's, against Takawira's code |
| **R20** — model not pulled | 12 | ~2 GB download on the critical path | Pull day 1. Fallback serves identical numbers. Degradation pre-agreed |
| **R02** — compliance unscopable | 15 | **Confirmed live.** Silent bypass for nationwide roles | Disclosure is the only control. Demo item 3 proves it |
| **R21** — CPU latency | 9 | 3B on a 6-core CPU is slow; ~900 tokens | Cap `max_tokens` at 900, cache fact packs, rehearse day 7 |

**R18 and R20 were identified on 6 October while testing this plan against your system.**

---

### Slide 15 — Decisions D1–D9

| # | Decision | Recommendation |
|---|---|---|
| D1 | `ai` schema target | `ai` schema in the main database |
| D2 | Compliance disclosure | **Declare `ESTATE_WIDE` explicitly** — now proven, and it lands in generated text |
| D3 | AG narrative in the attestation | Keep separate — attestation untouched |
| D4 | `DEPARTMENT_NAMES` for `exec` | Yes, as drafted — **no additions to the exec claim set** |
| D5 | `ai.report` retention | Same as `audit.action_audit`, covering model id, digest and prompt version |
| **D6** | **Model hosting** | **Self-hosted Ollama — no CAPEX, no procurement. ANSWERED** |
| **D7** | Phase 2 authorisation | Authorise a re-estimate, **not a date** |
| **D8** | **Team allocation 7–14 Oct, incl. Saturday** | **Accept Takawira at 168% (94.0 h) with the solo Saturday, or cut `compliance_status` at Gate C** |
| **D9** | **AI tooling** | **Private, local Ollama. No external provider, no API key, nothing leaves the environment. Sovereign cloud as DR only** |

**D4 is now material in a way it was not.** With role-aware prompting, a claim class in the prompt is one the model will try to use. Widening `exec` to include `rule_ids` "for completeness" would put control identifiers into executive prose on the next prompt iteration.

---

### Slide 16 — What we ask of you

| # | Ask | Who signs | If you do not decide |
|---|---|---|---|
| 1 | **Approve the G2 plan** | Jerry, Kagiso | No build authority |
| 2 | **D1** — `ai` schema in the main DB | Data Architect, DevOps | Same. A separate DB breaks audit atomicity and cannot be delivered in 7 days |
| 3 | **D2** — declare `ESTATE_WIDE` | Compliance, AG liaison | **684 rows reach `exec` and `compliance` undeclared, in generated text** |
| 4 | **D3, D4, D5** | Compliance, AG liaison | Defaults adopted as drafted |
| 5 | **D6** — acknowledge self-hosted Ollama | Kagiso, Jerry | Model stays unpulled; no generation demonstrated |
| 6 | **D7** — Phase 2 basis | Kagiso | **29 Jan 2027 remains unsupported by evidence** |
| 7 | **D8 — accept the 168% loading and the solo Saturday**, or cut scope | Kagiso | **Either the overtime is accepted, or `compliance_status` is dropped at Gate C.** Not discovered on 14 Oct |
| 8 | **D9 — confirm private local Ollama** | Richard, Kagiso | **An external provider engages a POPIA DPA review, adds a redaction build task and a gateway abstraction** |

### After today

- **14 Oct 17:00** — POC frozen, evidence pack signed.
- **Within 10 working days** — Phase 2 costed plan with a date, informed by what the POC proved about a 3B local model's narrative quality.

**Amendments today are logged as change control and re-baselined. They do not stop the build.**

---

*Takawira Mazando · Peter Rashaya · Richard Masukume · Jerry Mokone · Victoria Nedombeloni · Evidence verified against the live system 6 Oct 2026. Build 7–14 October 2026, Saturday 10 October included. Dates planned, not committed.*
