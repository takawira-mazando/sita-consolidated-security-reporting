# G2 — AI Report Generation Plan (Alternative)

> ## ⚠️ SUPERSEDED — 6 October 2026
> **Replaced in full by [`AI_INTEGRATION_PLAN_MASTER.md`](AI_INTEGRATION_PLAN_MASTER.md)**, with the POC-level detail in [`G2_POC_2026-10-15/`](G2_POC_2026-10-15/) — plan (`01`), decision papers (`02`), live evidence (`04`), architecture assessment (`05`), decision record (`06`), execution plan (`07`).
> Retained as the dated original. Claims in this document that did not survive live verification: **"11 roles"** (there are 14), the **"Estate risk is 62"** worked example (live max is 25.2, avg 7.46, every row `safe`), and **"nothing existing modified"** (one `include_router` line in `app/main.py` is unavoidable). Three further additions: `DERIVED_FROM_ESTATE_WIDE` as a third disclosure class, a **`NEVER_READ` denial of `identity.users` and `audit.action_audit`**, and the fact that **9 of 16 warehouse tables are unscopable, not 6**.

**Document ID:** G2 (superseded)
**Type:** ALTERNATIVE PLAN — proposal only, nothing built
**Status:** Draft for approval
**Date:** 2026-10-05
**Relates to:** `G1_AI_Integration_Plan.md` (broader AI programme: copilot + triage + narrative)
**Stage placement:** Stage 4 (REST API) — additive
**Hosting:** Self-hosted / on-prem or sovereign cloud. No security data leaves the environment.

---

## 0. What this document is

An **alternative** to the AI-reporting section of G1. Where G1 treats RBAC and tenancy as a *mitigation to be respected*, this plan treats them as the **primary design constraint that determines the architecture**. Everything else — prompts, models, report catalogue — is downstream of that decision.

**Three properties this plan guarantees by construction:**

1. **Nothing existing changes.** No modification to any current router, export, dashboard, prompt, or warehouse table. Every file and every table is new.
2. **A report cannot be requested without an authorisation decision.** RBAC and tenancy are resolved *before* any data is read, into a frozen object that every data accessor must physically accept as an argument.
3. **A model cannot widen its own scope.** The prompt receives pre-scoped, disclosure-classed facts. The model has no tool, no SQL, no database handle — it cannot ask for anything it was not given.

---

## 1. Non-interference with existing reports

The existing reporting surface is treated as **frozen**. The AI capability is a parallel addition.

| Existing artefact | Location | Change |
|---|---|---|
| AG compliance attestation | `app/api/routers/exports_ag.py` — `build_attestation()` | **None.** AI narrative is *not* embedded. It is a separate, unsigned report. |
| CSV exports | `app/api/routers/exports.py` | **None** |
| Provincial benchmark | `app/api/routers/benchmark.py` — `_build_benchmark()` | **None.** Read-only reuse as a data source. |
| Static dashboard narratives | `frontend/src/data/explanations.ts` — `buildExplain` / `buildLayman` | **None.** The AI report is a *separate* surface. |
| Marketing pipeline copy | `frontend/src/pages/HomePage.tsx` — `PIPELINE_STAGES` | **None** |
| Stage diagram | `architecture.html:936-941` | **None.** Stage 4 is already REST API; no re-numbering. |
| Warehouse tables | `warehouse.*` | **None.** AI artefacts go to a **new `ai` schema**. |
| Risk / alert / compliance engines | `app/processing/` | **None** |

**New objects only:**

```
backend/app/api/routers/reports_ai.py      new Stage-4 router
backend/app/ai/…                           new prompting engine (see §4)
infrastructure/scripts/init-ai-schema.sql   new DDL — schema "ai"
```

**Rationale for not embedding AI in the AG attestation:** the attestation is an ECDSA-signed legal artefact whose current `build_attestation()` is a pure, deterministic function unit-tested without a DB (`tests/test_exports_ag.py:71-109`). Injecting nondeterministic model output into it would make the signature attest to text nobody verified deterministically. Keeping AI reports separate preserves the attestation's determinism, which is worth more than the convenience. *(If the AG liaison later requires an AI narrative inside the attestation, that is a separate, explicitly-approved change to G2 §12 open decision 3.)*

---

## 2. Why RBAC and tenancy must drive the architecture

The platform's tenancy model is denormalised onto every warehouse row as four slug columns (`department_id`, `branch_id`, `ministry_id`, `cluster_id`) at write time (`app/lake/writer.py:74-77`, and five other write sites). Scope is carried in the JWT (`app/security.py:34-59`) and **is not re-derived from the database per request** (`app/api/auth.py:52-73`).

Three properties follow, and each one shapes the design:

| Property | Consequence for AI reports |
|---|---|
| `tenant_filter()` is **opt-in** — there is no middleware (`app/main.py:74-120`) | A forgotten call silently returns the whole estate. Scope must be made **impossible to omit**. |
| Scope is **ambient** — passed as `claims` wherever the author remembered | Data helpers must take scope **explicitly and positionally**. No ambient authority. |
| `tenant_filter()` requires `department_id` + `branch_id`; it raises `AttributeError` on `ComplianceSnapshot`, `ComplianceGap`, `SystemMetric`, `SloMetric`, `Agent` | Compliance data is **structurally unscopable** today. That must become an **explicit, typed, disclosed fact** — not an accident. |

---

## 3. The two-gate authorisation model

Every AI report request passes **two independent gates**, in order, before any warehouse row is read.

```
POST /api/v1/reports-ai/generate
        │
        ├─ GATE 1 — RBAC: may this ROLE request this REPORT TYPE at all?
        │           require_report_permission("executive_briefing")
        │           permission namespace: report_ai:<report_type>
        │
        ├─ GATE 2 — TENANCY: freeze the caller's scope into ReportScope
        │           resolve_report_scope(claims) -> ReportScope (frozen)
        │
        ├─ FACT PACK: built ONLY through the frozen scope
        │           every accessor requires scope as a positional argument
        │           each fact carries a DisclosureClass
        │
        ├─ PROMPT: model receives facts + disclosure classes. No DB. No SQL. No tools.
        │
        └─ VERIFIER: numerals grounded? claims within role's ClaimMatrix? scope_hash match?
```

### 3.1 Gate 1 — capability RBAC (per report type, not coarse)

Existing RBAC is coarse: `require_roles("findings")` grants the whole findings surface (`app/api/auth.py:21-36`). For AI reports that is too coarse — a `dbsec` role holding `findings` must not be able to request an executive briefing.

The AI permission namespace is therefore **per report type**:

```python
# backend/app/ai/permissions.py
REPORT_AI_PERMISSIONS: dict[str, str] = {
    "executive_briefing":        "report_ai:executive",
    "soc_shift_handover":         "report_ai:soc",
    "appsec_posture":             "report_ai:appsec",
    "dbsec_posture":              "report_ai:dbsec",
    "compliance_status":          "report_ai:compliance",
    "department_monthly":         "report_ai:executive",
    "peer_benchmark":             "report_ai:executive",
}

ROLE_REPORT_AI: dict[str, frozenset[str]] = {
    "exec":                  frozenset({"report_ai:executive", "report_ai:compliance"}),
    "compliance":            frozenset({"report_ai:compliance", "report_ai:executive"}),
    "soc":                   frozenset({"report_ai:soc"}),
    "province-soc-lead":     frozenset({"report_ai:soc", "report_ai:executive"}),
    "appsec":                frozenset({"report_ai:appsec"}),
    "local-appsec":          frozenset({"report_ai:appsec"}),
    "dbsec":                 frozenset({"report_ai:dbsec"}),
    "dept-admin":            frozenset({"report_ai:appsec", "report_ai:soc"}),
    "transversal-admin":     frozenset({... all ...}),
    "admin":                 frozenset({... all ...}),
    "operator":              frozenset({... all ...}),
}
```

This is a **new, additive namespace**. It does not modify `ROLES_HIERARCHY` or any existing role definition.

A role absent from `ROLE_REPORT_AI` gets **no** AI reports. Default-deny, not default-allow.

### 3.2 Gate 2 — tenancy (`ReportScope`, a frozen value object)

The structural fix. `ReportScope` is created once per request, is immutable, and is a **required positional parameter** of every data accessor — so a function that reads the warehouse cannot be called without a scope.

```python
# backend/app/ai/scope.py
from dataclasses import dataclass, field
from typing import FrozenSet

@dataclass(frozen=True, slots=True)
class ReportScope:
    """Immutable, fully-resolved tenant scope. Created once, passed explicitly.

    There is deliberately no `claims` accessor and no `get_current_user()` call
    anywhere in this object: the scope is resolved once and cannot drift.
    """
    subject: str                     # claims.sub
    roles: FrozenSet[str]            # claims.roles
    department_ids: FrozenSet[str]   # already province-expanded
    branch_ids: FrozenSet[str]
    province_ids: FrozenSet[str]
    nationwide: bool                 # is_nationwide(claims)
    scope_class: ScopeClass          # TENANT_SCOPED | ESTATE_WIDE
    scope_hash: str                  # sha256 of canonical scope tuple

    def tenant_filter(self, model): ...   # delegates to app.api.auth.tenant_filter
    def permits_department(self, dept_id: str) -> bool: ...
    def permits_branch(self, branch_id: str) -> bool: ...
```

`scope_hash` = `sha256(canonical_json({sorted department_ids, branch_ids, province_ids, nationwide}))`. It is recorded in the audit row, returned to the caller, and used as part of the cache key — so a cached report minted for one scope can never be served to another (§7).

### 3.3 Data accessors require scope positionally

```python
# GOOD — scope is structurally mandatory
async def findings_severity_counts(scope: ReportScope, db: AsyncSession) -> dict[str, int]: ...

# GOOD — aggregate
async def risk_rows(scope: ReportScope, db: AsyncSession, limit: int) -> list[dict]: ...

# IMPOSSIBLE TO WRITE SAFELY — no scope parameter exists
async def findings_severity_counts(db: AsyncSession) -> dict[str, int]: ...   # ← never written
```

Every accessor in `app/ai/context.py` takes `scope: ReportScope` as its **first positional parameter**. A unit test asserts this by signature inspection across the module, so the convention is enforced mechanically rather than by code review.

### 3.4 Scope classes — making the compliance gap explicit

`ComplianceSnapshot` and `ComplianceGap` have **no tenancy columns**. Rather than letting that appear as an `AttributeError` or, worse, as silent estate-wide data, the plan introduces an explicit type:

```python
class ScopeClass(str, Enum):
    TENANT_SCOPED = "tenant_scoped"   # filtered by ReportScope.tenant_filter()
    ESTATE_WIDE   = "estate_wide"     # structurally unscopable today — MUST be disclosed
```

Every fact in the fact pack carries one. Estate-wide facts **must** propagate to the response envelope and **must** be attributed as estate-wide in the narrative — enforced by the verifier (§6), not by prompt politeness.

### 3.5 Provable scope non-widening

The model is given facts that are already scoped. It has no database handle, no query tool, and no ability to request more. Additionally:

- `ReportScope` is frozen and has no mutator.
- Accessors never widen: `tenant_filter()` is applied, never composed away.
- A nationwide role gets `tenant_filter() -> None` (existing behaviour). The AI layer **preserves** this exactly and never re-derives or narrows it behind the user's back.
- A department-scoped role with an empty scope gets `expression.false()` — the existing fail-closed behaviour — and the report renders as empty with an explicit "no data in your scope" notice, never as estate-wide.

---

## 4. Stage 4 file layout

```
backend/app/api/routers/reports_ai.py   router — gates, envelope, audit
backend/app/ai/
  permissions.py     Gate 1 — per-report-type RBAC namespace
  scope.py           Gate 2 — frozen ReportScope, ScopeClass, scope_hash
  accessors.py       warehouse readers; scope is FIRST POSITIONAL arg on all
  context.py         pure fact-pack builder — consumes accessors
  disclosure.py      DisclosureClass tagging + estate-wide attribution
  claims.py          ClaimMatrix — what entity classes a role may see NAMED
  gateway.py         httpx → vLLM; CircuitBreaker reuse; token budget
  redaction.py       PII scrubber — mandatory pre-egress
  generate.py        prompt assembly → generation → verification → fallback
  verify.py          numeral fidelity + claim permission + scope_hash checks
  templates/*.yaml   7 versioned prompt templates
infrastructure/scripts/init-ai-schema.sql   schema "ai"
```

---

## 5. Report catalogue — RBAC × tenancy matrix

`—` means the role cannot request it at all (Gate 1 denies).

| Report type | exec | compliance | soc | appsec | dbsec | transversal-admin | Scope class |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `executive_briefing` | ✓ | ✓ | — | — | — | ✓ | tenant (province/estate) |
| `peer_benchmark` | ✓ | ✓ | — | — | — | ✓ | tenant + anonymised peers |
| `compliance_status` | ✓ | ✓ | — | — | — | ✓ | **estate-wide — disclosed** |
| `department_monthly` | — | — | — | ✓ | ✓ | ✓ | tenant (single dept) |
| `soc_shift_handover` | — | — | ✓ | ✓ | — | ✓ | tenant |
| `appsec_posture` | — | — | ✓ | ✓ | — | ✓ | tenant |
| `dbsec_posture` | — | — | — | — | ✓ | ✓ | tenant |

---

## 6. Claim permission — the RBAC layer *inside* the output

A role may be permitted to request a report but not to see everything inside it. This is a second, distinct RBAC layer, applied to the generated text rather than the request.

```python
# backend/app/ai/claims.py
class ClaimClass(str, Enum):
    HEADLINE_METRICS   = "headline_metrics"
    RISK_BUCKETS       = "risk_buckets"
    APP_NAMES          = "app_names"
    DEPARTMENT_NAMES   = "department_names"
    CVE_IDS            = "cve_ids"
    ALERT_IDS          = "alert_ids"
    OWNER_NAMES        = "owner_names"      # from app_catalog.yaml / enriched_data
    RULE_IDS           = "rule_ids"
    AGGREGATE_COMPLIANCE = "aggregate_compliance"   # no control-level detail

ROLE_CLAIMS: dict[str, frozenset[ClaimClass]] = {
    "exec": frozenset({HEADLINE_METRICS, RISK_BUCKETS, APP_NAMES,
                       DEPARTMENT_NAMES, AGGREGATE_COMPLIANCE}),
    "soc": frozenset({HEADLINE_METRICS, APP_NAMES, CVE_IDS, ALERT_IDS,
                      OWNER_NAMES, RULE_IDS, DEPARTMENT_NAMES}),
    "appsec": frozenset({HEADLINE_METRICS, APP_NAMES, CVE_IDS, RISK_BUCKETS}),
    "dbsec": frozenset({HEADLINE_METRICS, APP_NAMES, RISK_BUCKETS}),
    "compliance": frozenset({HEADLINE_METRICS, DEPARTMENT_NAMES, RISK_BUCKETS,
                             AGGREGATE_COMPLIANCE}),
}
```

**Enforcement:** after generation, the verifier scans the output for claim patterns (`CVE-\d{4}-\d+`, alert UUIDs, department names, rule ids, owner names) and discards any sentence containing a `ClaimClass` the role does not hold. This is a **post-generation filter with discard**, not a warning — a failed verification returns the deterministic template, never the model text.

**Why this matters:** an `exec` role sees "Estate risk is 62, critical exposure concentrated in 4 applications" — no CVE list, no owner names. A `soc` role sees "CVE-2026-31429 on payment-gateway, alert a1b2…, owner Payment Ops". Same report type family, materially different disclosure. Today the platform differentiates only by *which dashboard* you land on; this differentiates by *what your narrative is permitted to say*.

---

## 7. Endpoint contract

`POST` routes under `/api/v1/reports-ai/…`. Avoids the `GET`-path hijack in `frontend/src/api/demoInterceptor.ts:34-42` (`/findings|/metrics|/risks|/compliance|/dashboard|/public/summary`).

| Method | Path | Auth |
|---|---|---|
| `POST` | `/api/v1/reports-ai/generate` | Gate 1 + Gate 2 |
| `GET` | `/api/v1/reports-ai/available` | Returns only the report types **this caller** may request |
| `GET` | `/api/v1/reports-ai/audit/{report_id}` | Own reports only; reveals nothing about scope size |

Response envelope — authorisation facts are part of the contract, not metadata:

```json
{
  "report_id": "…",
  "report_type": "soc_shift_handover",
  "narrative_html": "<h3>SOC handover — Gauteng</h3>…",
  "authorisation": {
    "granted_by_role": "soc",
    "permission": "report_ai:soc",
    "scope_class": "tenant_scoped",
    "scope_hash": "sha256:9f2c…",
    "departments_in_scope": 13,
    "claim_classes_applied": ["headline_metrics","app_names","cve_ids"]
  },
  "disclosure": [],
  "provenance": {
    "model_id": "…", "model_digest": "sha256:…",
    "prompt_id": "soc_shift_handover", "prompt_version": 3,
    "generated_at": "2026-11-19T09:14:22Z", "latency_ms": 6120
  },
  "verification": { "numerals_checked": 47, "ungrounded": 0, "claims_violations": 0, "passed": true },
  "fallback_used": false
}
```

**Cache key** = `sha256(report_type + scope_hash + fact_pack_hash + prompt_version + model_digest)`. Scope is in the key, so cross-scope cache poisoning is not possible by construction.

**Audit** — one `ActionAudit` row per generation, using the existing shape from `app/api/routers/exports_ag.py:209-221` but a distinct action value, so it is trivially separable from AG attestation rows:

```python
ActionAudit(
    actor=scope.subject,
    action="ai_report_generated",              # VARCHAR(50)
    target=report_type,
    tenant_scope={
        "department_ids": sorted(scope.department_ids),
        "branch_ids": sorted(scope.branch_ids),
        "province_ids": sorted(scope.province_ids),
        "scope_class": scope.scope_class.value,
    },
    payload_hash=report_id_hash,
)
```

The AG attestation and its verification endpoint are untouched — AI rows never appear in an attestation.

---

## 8. Prompt contract

Versioned YAML, matching the existing `alert_rules.yaml` / `field_mapper.yaml` convention.

```yaml
report_type: soc_shift_handover
version: 3
model_tier: reasoning
system: |
  You are a SOC shift-handover writer for a South African government security
  operations centre. Write only from the FACTS block.
  If a required figure is absent, write "not tracked in this build" — never estimate.
  Never state a finding is remediated unless FACTS.status confirms it.
  Do not name any department outside the SCOPE block.
  Do not name CVE, alert, owner or rule identifiers — your audience profile does
  not permit identifier-level claims.
input:
  facts_from: context.build_soc_context     # pure, consumes scope-bound accessors
  max_tokens: 1200
  temperature: 0.2                          # reporting, not creative writing
constraints:
  - figures_only_from_facts: true
  - allowed_claim_classes: [headline_metrics, app_names, department_names]
  - estate_wide_attribution: required
output:
  schema: narrative_html      # constrained decode; <h3>/<ul>/<li>/<strong> only
```

`allowed_claim_classes` is injected from the caller's role (§6). The prompt states the restriction, and the verifier independently enforces it — the prompt is not the control.

---

## 9. New database objects — schema `ai`

Kept out of `warehouse` so the existing reporting tables are untouched.

```sql
CREATE SCHEMA IF NOT EXISTS ai;

CREATE TABLE ai.report (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_type       varchar(40)  NOT NULL,
  actor             varchar(255) NOT NULL,
  scope_hash        varchar(80)  NOT NULL,
  scope_class       varchar(20)  NOT NULL,
  department_ids    jsonb        NOT NULL,
  branch_ids        jsonb        NOT NULL,
  prompt_version    integer      NOT NULL,
  model_id          varchar(100) NOT NULL,
  model_digest      varchar(80),
  fact_pack_hash    varchar(80)  NOT NULL,
  narrative_html    text,
  verification      jsonb,
  fallback_used     boolean      NOT NULL DEFAULT false,
  disclosure        jsonb,
  latency_ms        integer,
  created_at        timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX ai_report_actor_idx   ON ai.report (actor, created_at DESC);
CREATE INDEX ai_report_scope_idx   ON ai.report (scope_hash);
-- Append-only by convention; immutability hardening is Phase 0 of G1 (P0-5).
```

Written to `audit.action_audit` as well, so AI report generation appears in the existing audit trail alongside every other privileged action.

---

## 10. Verification plan — the actual proof

RBAC and tenancy claims are only worth as much as their tests. Six suites, all CI-gated.

| Suite | Method | Pass criterion |
|---|---|---|
| **S1 Role matrix** | For each of the 11 roles × 7 report types, call the endpoint | Exactly the §5 matrix holds; unknown role → 403 |
| **S2 Scope containment** | `soc` user in Gauteng requests a report; inspect every returned figure | Zero rows with `department_id` outside the province-expanded set |
| **S3 Scope non-escalation** | Provincially-scoped user attempts to name another province via the prompt | Verifier rejects; `expression.false()` yields empty, never estate-wide |
| **S4 Claim permission** | `exec` request a report; scan output for `CVE-\d{4}-\d+`, alert UUIDs, owner names | Zero violations of unheld claim classes |
| **S5 Cache isolation** | Generate as provincial user, replay cache key as national user | Different `scope_hash` → cache miss, no cross-serve |
| **S6 Structural enforcement** | Import `app/ai/accessors.py`, assert `scope: ReportScope` is first positional param on every public function | 100% compliance |

**S6 is the one that prevents regression.** It is a signature-inspection test, not a behavioural test — it fails the build if anyone adds a warehouse-reading function without a mandatory scope parameter.

Plus a **numeral-fidelity suite**: every figure in generated prose must exist in the fact pack. Failure → discard → deterministic fallback.

---

## 11. Deterministic fallback

When the model is unavailable, the breaker is open, verification fails, or `llm_enabled=False`:

- The report renders from a **static Jinja2 template** driven by the same fact pack — same numbers, no prose flourish.
- `fallback_used: true` is returned and surfaced in the UI.
- The fact pack is **identical** in both paths, so a fallback report never shows different numbers from an AI report for the same scope and moment.

The fallback is also the mechanism that makes the whole capability safely demoable and testable with **no GPU at all** — a useful property independent of the AI itself.

---

## 12. Explicit non-goals

1. **No change to any existing report, export, dashboard, prompt, or table.**
2. **No AI text inside the AG attestation.** A separate signed artefact would be required, and is an open decision.
3. **No model-generated SQL, ever.** Not for reports, not for the copilot.
4. **No scope held in prompt text.** Scope is enforced in code; the prompt only *discloses* it.
5. **No new role names or modified `ROLES_HIERARCHY`.** A new additive permission namespace only.
6. **No SaaS LLM.** Self-hosted; sovereign cloud only as DR, behind the same redaction gate.
7. **No default-allow.** A role absent from `ROLE_REPORT_AI` gets nothing.

---

## 13. Open decisions

| # | Decision | Owner | Blocks |
|---|---|---|---|
| 1 | Approve `ai` schema in the main DB, or a separate reporting DB? | Data Architect + DevOps | §9 |
| 2 | Is estate-wide compliance disclosure acceptable, or must compliance reports wait for tenancy columns on `ComplianceSnapshot`/`ComplianceGap`? | Compliance Analyst | `compliance_status` report |
| 3 | Does AG require an AI narrative inside the attestation? (G2 §1 says keep separate) | AG liaison | nothing — safe default is "separate" |
| 4 | Claim-class granularity — is `DEPARTMENT_NAMES` safe for `exec` estate-wide, given provincial sensitivity? | Compliance + AG liaison | §6 matrix sign-off |
| 5 | Audit retention for `ai.report` — same as `audit.action_audit`? | Compliance Analyst | §9 |
| 6 | GPU CAPEX, or sovereign-cloud-only? (carried from G1) | Sponsor / PM | non-functional, not this plan |

---

## 14. Acceptance criteria

- [ ] No existing router, export, dashboard, prompt, or warehouse table is modified — verified by diff review against `main`.
- [ ] Every role × report-type combination behaves exactly as the §5 matrix.
- [ ] `accessors.py` has 100% scope-first-positional coverage, enforced by test S6.
- [ ] A provincial user cannot retrieve any figure from outside their province, verified by S2 and S3.
- [ ] An `exec` report contains zero CVE IDs, alert IDs, or owner names, verified by S4.
- [ ] `scope_hash` appears in the response, the cache key, and the audit row, and is equal across all three for a given request.
- [ ] Every response carries `authorisation` and `disclosure` blocks; neither is optional.
- [ ] Estate-wide compliance figures are attributed as estate-wide in the prose.
- [ ] With the model unavailable, all 7 reports still render with correct numbers via the Jinja2 fallback.
- [ ] `ai.report` rows and `audit.action_audit` rows exist for every generation; AG attestation output is byte-identical to pre-change for the same inputs.
- [ ] Backend `pytest` passes.

---

*No code in this document has been written. This is a proposal for approval.*