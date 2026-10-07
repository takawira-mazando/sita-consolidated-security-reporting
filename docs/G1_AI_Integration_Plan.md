# G1 — AI Integration Plan

> ## ⚠️ SUPERSEDED — 6 October 2026
> **Replaced in full by [`AI_INTEGRATION_PLAN_MASTER.md`](AI_INTEGRATION_PLAN_MASTER.md).**
> Retained as the dated original. Seven claims in this document were tested against the live system and **did not survive** — see master §2. Most materially: the GPU/vLLM hosting decision (§3.1) is resolved by Ollama already running on the host; the `tenant_filter` `AttributeError` failure mode (§5) is **inverted** — nationwide callers get silent full-table access, not a crash; and §8's blocking items P0-1/P0-2/P0-3 are **not applicable** — none of those secret files has ever been committed, in any branch's history.

**Document ID:** G1 (superseded)
**Programme:** HOSI-UNIFIED MANAGED SERVICES — AI workstream (Month 4+)
**Status:** Draft for approval
**Date:** 2026-10-05
**Extends:** `scratch/plan_dump.txt` (Months 1–3, 71.2% complete)
**Hosting constraint:** Self-hosted / on-prem or sovereign cloud. No security data leaves the environment.
**Stage placement:** AI integrated at **Stage 4 (REST API)** — see §4A. Stage 4 gains `api/routers/reports_ai.py` + `app/ai/`; Stages 5 and 6 consume its JSON. No AI in Stages 1–3 hot paths.

---

## 1. Executive summary

The platform ingests, normalises and fuses security data from four OEM sources (AppScan Cloud, Imperva DAM/WAF, API Security, Compliance) into a PostgreSQL warehouse, and serves six role-scoped dashboards. Today, every insight it surfaces is a **fixed arithmetic** — a weighted sum (`app/processing/risk_engine.py:14`), a rule evaluation (`alert_rules.yaml`), or a hardcoded template (`frontend/src/data/explanations.ts`).

This plan adds a **self-hosted LLM capability** in three increments, ordered by risk-adjusted value:

| # | Capability | User value | Risk | Weeks |
|---|---|---|---|---|
| **1** | **Narrative reporting & executive briefings** | Turns numbers into board-ready prose; feeds the AG attestation | Low — read-only, grounded, signed | 4 |
| **2** | **Finding triage & severity assist** | Cuts alert fatigue; suggests severity/CWE/exploitability for human approval | Medium — advisory only | 5 |
| **3** | **Analyst copilot (NL query over findings)** | Removes the need to learn every dashboard | High — must not breach tenancy | 6 |

**Placement: all three land at Stage 4 (REST API).** Per the platform's own taxonomy (`architecture.html:936-941`), AI report generation is a Stage-4 concern — the layer that already owns `tenant_filter()` and is the single contract point for Stages 5 and 6. The model never runs in the ingestion or dispatch path. See §4A.

The single most important design decision: **the model never writes SQL, and never sees an un-tenant-filtered row.** See §5.

### The blocking problem found during assessment

`tenant_filter()` (`backend/app/api/auth.py:210`) is **opt-in per endpoint with no middleware enforcing it** (`backend/app/main.py:74-120`). A forgotten call silently returns the whole estate. Text-to-SQL over this schema would be a catastrophic data-exposure path for a platform holding government security data across 9 provinces and 113 provincial departments.

Additionally, three secrets-handling issues must be fixed **before** any AI work begins, because AI amplifies their blast radius:

- `backend/.env` contains live AppScan Cloud credentials in plaintext.
- `backend/certs/ag_signing_key.pem` — the **AG attestation private signing key** — is committed to the repository.
- `backend/new_credentials.txt` is a plaintext credential dump.

These are tracked as **Phase 0 (blocking gate)** in §8.

---

## 2. Current-state summary (evidence base)

This plan is grounded in the implemented system, not the requirements document.

### 2.1 Backend

| Area | Finding | Source |
|---|---|---|
| Stack | FastAPI 0.112, SQLAlchemy 2.0.31 async + asyncpg, Pydantic v2, python-jose HS256, Redis Streams, APScheduler 3.10 | `backend/requirements.txt` |
| Process topology | 5 containers from one image: `backend` (HTTP only), `ingestion`, `processing`, `dispatch`, `analytics` | `infrastructure/docker-compose.yml:31-98` |
| Data flow | connectors → Redis Stream `sita:ingestion:raw` → `processing` consumers → normalise → `warehouse.*` → alerts → `sita:processing:alerts` → `dispatch` | `app/bus/streams.py:1-6` |
| Risk model | Linear weighted sum, 4 signals, weights `0.35/0.25/0.20/0.20`; AppScan ceiling auto-calibrated at P99 | `app/processing/risk_engine.py:14,64-76` |
| Alert rules | 9 declarative YAML rules + aggregate rules | `app/processing/alert_rules.yaml` |
| Audit trail | **No helper function.** Written inline in exactly one place | `app/api/routers/exports_ag.py:209-221` |
| AG export | Aggregation-only attestation, SHA-256 integrity hash bound to actor+tenant, ECDSA-P256 signature | `app/api/routers/exports_ag.py:62-230`, `app/security_pki.py` |
| Tenancy | 4 denormalised columns per row (`department_id`, `branch_id`, `ministry_id`, `cluster_id`), resolved at write time from a static catalogue | `app/lake/writer.py:74-77` and 5 other sites |
| Config | `pydantic-settings`, no env prefix, `extra="allow"`, non-dev guard on JWT/bootstrap defaults | `app/config.py:48-59` |

**Zero** LLM/AI code, and **no** `pgvector` or vector extension anywhere in `infrastructure/scripts/*.sql`. This is greenfield.

### 2.2 Frontend

| Area | Finding | Source |
|---|---|---|
| Stack | React 18 + TypeScript (strict) + Vite 5, React Router 6, axios, DOMPurify | `frontend/package.json` |
| State | **No** Redux/Zustand/React Query. React Context + a hand-rolled `useApi` mini-cache | `frontend/src/hooks/useApi.ts:10-34` |
| Charts | **All hand-rolled** (CSS `conic-gradient`, flex bars). `recharts` is installed but never imported | `frontend/src/pages/ExecDashboard.tsx:121` |
| UI kit | 8 primitives in `components/dashboard/` + ~200 CSS classes in `global.css`. No design system | `frontend/src/components/dashboard/` |
| Auth | JWT in `localStorage['sita_token']`, Bearer interceptor on both axios instances | `frontend/src/api/client.ts` |
| Real-time | **None.** No SSE, no WebSocket, no polling in use (`usePolling` exists but is never imported) | — |
| Narrative surface | `ExplainOverlay` renders raw HTML through `DOMPurify.sanitize` — **model output is already safe to inject** | `frontend/src/components/dashboard/ExplainOverlay.tsx:17` |
| Mount point | `DashHeader` accepts `children` (already used for a `+ New User` button) → AI control on all 6 dashboards with **zero route changes** | `frontend/src/components/dashboard/DashHeader.tsx:36` |
| Tests | **No test runner at all** — no vitest/jest/playwright, no `test` script | `frontend/package.json:5-11` |

---

## 3. Hosting & model strategy

### 3.1 Decision

**Primary: self-hosted open-weights models served in-cluster by vLLM** (OpenAI-compatible `/v1` API), on a GPU node inside the SITA private cloud / on-prem environment. **DR: a sovereign-cloud endpoint** (Azure OpenAI or AWS Bedrock in an SA/sovereign region) reachable only if the primary is unavailable, with the same redaction gate applied.

Rationale: POPIA + government data-residency obligations make raw OEM payloads non-egressible. Self-hosting also removes per-token cost, which matters at the volumes this platform reaches (`processing_batch_size=100`, 4 consumers, `appscan_page_size=200`).

### 3.2 Two-tier model configuration

| Tier | Purpose | Model class | Latency budget | Deployment |
|---|---|---|---|---|
| **Reasoning** | Copilot query answering, narrative generation | 30–34B instruct, AWQ/GPTQ 4-bit | ≤ 20 s P95 | 1× 80 GB GPU (A100/H100/L40S), vLLM, continuous batching |
| **Fast** | Bulk finding triage (high volume, short output) | 7–8B instruct, quantised | ≤ 3 s P95 | Same node, second adapter, `--max-model-len 8192` |

Both must be **pinned by container digest**, not floating tags, so the model in production is reproducible for audit purposes. Embeddings: local bi-encoder (`bge-m3`, multilingual — the estate contains non-English app/asset names), served by the same vLLM process via the `/v1/embeddings` route.

### 3.3 Why not fine-tuning (yet)

Fine-tuning requires a labelled corpus and an eval harness. Neither exists. The accepted/rejected triage outcomes from Phase D generate the labels — fine-tuning becomes viable in Month 7+ only after ≥ 2 000 reviewed decisions. Everything in Phases A–D uses **prompted RAG + structured output**, which is reversible, auditable and cheap to change.

---

## 4. Target architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React)                                                     │
│  DashHeader children slot ──▶ AI toggle (all 6 dashboards, 0 routes)  │
│  ExplainOverlay ◀── AI Narrative tab (DOMPurify already in place)      │
│  CopilotDrawer (new CSS)  ◀── streaming via fetch + ReadableStream    │
│  TriageSuggestion  ◀── accept/reject                                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ Bearer JWT (axios client.ts)
┌───────────────────────────────▼──────────────────────────────────────┐
│  BACKEND — NEW MODULE  app/ai/                                        │
│                                                                       │
│  app/ai/config.py      prompt registry, model routing (fast|reasoning) │
│  app/ai/gateway.py     httpx → vLLM; retries, token budget,            │
│                        CIRCUIT BREAKER (reuse app/ingestion/          │
│                        circuit_breaker.py), structured output          │
│  app/ai/redaction.py   PII/OEM-payload scrubber — MANDATORY pre-egress │
│  app/ai/narrative/     fact-pack builder (pure) + narrative generator │
│  app/ai/copilot/       intent schema → allowlisted query compiler     │
│  app/ai/triage/        batch triage job + suggestion store            │
│  app/audit.py          record_audit()  ◀── NEW reusable audit helper  │
│                                                                       │
│  Routers (all POST — avoid demo-interceptor substring trap):          │
│  app/api/routers/copilot.py                                           │
│    POST /api/v1/copilot/narrative                                     │
│    POST /api/v1/copilot/query                                         │
│    PATCH /api/v1/copilot/triage/{finding_id}                          │
│  app/api/routers/ai_admin.py  (prefix /admin, admin_read/write)        │
│    GET/POST /admin/ai/config, /admin/ai/evals, /admin/ai/kill-switch  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ tenant_filter(claims, model) — ALWAYS
┌───────────────────────────────▼──────────────────────────────────────┐
│  DATA    warehouse.finding_triage (NEW, versioned)                    │
│          audit.action_audit (action="ai_*")                          │
│          Redis: narrative cache, conversation TTL, rate limits        │
│          pgvector extension (Phase C only)                           │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ private network, no external egress
┌───────────────────────────────▼──────────────────────────────────────┐
│  SELF-HOSTED MODEL SERVERS (new containers)                          │
│  vLLM (reasoning) + vLLM (fast) + bge-m3 embeddings                 │
│  infrastructure/docker-compose.llm.yml  ·  backend/k8s/llm-inference.yaml │
│  SOVEREIGN DR ENDPOINT (behind the same redaction gate)              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4A. Stage 4 placement — AI inside the SITA 6-stage model

The platform's own architecture taxonomy (`architecture.html:936-941`) defines six stages:

| Stage | Name | Path | AI role |
|---|---|---|---|
| 1 | OEM Ingestion | `connectors/` `ingestion/` | **None** — no AI on the ingestion path |
| 2 | Pipeline Processing | `processing/` `dispatch/` | **Advisory only** — triage runs out-of-band after the warehouse write |
| 3 | PostgreSQL Warehouse | `init-db.sql` `seed-demo.sql` | **Reads from** the warehouse (post-tenant-filter). Writes only `finding_triage` + audit |
| **4** | **REST API** | **`api/routers/`** | **AI report generation lives here** |
| 5 | Reports UI | `frontend/src/` | Consumes Stage-4 report JSON; renders it |
| 6 | Reports | `pages/` `data/` `grafana/` | Consumes Stage-4 report JSON; exports it |

### 4A.1 Why Stage 4 is the only correct insertion point

Stage 4 is the layer that already owns the three properties report generation requires:

1. **Tenant scoping.** `tenant_filter(claims, model)` lives at `app/api/auth.py:210` and every scoped query in the codebase is written in a router. AI report generation that queries the warehouse *must* live here, or it will re-implement tenancy badly somewhere with no enforcement.
2. **Read-only access to Stage 3.** The warehouse is fully normalised and aggregated by Stage 2. Report generation needs no writes beyond its own audit trail.
3. **The single contract point.** Stages 5 and 6 consume *only* what Stage 4 returns. Putting AI at Stage 5 would push a model call into the browser; putting it at Stage 2 would put a model in the ingestion hot path. Both are worse.

This also means **the AI never runs in the request path of the pipeline** — it is a synchronous, tenant-scoped, cacheable report service.

### 4A.2 Stage-4 file layout

```
backend/app/api/routers/reports_ai.py     ◀── Stage 4 surface (the router)
backend/app/ai/
  __init__.py
  config.py            prompt + model registry, routing (fast|reasoning), version pinning
  gateway.py           httpx → vLLM; CircuitBreaker reuse; retries; token budget
  redaction.py         PII scrubber — mandatory pre-egress gate
  context.py           pure fact-pack builder (unit-testable without a DB)
  generate.py          prompt assembly → generation → numeral verification → fallback
  templates/
    executive_briefing.yaml
    soc_shift_handover.yaml
    appsec_posture.yaml
    dbsec_posture.yaml
    compliance_status.yaml
    department_monthly.yaml
    peer_benchmark.yaml
    ag_attestation.yaml
  verify.py            numeral-fidelity verifier (primary hallucination control)
```

Prompts are **YAML in git**, versioned and reviewed like code (NFR-AI-09), matching the existing `alert_rules.yaml` / `field_mapper.yaml` convention already used by Stage 2.

### 4A.3 Report catalogue

Eight report types, each with a prompt template, a role gate and a tenant scope:

| `report_type` | Persona / audience | Scope | Stage 4 permission | Notes |
|---|---|---|---|---|
| `executive_briefing` | exec, transversal-admin | province or estate | `require_roles("dashboard")` | Feeds the exec dashboard AI tab |
| `soc_shift_handover` | soc, province-soc-lead | tenant-filtered | `require_roles("alerts_read")` | Alert backlog, MTTD/MTTR, open criticals |
| `appsec_posture` | appsec, local-appsec | tenant-filtered | `require_roles("findings")` | Severity mix, shadow APIs, fix rate |
| `dbsec_posture` | dbsec | tenant-filtered | `require_roles("findings")` | Inventory coverage, DAM findings |
| `compliance_status` | compliance | **estate-wide — flagged unscoped** | `require_roles("compliance")` | `ComplianceSnapshot`/`ComplianceGap` have no tenancy columns; the narrative MUST say so |
| `department_monthly` | dept-admin, province-dept-admin | single department | `require_roles("dashboard")` | Month-over-month movement |
| `peer_benchmark` | exec, compliance | province + anonymised peers | `require_roles("dashboard")` | Reuse `benchmark.py:_build_benchmark` |
| `ag_attestation_narrative` | compliance, admin | tenant-filtered | `require_roles("compliance", "admin_write")` | Embedded into `build_attestation`, inherits the SHA-256 + ECDSA chain |

### 4A.4 Endpoint contract

All routes are `POST` under `/api/v1/reports/…` — deliberately avoiding `GET` paths containing `/findings`, `/metrics`, `/risks`, `/compliance`, `/dashboard` or `/public/summary`, which `frontend/src/api/demoInterceptor.ts:34-42` silently hijacks in demo mode.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/reports/generate` | Generate a report. Body: `{report_type, period?, format: narrative\|html\|markdown, force_refresh?}` |
| `GET` | `/api/v1/reports/templates` | List report types, prompt versions, model ids — for the admin UI |
| `GET` | `/api/v1/reports/{report_id}` | Retrieve a generated report (Redis cache or `audit.action_audit` replay) |
| `POST` | `/api/v1/reports/{report_id}/regenerate` | Bust the cache and regenerate with the same fact pack |
| `GET` | `/api/v1/reports/grounding/{report_id}` | The exact fact pack the narrative was written from — transparency + audit |

`generate` returns a **self-describing envelope** so Stage 5/6 never has to guess provenance:

```json
{
  "report_id": "…",
  "report_type": "executive_briefing",
  "narrative_html": "<h3>…</h3>…",
  "grounding_hash": "sha256:…",
  "scope": { "type": "province", "provinces": ["gauteng"], "departments_count": 13 },
  "model": { "id": "qwen2.5-32b-instruct-awq", "digest": "sha256:…", "prompt_version": "exec_briefing.v3" },
  "generated_at": "2026-11-19T09:14:22Z",
  "latency_ms": 6120,
  "verification": { "numerals_checked": 47, "ungrounded": 0, "passed": true },
  "fallback_used": false,
  "data_disclosure": ["compliance figures are estate-wide and not tenant-scoped"]
}
```

`data_disclosure` is **not optional** — the compliance limitation in §4A.3 must travel with the payload so the UI cannot accidentally present estate-wide figures as department-scoped.

### 4A.5 Prompt contract

Every template in `templates/` has four fixed sections. Keeping these uniform is what makes the eval harness (§7) possible:

```yaml
report_type: executive_briefing
version: 3
model_tier: reasoning          # fast | reasoning
system: |
  You are a security posture analyst writing for a South African government
  executive audience. State only figures present in the FACTS block.
  If a required figure is absent, write "not tracked in this build" — never estimate.
input:
  facts_from: context.build_executive_context   # pure function, Stage 3 reads
  max_tokens: 1200
  temperature: 0.2             # low: this is reporting, not creative writing
constraints:
  - Do not invent figures.
  - Do not name a department outside the SCOPE block.
  - Do not state a remediation is complete unless FACTS.status confirms it.
  - Attribute compliance figures as estate-wide when the compliance block is present.
output:
  schema: narrative_html          # constrained decode; <h3>/<ul>/<li> only
```

`temperature: 0.2` is deliberate — narrative reporting needs reproducibility, not variety. Variety belongs in the copilot (Phase C), not the briefing.

### 4A.6 What Stages 5 and 6 consume

- **Stage 5 (Reports UI):** `frontend/src/api/reports.ts` (new axios module importing the existing `client.ts`), `useReport<T>()` hook, and a new `ReportPanel.tsx` that renders `narrative_html` through the **existing** `ExplainOverlay` (which already runs `DOMPurify.sanitize`, `ExplainOverlay.tsx:17`). Mounted via the `DashHeader` `children` slot (`DashHeader.tsx:36`) — no route changes, no new component library.
- **Stage 6 (Reports):** `regenerate` and CSV/PDF export of generated reports; Grafana stays numeric-only (Grafana cannot call an LLM — it must not be given a model endpoint).

### 4A.7 Updating `architecture.html`

The diagram is interactive: `stage-btn[data-stage]` → `render(key)` → `details[key]` panel + `FLOW_STAGE` mapping + `BACKEND_STAGES` highlighting (`architecture.html:2383-2442`). To surface the AI node at Stage 4:

1. Insert after line 963 (the REST API node):
   ```html
   <span class="flow-arrow">&rarr;</span>
   <span class="flow-node" data-flow="ai" data-stage="api" data-fw="bk"><span class="fn-name">AI Report Generation</span><span class="fn-path">backend\app\api\routers\reports_ai.py + backend\app\ai\</span><span class="fn-fw bk">backend</span><span class="fn-stage">Stage 4</span></span>
   ```
2. Add `ai: 'api'` to `FLOW_STAGE`.
3. Add an `ai` entry to the `details` object (title, badge, body — reuse the security-property framing already used at line 748).
4. Add `'ai'` to the `STAGES` array so `highlightStage()` fires.
5. Add `'ai'` to `BACKEND_STAGES` in `highlightFramework()` (line 2410) so the backend-framework modal highlights.
6. Add a `data-key="ai"` span in the repo tree (`<pre>` block starting line 974).

> **Gotcha:** `architecture.html` exists in **two** places — `C:\sita-platform\architecture.html` **and** `C:\sita-platform\frontend\public\architecture.html`. They are currently byte-identical. Any change must be applied to **both** or they will drift, and only the `frontend/public` copy is actually served by the app. A CI check asserting the two files match is worth adding in Phase 0.

---

## 5. The tenancy rule (non-negotiable)

> **The model must never generate SQL, and must never receive a row that has not passed through `tenant_filter(claims, model)`.**

Why this is absolute:

1. `tenant_filter` (`app/api/auth.py:210-244`) is **opt-in** — there is no middleware. Omit it and you leak the whole estate.
2. The JWT carries the scope; it is **not re-derived from the DB per request**, so any divergence between token issue time and now is inherited by every query.
3. `tenant_filter` requires `department_id` and `branch_id` on the model. It raises `AttributeError` on `ComplianceSnapshot`, `ComplianceGap`, `SystemMetric`, `SloMetric`, `Agent` — which is why the compliance endpoints are simply unscoped. **AI must not silently imply tenant scoping for compliance data.**

### 5.1 Copilot query architecture (Phase C)

```
user question
    ↓
LLM #1  →  JSON Schema-constrained intent       (no free text output)
           { entity, filters{severity,source,app,category,status,
            date_range,department,province}, agg{type,group_by,top_n},
            time_range }
    ↓
DETERMINISTIC COMPILER  →  SQLAlchemy Core expressions
           • field names map to an explicit ALLOWLIST (no dynamic attrs)
           • every enum value validated against Severity/AlertStatus/RiskBucket
           • date range bounded to ≤ 400 days
           • top_n ≤ 50, hard row cap 200
    ↓
scope = tenant_filter(claims, model)            ◀── INJECTED BY CODE, NOT PROMPT
    ↓
compiled_query = scope.apply_to(constructed)   ◀── scope cannot be omitted
    ↓
execute → aggregate (k-anonymity floor 5) → redact → LLM #2 → prose answer
                                                 + cited finding IDs
                                                 + the executed query plan shown to user
```

The model proposes *what to look for*; the code decides *what it is allowed to see*. The `tenant_filter` call is a straight-line statement in our code, not an instruction in a prompt.

### 5.2 K-anonymity and redaction

- Aggregate results returned to the UI are suppressed below a cohort of 5 (`Peer Province A` behaviour already exists in `benchmark.py:46-160` — reuse `_build_benchmark` as the structural template).
- `Finding.raw_data` (`app/models/finding.py:34`) is the full OEM payload and is the single largest PII risk. It **never** reaches the model raw. `app/ai/redaction.py` strips emails, ID numbers, request bodies, query strings, and OAuth/JWT material, and records what it stripped in the audit row.
- Conversation memory lives in Redis keyed by `(actor, tenant_scope_hash)` with a TTL — no cross-tenant bleed is structurally possible.

---

## 6. Capability designs

### 6.1 Phase B — Narrative reporting & executive briefings

**Why first:** read-only, grounded, and it lands in the artefact you already have to produce — the AG attestation (`exports_ag.py`). It is the fastest visible win and the lowest risk.

**Pipeline:** a **pure** fact-pack builder produces a bounded JSON context; the LLM writes prose from it; every number in the output must be traceable to the fact pack.

```python
# app/ai/narrative/context.py — pure function, unit-testable without a DB
def build_narrative_context(
    role: str,                 # exec | soc | appsec | dbsec | compliance
    scope_meta: dict,          # {type, provinces, departments}
    summary: dict,             # from dashboard.py
    risk_rows: list[dict],     # post-tenant_filter
    findings_summary: dict,    # counts by severity/category/source
    compliance: dict | None,   # estate-wide — flagged as unscoped
) -> dict:
    ...
```

- Fact pack is **capped** (top-N apps, severity counts, deltas) — the context is a fact sheet, not a data dump.
- Prompt instructs: *"State only figures present in the input. If a figure is absent, say so."*
- **Post-generation verifier** re-extracts every numeral from the generated prose and asserts it exists in the fact pack. A failure discards the output and falls back to the deterministic template. This is the primary hallucination control.

**Signature & audit:** reuse `canonical_json` + `sha256_hex` + `sign_canonical_payload` from `exports_ag.py:48-59` / `app/security_pki.py:84-91`. The narrative is embedded into `build_attestation` output between `risk_profile` and `scope`, so it inherits the existing integrity hash, ECDSA signature and `verify_url`. One new `ActionAudit` row per generation with `action="ai_narrative_generated"`.

**Frontend:** new `src/api/copilot.ts` + `src/hooks/useNarrative.ts`. AI output becomes a **third tab** in `ExplainOverlay` alongside `buildExplain`/`buildLayman` — zero changes to `ExplainOverlay`, `DashHeader` or any page's overlay plumbing. Redis-cached per `(role, tenant_scope, fact_pack_hash)`; a `Regenerate` button busts the cache.

**Degradation:** LLM down → the existing static `buildExplain` output renders. The dashboard is never blank.

### 6.2 Phase D — Finding triage & severity assist

**Runs out-of-band**, after the normaliser and warehouse write, never inside the hot ingestion path. A slow LLM must not stall `processing` consumers.

```python
# app/ai/triage/prompt.py
# inputs: redacted raw_data excerpt, title, description, category,
#         app_catalog tier + owner, historical severity distribution for the app
# JSON-schema output:
# { suggested_severity, cwe_id, exploitability: low|med|high,
#   confidence: 0..1, rationale, requires_human_review }
```

**Hard rules:**
- **AI never mutates `warehouse.findings.severity`.** The suggestion is advisory; a human accepts or rejects. For a platform whose scores are AG-audited, an autonomous severity change is indefensible.
- Suggestions below a confidence floor (default 0.7) are not surfaced at all.
- Every suggestion and every accept/reject decision is written to `warehouse.finding_triage` and `audit.action_audit`.

**Schema:** a **new table**, not a new column on `findings`. Your own plan file flags `warehouse.findings` row-width/TOAST bloat as an open risk (`plan_dump.txt:51`) — adding a JSON triage blob to the same row worsens it. A separate versioned table also gives free history and rollback.

```sql
CREATE TABLE warehouse.finding_triage (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id varchar(36) NOT NULL REFERENCES warehouse.findings(id),
  department_id varchar(36), branch_id varchar(36),
  model_id varchar(100) NOT NULL,
  prompt_version varchar(20) NOT NULL,
  suggested_severity varchar(20), cwe_id varchar(20),
  exploitability varchar(10), confidence numeric(4,3),
  rationale text, requires_human_review boolean NOT NULL DEFAULT true,
  decision varchar(20),            -- NULL | accepted | rejected
  decided_by varchar(255), decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (finding_id, prompt_version)
);
CREATE INDEX ON warehouse.finding_triage (department_id, created_at DESC);
CREATE INDEX ON warehouse.finding_triage (decision, confidence);
```

**Feedback loop:** accepted/rejected decisions are the labelled dataset. After ≥ 2 000 decisions, evaluate a small classifier (or a LoRA adapter) against the LLM baseline — that is the Month 7+ conversation, and it is the honest answer to "does the AI actually beat the rules".

### 6.3 Phase C — Analyst copilot

Described in §5.1. Additional requirements:

- **Streaming** requires backend SSE (`StreamingResponse` + `text/event-stream`) and an nginx fix. `frontend/nginx.conf` currently has no `proxy_buffering off;`, no `proxy_cache off;` and no `proxy_read_timeout`. **Without this, streaming works in dev and silently breaks in production** — because Vite's dev proxy does not buffer. Fix both `nginx.conf` and `infrastructure/nginx/` in the same phase.
- Frontend must use raw `fetch()` + `ReadableStream.getReader()` (axios XHR cannot stream) and attach the Bearer header by hand — `client.ts` interceptors do not apply to `fetch`.
- **Route naming:** all copilot routes are `POST` under `/api/v1/copilot/...`. `api/demoInterceptor.ts:34-42` silently injects a demo tenant parameter into any GET whose path contains `/findings|/metrics|/risks|/compliance|/dashboard|/public/summary` — a GET `/copilot/findings` would be quietly hijacked in demo mode.
- **Kill switch:** `SITE_AI_ENABLED` plus a per-role allowlist at `/admin/ai/config`, so AI can be switched off for a tier without a deploy.

---

## 7. Cross-cutting requirements

| ID | Requirement | Target | Verification |
|---|---|---|---|
| NFR-AI-01 | Narrative P95 latency | ≤ 8 s cached, ≤ 20 s cold | Prometheus `llm_request_duration_seconds` |
| NFR-AI-02 | Copilot query P95 latency | ≤ 15 s | same |
| NFR-AI-03 | Triage throughput | ≥ 200 findings/min sustained | batch job metrics |
| NFR-AI-04 | Narrative numeral-fidelity | 100 % — any ungrounded figure discards the output | eval suite, CI gate |
| NFR-AI-05 | PII leak rate | 0 across the redactor corpus | CI gate, synthetic PII corpus |
| NFR-AI-06 | Cross-tenant leak rate | 0 — scope-escape test suite | CI gate |
| NFR-AI-07 | Availability | AI failure must not degrade any dashboard | fault-injection test |
| NFR-AI-08 | Model reproducibility | model + prompt + template pinned by digest/version | recorded in every audit row |
| NFR-AI-09 | Prompt inventory | every prompt versioned in git, reviewed like code | `app/ai/config.py` registry |
| NFR-AI-10 | Human oversight | every AI recommendation traceable to a named decider | `audit.action_audit` |

**Observability:** new Prometheus collectors `llm_requests_total{model,capability,outcome}`, `llm_request_duration_seconds`, `llm_tokens_total`, `llm_circuit_state`, plus a Grafana panel. `setup_metrics()` (`app/monitoring/metrics.py`) is currently a no-op stub — wire it up as part of this phase.

**Configuration** — new block in `app/config.py`, with the existing non-dev guard extended:

```python
llm_enabled: bool = False
llm_base_url: str = "http://vllm-reasoning:8000/v1"
llm_fast_base_url: str = "http://vllm-fast:8000/v1"
llm_model: str = ""
llm_fast_model: str = ""
llm_embedding_model: str = ""
llm_api_key: SecretStr = SecretStr("")     # vLLM auth, even internal
llm_timeout_seconds: int = 60
llm_max_context_tokens: int = 16384
llm_max_output_tokens: int = 1024
llm_max_rows_per_query: int = 200
llm_min_cohort_size: int = 5
llm_triage_confidence_floor: float = 0.70
```

Extend `_guard_non_dev_defaults` (`app/config.py:48-59`) so a non-dev environment with `llm_enabled=True` but no `llm_base_url`/`llm_model`, or any non-loopback `llm_base_url` pointing off-cluster, fails at startup. Use `SecretStr` — the existing plain-`str` secret fields are the root of the `.env` problem.

---

## 8. Phase 0 — blocking governance gate

**These must complete before any model is deployed.** They are not AI features; they are the reason AI features are currently unsafe to add.

| ID | Item | Evidence |
|---|---|---|
| P0-1 | Rotate AppScan Cloud credentials; purge `backend/.env` from tracking; confirm not in git history | `backend/.env` (live creds) |
| P0-2 | Rotate the AG ECDSA signing key; remove `certs/ag_signing_key.pem` from the repo; move to env/HSM | `app/security_pki.py:44-50` |
| P0-3 | Delete `backend/new_credentials.txt` | plaintext dump |
| P0-4 | Add `record_audit()` in `app/audit.py`; call it from every privileged mutation (alert ack/resolve, user CRUD, connector reset) — none are audited today | `app/api/routers/exports_ag.py:209` is the only audit write |
| P0-5 | Add a DB trigger making `audit.action_audit` genuinely immutable (currently nominal only) | `infrastructure/scripts/init-db.sql:120-130` |
| P0-6 | Add a startup self-test that enumerates registered routes and asserts every data-returning route calls `tenant_filter` | no enforcement exists |
| P0-7 | Consolidate the three conflicting risk-bucket implementations into one module | `exports_ag._bucket` (45/70), `risk_engine.risk_bucket` (30/70), `benchmark._bucket` — narratives must not inherit this ambiguity |
| P0-8 | Fix `verify_token` to re-read user state so role changes and deactivation take effect without a re-login | `app/api/auth.py:52-73` |
| P0-9 | Remove `GET /admin/ipinfo` — an **unauthenticated** proxy to an external service. This is a live egress path | `app/api/routers/admin.py:571-572` |
| P0-10 | Refresh `openapi.json` at repo root — it is stale (missing `/health/detailed`, `/admin/ipinfo`, `/admin/hr/sim/*`) | `openapi.json` |

P0-9 deserves emphasis: if that endpoint is reachable in production, "no data leaves the environment" is not currently true of the platform — regardless of what we do about AI.

---

## 9. Effort, sequencing and owners

Dates assume a start of **2026-10-12** and align to the existing owner set from `plan_dump.txt`.

| Phase | Weeks | Calendar | Owner | Track |
|---|---|---|---|---|
| **0 — Governance gate** | 1 | Oct 12–16 | Lead Dev + DevOps | Blocking |
| **A — AI platform foundation** | 3 | Oct 19–Nov 6 | Lead Dev + DevOps | Blocking |
| **B — Narrative & briefings** | 4 | Nov 9–Dec 4 | Lead Dev | Capability 1 |
| **D — Triage assist** | 5 | Dec 7 – Jan 8 | Data Engineer + Data Scientist | Capability 3 |
| **C — Copilot** | 6 | Jan 11 – Feb 19 | Lead Dev + Data Architect | Capability 2 |
| **E — Risk 5th signal (EPSS/KEV)** | 3 | Feb 22 – Mar 12 | Data Scientist | Enhancement |
| **F — Assurance & AG reporting** | 2 | Mar 15–26 | Compliance Analyst + Data Scientist | Governance |

Phases B and D can overlap from week 8 — they touch different tables and different routers. Phase C must not start before P0-6 (route/tenancy self-test) lands, because it is the phase that depends on tenant scoping being provably correct.

> **Sequencing note against your plan file:** `plan_dump.txt:56` records "Risk: RTO ~30min does not meet SLA (target <15min)" and `:45` records "Risk: static weights fail to capture 0-day urgency → Future: CVE EPSS score as 5th signal (+0.10 weight shift from Sa)". **Phase E is that EPSS work**, pulled forward into the AI programme. Phase 0 addresses the third such risk (ingestion/RPO) only partially — the 30-minute RTO needs a Patroni decision that remains a business call, not a technical one.

### 9.1 Team shape

| Role | Allocation | Notes |
|---|---|---|
| Lead Dev | 0.6 FTE | Router, gateway, tenancy enforcement |
| Data Engineer | 0.5 FTE | Triage table, batch job, EPSS ingest |
| Data Scientist | 0.4 FTE | Eval harness, confidence calibration, risk signal |
| DevOps | 0.3 FTE | GPU node, vLLM, nginx, monitoring |
| Compliance Analyst | 0.2 FTE | POPIA/ISO mapping, AG disclosure |
| **New: MLOps engineer** | **0.5 FTE (Months 1–4)** | Model serving, eval CI, drift. Currently no one on the team owns this — see Risks |

### 9.2 Budget lines requiring approval

| Item | Estimate |
|---|---|
| GPU node (1× 80 GB, or a sovereign-cloud A100-equivalent on demand) | New CAPEX/OPEX line |
| Sovereign-cloud DR endpoint (idle, DR-only) | ~R 3–6k/month |
| MLOps engineer, 4 months | ~R 180–260k loaded |
| Eval corpus construction (2 000 labelled findings) | Data Engineer + Data Scientist time |
| **No per-token API cost** | Self-hosted |

---

## 10. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-AI-1 | **Cross-tenant data leak via the copilot** | Medium | Severe | §5 architecture; P0-6 route self-test; scope-escape CI suite; k-anonymity floor |
| R-AI-2 | **Hallucinated figures in an AG-audited narrative** | Medium | Severe | Numeral-fidelity verifier + deterministic fallback + signature chain (§6.1) |
| R-AI-3 | Model unavailable / GPU failure at scale event | Medium | Medium | Circuit breaker reuse, deterministic fallback, two-tier routing, sovereign DR |
| R-AI-4 | Analysts over-trust triage suggestions | High | High | Confidence floor; advisory-only (never mutates severity); accept/reject logged and fed back |
| R-AI-5 | No MLOps capability on the team | High | Medium | Hire/contract Month 1; otherwise Phase C slips |
| R-AI-6 | Sovereign-cloud DR endpoint becomes a data-egress path under pressure | Low | Severe | Same redaction gate on the DR route; egress allow-list at the network layer |
| R-AI-7 | GPU CAPEX not approved | Medium | High | Re-scope to 7-8B single tier; narrative + triage still ship |
| R-AI-8 | Prompt drift after model upgrade silently degrades quality | High | Medium | Model+prompt pinned by digest/version; eval suite in CI as a release gate |
| R-AI-9 | Inference cost/latency spikes on large estates | Medium | Medium | Row/token caps, Redis narrative cache, fast tier for triage, batch not interactive |
| R-AI-10 | Phase 0 exposes pre-existing security debt with no owner/date | **High** | Severe | Escalate P0-1…P0-10 as named, dated tasks **before** approving AI spend |

---

## 11. Explicit non-goals

Stated so they are not quietly added later:

1. **No free-form text-to-SQL, ever.** Intent schema + allowlisted compiler only.
2. **No autonomous change to finding severity, risk scores, or alert suppression.**
3. **No AI inside the ingestion or dispatch hot path.**
4. **No fine-tuning before the eval harness and ≥ 2 000 labelled decisions exist.**
5. **No raw `Finding.raw_data` to any model, hosted or self-hosted.** Redaction is a hard gate.
6. **No AI output entering the AG attestation without passing the numeral-fidelity verifier and the ECDSA signature chain.**
7. **No SaaS LLM API.** Sovereign cloud only, DR-only, behind the redaction gate.

---

## 12. Acceptance criteria

- [ ] P0-1…P0-10 complete and evidenced; `GET /admin/ipinfo` removed.
- [ ] `llm_enabled=True` in a non-dev environment starts only with a cluster-local `llm_base_url` and pinned model digest.
- [ ] An executive dashboard shows an AI narrative tab; every figure in it is traceable to the fact pack; the numeral verifier is green.
- [ ] Killing the vLLM container leaves all 6 dashboards fully functional with the static fallback.
- [ ] Copilot answers a cross-tenant probe ("show findings in KwaZulu-Natal") from a `dept`-scoped user with **zero** rows outside scope, and the executed query plan is displayed to the user.
- [ ] No suggestion with confidence < 0.70 is rendered.
- [ ] Accepting a triage suggestion writes `warehouse.finding_triage.decision='accepted'` **and** an `audit.action_audit` row with the actor and the model/prompt version.
- [ ] An AI-generated narrative embedded in the AG attestation verifies via `GET /api/v1/exports/ag-compliance/verify/{hash}`.
- [ ] The redaction corpus shows 0 PII egress; the scope-escape suite shows 0 leaks.
- [ ] Grafana shows `llm_*` metrics per model, capability and outcome.
- [ ] Backend `pytest` passes; frontend `npm run lint` and `npm run typecheck` pass.

---

## 13. Open decisions required

| # | Decision | Owner | Needed by |
|---|---|---|---|
| 1 | Approve GPU node (CAPEX) or sovereign-cloud-only (OPEX)? | Sponsor / PM | Before Phase A |
| 2 | Fund the 0.5 FTE MLOps engineer? | PM | Before Phase A |
| 3 | Is AI output permitted inside an AG attestation at all, or must it be advisory-only? This changes Phase B's design | Compliance + AG liaison | Before Phase B |
| 4 | Accepted/rejected triage decisions — is a model trained on them a "decision" requiring its own POPIA/AI-governance approval? | Compliance Analyst | Before Phase D |
| 5 | Which sovereign-cloud region/provider is acceptable for the DR endpoint? | DevOps + Compliance | Before Phase C |
| 6 | Does Phase 0's revealed security debt change the go-live date? | PM | Immediate |

---

*Companion deliverable: `docs/G1_AI_Integration_Plan_Rows.csv` — Month 4+ activities in the delivery-plan column schema, ready to paste into the HOSI-UNIFIED plan.*