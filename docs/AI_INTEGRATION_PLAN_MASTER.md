# SITA Platform — AI Integration Master Plan

**Document ID:** AI-MASTER-R1 · **Prepared:** 6 October 2026
**Status:** Master. **Supersedes `G1_AI_Integration_Plan.md` and `G2_AI_Report_Generation_Plan.md`** in full. Those two documents remain as their dated originals and contain material this plan corrects.
**Builds on:** `05` G2-ARCH-R1 · `06` G2-ADR-R1 · `07` G2-EXEC-PLAN-R1 (in `docs/G2_POC_2026-10-15/`)
**Baseline commit:** `57e080d` · **Verification method:** code read + live database + live HTTP

---

## 1. Executive summary

The platform ingests, normalises and fuses security telemetry from four OEM sources into a PostgreSQL warehouse and serves six role-scoped dashboards. The AI workstream adds a **self-hosted LLM capability** in five capabilities plus a governance gate, ordered so that the highest-value, lowest-risk capability ships first and each phase de-risks the next.

| # | Capability | Risk | Weeks | Status |
|---|---|---|---|---|
| **POC** | RBAC-guided prompting agent — 2 report types, proven | — | 1 | **In build 7–14 Oct · demo 15 Oct** |
| **13.2** | Vector retrieval design — complete, deferred pending gate V8 | Medium | — | Design ready |
| **0** | Governance gate — **corrected, 3 items closed as never-committed** | Blocking | 1 | Ready |
| **A** | AI platform foundation — gateway, redaction, eval harness, metrics | Blocking | 3 | Planned |
| **B** | Narrative & briefings — remaining 6 report types, cache, UI | Low | 4 | Planned |
| **D** | Finding triage assist — advisory only | Medium | 5 | Planned |
| **C** | Analyst copilot — NL query, allowlisted compiler | High | 6 | Planned |
| **E** | Risk 5th signal (EPSS/KEV) | Medium | 3 | Planned |
| **F** | Assurance & AG reporting | Low | 2 | Planned |

**Total: 24 weeks from 19 October 2026**, after the POC.

**The three claims this programme is built on:**

1. **The model never generates SQL and never receives a row that has not passed `tenant_filter()`.** Not as a policy — as a structural property: accessors take scope as a mandatory first positional argument, enforced by signature-inspection test S6.
2. **The prompt is not the control.** The prompt *states* the restriction; the verifier *enforces* it, independently, and any failure returns a deterministic template — never model text.
3. **Tenancy containment, default-deny, typed disclosure and numeral fidelity are provable without a model.** Layers 1, 2 and 4 of the architecture contain no inference call. A missing or failed model degrades narrative *quality* and changes no security property.

**The programme's most serious open finding is not about AI.** `GET /admin/ipinfo` (`backend/app/api/routers/admin.py:571-584`) is an **unauthenticated outbound HTTPS proxy** to `ipapi.co`. While it exists, "no security data leaves the environment" is not true of the platform regardless of what the AI workstream does. It is Phase 0 item 1.

---

## 2. Corrections to the prior plans

G1 and G2 were both drafted 5 October. Both are good documents that have since been tested against the live system, and several of their claims did not survive. **This section is the highest-value part of this plan**; the corrections are load-bearing.

### 2.1 Corrections that change the design

| # | Prior claim | Source | Verified reality | Consequence |
|---|---|---|---|---|
| **C1** | Self-hosted **vLLM on a 1×80 GB GPU**, two tiers (30–34B reasoning + 7–8B fast), CAPEX required | G1 §3.1–3.2 | **Ollama 0.35.1 is installed and running** (PID 27452, `localhost:11434`). `qwen2.5:3b` fits the host: i5-11400H 6-core, **no GPU**, 15.6 GB RAM, 84.3 GB free | **Ollama/CPU now; vLLM deferred to a Phase C scale decision.** R01 (GPU CAPEX, Critical 16) does not apply to the POC. Zero CAPEX, zero procurement lead time |
| **C2** | `tenant_filter()` **raises `AttributeError`** on compliance tables | G1 §5, G2 §2 | **It raises only for scoped callers**, who are denied the report at Gate 1 anyway. Nationwide callers short-circuit to `None` **before** touching `model.department_id` — `app/api/auth.py:238-241` — so they receive the **full table silently** | The failure mode is **inverted**. For the intended audience it is a silent, total bypass of 684 rows, not a crash. Typed disclosure is therefore the *only* control, not a mitigation |
| **C3** | "**11 roles**" | G1/G2 | `ROLES_HIERARCHY` defines **14** (`app/api/auth.py:21-36`) | A suite hardcoded to 11 passes while missing three roles. S1 must enumerate from the dict |
| **C4** | "Estate risk is 62, critical exposure concentrated in 4 applications" as example `exec` output | G2 §6 | **Live: max `fused_score` 25.2, avg 7.46, all 15 283 rows bucket `safe`, `critical` bucket empty** | A prompt seeded with 62 hallucinates 62. Prompt examples and the eval set **must** be rebuilt from live fact packs before any quality claim |
| **C5** | Non-interference: *"nothing existing modified"* | G2 §0, §1, `01` §3 | `app/main.py:122-133` is the **only** router registration point. One `include_router` line is unavoidable | Restate the claim precisely (ADR D-A8): **one added line, zero deletions, nothing in `app/api/`, `app/processing/`, `app/tenant.py`, `app/models/` or the frontend**. A sweeping claim fails on a projector |
| **C6** | 8 / 7 report types | G1 §4A.3 / G2 §5 | Catalogue of 8 is correct; the **POC delivers 2** | Keep 8 as the target; state the POC scope honestly |
| **C7** | Verifier = numeral fidelity only | G1 §6.1 | Insufficient. Roles may request a report but not see everything in it | **Four checks:** numeral fidelity, claim class, scope containment, attribution. The claim filter is what makes role-aware prompting safe |

### 2.2 Corrections to the governance gate — the gate is smaller than G1 claims

G1 §8 states that `backend/.env`, `backend/certs/ag_signing_key.pem` and `backend/new_credentials.txt` are *committed to the repository*, and lists purging them as blocking items P0-1, P0-2, P0-3.

**Verified 6 October 2026 against the full git history of every branch:**

```
git log --all -- backend/.env                            → never committed
git log --all -- backend/certs/ag_signing_key.pem        → never committed
git log --all -- backend/new_credentials.txt             → never committed
git ls-files  (pattern: .env|certs/|credentials|.pem)    → empty
```

All three are **gitignored** (`.gitignore`: `.env`, `.env.*`, `backend/new_credentials.txt`) and none has ever been tracked. **P0-1, P0-2 and P0-3 are closed as not-applicable.** No credential rotation is required on the evidence; the practice is already correct.

This materially changes Phase 0. R-AI-10 ("Phase 0 exposes pre-existing security debt with no owner") is **downgraded** — the gate is six items, not ten, and it can be completed in one week.

### 2.3 Corrections to Phase 0 items that remain open

| ID | Item | Verified status 6 Oct 2026 |
|---|---|---|
| **P0-1** | Remove `GET /admin/ipinfo` — unauthenticated egress | **OPEN — confirmed real.** `app/api/routers/admin.py:571-584`. Signature takes only `session: AsyncSession = Depends(get_session)` — **no auth dependency** — and issues a live `https://ipapi.co/json` request. This is the single item that makes the platform's own data-residency claim untrue |
| **P0-2** | `audit.action_audit` immutability | **OPEN — confirmed nominal only.** `infrastructure/scripts/init-db.sql:120-130` is `CREATE TABLE` plus two indexes. No trigger, no `RULE`, no `REVOKE`. Append-only by convention |
| **P0-3** | Reusable `record_audit()` helper | **OPEN.** The only audit write in the codebase is inline at `app/api/routers/exports_ag.py:209-221`. Alert ack/resolve, user CRUD and connector reset are unaudited |
| **P0-4** | Route self-test: every data-returning route calls `tenant_filter` | **OPEN.** No enforcement exists. `app/ai/capability.py` (POC, task T08) is a partial preview of this and should be generalised in Phase A |
| **P0-5** | Consolidate the three risk-bucket implementations | **OPEN — confirmed divergent.** `risk_engine.py:78` (safe ≤30) vs `exports_ag.py:40` and `benchmark.py:38` (both safe <45). They disagree for scores in **30.0–44.9**. Verified live: **0 rows** currently in that band, so it is latent. The POC adds a tripwire test (task **T33**) that makes it detected; consolidation happens here in Phase 0 |
| **P0-6** | `verify_token` re-reads user state so deactivation/role change takes effect | **OPEN.** `app/api/auth.py:52-73` trusts the JWT. A revoked admin remains admin until token expiry (12 h default) |

**Phase 0 = P0-1 … P0-6. Six items, one week, blocking.**

---

## 3. Verified current state

### 3.1 Environment

| Item | Value |
|---|---|
| Database | PostgreSQL 18.1, `localhost:5432`, db `sita` |
| Backend | `backend/.venv` Python 3.13, FastAPI 0.112, SQLAlchemy 2.0 async + asyncpg, Pydantic v2, python-jose HS256 |
| **LLM runtime** | **Ollama 0.35.1 — installed and running**, PID 27452, port `11434` |
| Models installed | **0 — `qwen2.5:3b` (~2.0 GB) is pulled on POC day 1** |
| Host | Intel i5-11400H, **6-core, no GPU** · 15.6 GB RAM · 84.3 GB free |
| Docker | Unavailable (daemon down) — native PostgreSQL used |
| Frontend | Vite + React 18 + TS strict, six role dashboards, **no test runner** |
| CI | `.github/workflows/ci.yml` — `ruff check backend/`, `pytest backend/tests`, `npm run lint`, `npm run build` |

### 3.2 Data inventory

| Table | Rows | Scopable | Use |
|---|---:|:---:|---|
| `warehouse.risk_scores` | 15 283 | ✅ | narrative |
| `warehouse.waf_blocks` | 3 569 | ✅ | — |
| `warehouse.api_endpoints` | 2 752 | ✅ | — |
| `warehouse.database_inventory` | 2 577 | ✅ | — |
| `warehouse.findings` | 2 244 | ✅ | narrative |
| `warehouse.alerts` | 551 | ✅ | triage |
| `warehouse.departments` | 173 | ❌ **REFERENCE** | scope labels only |
| `warehouse.branches` | 347 | ❌ **REFERENCE** | scope labels only |
| `warehouse.compliance_snapshots` | **456** | ❌ | `compliance_status`, disclosed |
| `warehouse.compliance_gaps` | **228** | ❌ | `compliance_status`, disclosed |
| `warehouse.provinces` | **0** | ❌ **REFERENCE** | unused — expansion is in-memory |
| `audit.action_audit` | present | ❌ **NEVER READ** | audit sink (write only) |
| `identity.users` | present | ❌ **NEVER READ** | never agent-readable |

**9 of 16 warehouse tables are unscopable.** `backend/docs/` inventory and the capability probe confirm this by introspection, not by a hardcoded list.

### 3.3 The tenancy rule

> **The model must never generate SQL, and must never receive a row that has not passed `tenant_filter(claims, model)`.**

`tenant_filter` (`app/api/auth.py:210-244`) is **opt-in, per query, with no middleware.** Omit one call and the whole estate returns. Three consequences shape the architecture:

| Property | Consequence for AI |
|---|---|
| `tenant_filter` is opt-in | Scope must be **impossible to omit** → mandatory first positional parameter, enforced by test S6 |
| Scope is **ambient** (JWT), not re-derived per request | No ambient authority in helpers; `verify_token` re-read issue is Phase 0 P0-6 |
| `tenant_filter` requires `department_id` + `branch_id` | Unscopable tables become a **typed, disclosed** fact — never an `AttributeError`, never a silent bypass |

**Verified live:** `exec` 2 244 findings · `soc` scoped to `home-affairs-digital` **745** · `dept-admin` with no scope **0** (`expression.false()`) · province `gp` expands to 15 departments.

**Trap — unknown province slugs fail silently.** `PROVINCES` uses two-letter slugs (`gp`, `kzn`, `wc`…). A probe using `province_ids=["gauteng"]` returned 0 rows — correct for an unknown slug, but indistinguishable from correct scoping. **NFR-AI-14 requires loud failure.**

---

## 4. Governing architecture

### 4.1 The four layers

```
┌──────────────────────────────────────────────────────────────────┐
│ LAYER 1 · SCOPE RESOLUTION        deterministic · no model       │
│   permissions.require_report_permission()  — Gate 1, default-deny│
│   scope.resolve_report_scope(claims) → frozen ReportScope        │
│   scope_hash = sha256(canonical scope tuple)                     │
│   Delegates to tenant_filter() — never re-implements it          │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ LAYER 2 · FACT ASSEMBLY          deterministic · no model       │
│   capability(model) gate  →  SCOPABLE | REFERENCE |              │
│                               UNSCOPABLE | NEVER_READ           │
│   accessors(scope, db) — scope FIRST POSITIONAL                  │
│   Aggregate in SQL, never port the frontend's mappers.ts         │
│   Typed disclosure on every fact                                 │
│   Pure builders → fact_pack + fact_pack_hash                    │
│   Reuses canonical_json / sha256_hex / build_attestation shape   │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ LAYER 3 · NARRATIVE GENERATION     ← THE ONLY MODEL LAYER        │
│   prompt = template + FACT-FILTERED facts + allowed_claims      │
│   pack.serialise(allowed=claims) — the data boundary, not a rule │
│   scope block labelled for_attribution — disclosure, not control │
│   model receives NO db handle, NO sql, NO tools                  │
└───────────────────────────┬──────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ LAYER 4 · VERIFICATION            deterministic · no model       │
│   ① numeral fidelity   every figure ∈ fact pack                  │
│   ② claim class        DISCARD sentences holding unheld classes  │
│   ③ scope containment  no entity outside ReportScope named       │
│   ④ attribution        estate-wide facts said to be estate-wide  │
│   any failure → deterministic template, NEVER model text         │
└──────────────────────────────────────────────────────────────────┘
```

**Why this shape earns its keep.** Layers 1, 2 and 4 contain no inference call, which means every security claim in this programme is **testable on a machine with no model installed.** The fallback is not a degraded path — it is Layers 1 + 2 with a template in place of Layer 3, reading the identical fact view, so it cannot show different numbers. Swapping the model changes only Layer 3.

### 4.2 One agent, not several

A single writer plus a deterministic verifier. Not a planner → retriever → writer → critic chain:

- **CPU-only inference.** Each extra model pass multiplies demo latency (R21).
- **The verifier must be independent of the prompt.** A model-based critic shares the writer's blind spots and can be talked into the same error. A set-membership and regex verifier cannot.
- **Retrieval is already deterministic and already correct.** Layer 2 *is* `tenant_filter`. A retrieval agent would be a place to *lose* the tenancy guarantee, not gain capability.

Phase 2 may add a critic **if** a latency budget and a measured need appear.

### 4.3 Reuse map — what is taken, not rewritten

| Existing asset | Location | Reused for |
|---|---|---|
| `tenant_filter()` | `app/api/auth.py:210` | The scoping primitive. Delegated, never re-implemented |
| `canonical_json()` / `sha256_hex()` | `exports_ag.py:48,58` | `scope_hash`, `fact_pack_hash`, cache key |
| `build_attestation()` shape | `exports_ag.py:62` | The pure-builder pattern for fact packs |
| `_build_benchmark()` | `benchmark.py:46` | **Precedent** for blinded peer disclosure — the claim-class model already working in deterministic Python |
| `CircuitBreaker` | `app/ingestion/circuit_breaker.py:11` | Model gateway failure handling |
| `DOMPurify` sanitize | `ExplainOverlay.tsx:17` | Narrative injection surface (Phase B) |
| `DashHeader` `children` slot | `DashHeader.tsx:36` | AI control on all six dashboards, **zero route changes** |
| `sign_canonical_payload()` | `app/security_pki.py` | Signature chain for any future signed AI artefact |
| `ActionAudit` | `exports_ag.py:209-221` | Audit row shape (additive `action` value) |

**Three bucket definitions must be consolidated in Phase 0 (P0-5).** Until then: **read `risk_scores.bucket` from the column, never recompute it, and never mix a stored bucket with a recomputed one in one fact pack.**

### 4.4 Canonical decisions that supersede prior plans

| Decision | Canonical position | Supersedes |
|---|---|---|
| Model runtime | **Ollama, CPU, `qwen2.5:3b`** now. vLLM/GPU is a Phase C scale decision | G1 §3.1 |
| Config location | `app/ai/settings.py` (own `BaseSettings`) during the POC to hold non-interference to one added line; promotion to `app/config.py` in Phase A when that constraint is no longer binding | G1 §7 |
| Endpoint path | **`/api/v1/reports-ai/…`** — all data routes POST | G1 §4A.4 `/api/v1/reports/` |
| Prompt storage | **Assembled by code**, versioned immutable modules. Not hand-edited YAML | G1 §4A.2, G2 §8 |
| Disclosure | **Typed, 3 classes** in the envelope — `TENANT_SCOPED`, `ESTATE_WIDE`, `DERIVED_FROM_ESTATE_WIDE` | G1 §4A.4 free-text `data_disclosure` |
| Verifier | **Four checks**, discard on any failure | G1 §6.1 |
| AG attestation | **AI narrative stays separate.** The attestation is ECDSA-signed, pure and unit-tested without a DB; nondeterministic text inside it would make the signature attest to text nobody verified deterministically | G1 §4A.3 `ag_attestation_narrative` |
| Report catalogue | 8 target, **2 in the POC** | — |
| Cache | Phase 2, after S5 cache-isolation is proven | G1 §6.1 |

**Why POST-only and `reports-ai`:** `frontend/src/api/demoInterceptor.ts:34-42` silently injects a demo tenant into any `GET` whose path contains `/findings|/metrics|/risks|/compliance|/dashboard|/public/summary`. A GET copilot route would be quietly hijacked in demo mode.

---

## 5. Governance gate — Phase 0

**Blocking for any AI that is resident in the platform.** Six items, one week, 19–23 October 2026.

| ID | Item | Why it blocks AI | Effort |
|---|---|---|---:|
| **P0-1** | Remove `GET /admin/ipinfo`; add a CI rule that no route issues an outbound call without an auth dependency | The platform's own data-residency claim is false while it exists | 0.25 |
| **P0-2** | DB trigger + `RULE`/`REVOKE` making `audit.action_audit` genuinely immutable | `ai.report` retention inherits this trail; nominal-only audit is not audit | 0.5 |
| **P0-3** | `app/audit.py::record_audit()`; call from every privileged mutation | AI writes to the same trail. An unaudited trail is a shared defect | 0.5 |
| **P0-4** | Startup self-test: enumerate routes, assert every data-returning route calls `tenant_filter` | Makes the opt-in tenancy model enforceable rather than conventional | 1.0 |
| **P0-5** | Consolidate the three bucket definitions into one module | Generated narrative must not inherit a latent contradiction | 0.5 |
| **P0-6** | `verify_token` re-reads user state | A revoked role must not survive in a JWT for 12 h | 1.0 |
| | | **Total** | **3.75** |

**Closed as not-applicable** (see §2.2): G1's P0-1/P0-2/P0-3 secret-purge items. G1's P0-7 → this P0-5. G1's P0-8 → this P0-6. G1's P0-9 → this P0-1. G1's P0-10 (`openapi.json` stale) is carried as a documentation item, not a gate.

**Phase 0 exit criteria:**
- [ ] No route can reach an external host without an explicit egress allow-list entry **and** an auth dependency
- [ ] `UPDATE`/`DELETE` on `audit.action_audit` rejected at the database
- [ ] Every privileged mutation writes an audit row, verified by test
- [ ] Route self-test fails the build if a new data route omits `tenant_filter`
- [ ] One bucket implementation; `exports_ag._bucket` and `benchmark._bucket` delegate to it
- [ ] Deactivating a user takes effect within one request

---

## 6. Capability roadmap

Calendar assumes POC completion 15 Oct 2026. Owners align to the existing set.

| Phase | Weeks | Calendar | Owner | Track | Gate |
|---|---|---|---|---|---|
| **13** — POC build | 1 | **7–14 Oct** (Sat 10 Oct included) | Takawira, Peter | Capability 1 proof | **Gate C, Sat 10 Oct** |
| **POC** — Demonstration | — | **15 Oct** | Takawira, Peter, Richard (advisory) | Client acceptance | **15 Oct demo** |
| **13.2** — Vector dataset | deferred | Phase A+ | Lead Dev | Phase 13.2 design ready | gate **V8** below |
| **0** — Governance | 1 | 19–23 Oct | Lead Dev, DevOps | Blocking | §5 exit criteria |
| **A** — Foundation | 3 | 26 Oct – 13 Nov | Lead Dev, DevOps | Blocking | §7.1 |
| **B** — Narrative | 4 | 16 Nov – 11 Dec | Lead Dev | Capability 1 | §7.2 |
| **D** — Triage | 5 | 14 Dec – 15 Jan | Data Eng, Data Scientist | Capability 3 | §7.4 |
| **C** — Copilot | 6 | 19 Jan – 27 Feb | Lead Dev, Data Architect | Capability 2 | §7.3 |
| **E** — EPSS/KEV | 3 | 2–20 Mar | Data Scientist | Enhancement | §7.5 |
| **F** — Assurance | 2 | 23 Mar – 3 Apr | Compliance, Data Scientist | Governance | §7.6 |

Phases B and D may overlap from week 8 — different tables, different routers. **Phase C must not start before P0-4 lands**, because copilot is the capability that depends on tenant scoping being provably correct.

### 6.1 Phase 13 — the POC build (7–14 October 2026)

**1 PD = 8.0 hours.** The register fits the window; one person's calendar does not, and that is the honest headline.

| | PD | Hours |
|---|---:|---:|
| Capacity: 2 builders × 7 build days | 14.00 | 112.0 |
| Build demand (register, builders only) | 13.25 | 106.0 |
| **Float** | **+0.75** | **+6.0** |

| Resource | Tasks | Hours | Share of 56 h |
|---|---:|---:|---:|
| **Takawira Mazando** (Lead Dev, G2) | 34 | **94.0** | **168% — 38.0 h overtime** |
| **Peter Rashaya** (Second Dev, G2) | 3 | 12.0 | 21% |
| Richard Masukume *(advisory)* | 1 | 4.0 | +4.0 h review outside the register |
| Jerry Mokone | 1 | 4.0 | evidence pack |
| Victoria Nedombeloni *(support)* | — | 6.0 | all of it Fri 9 Oct |
| **Register total** | **39** | **114.0** | |

**Saturday 10 October is a working day worked by Takawira alone** — 16.0 h, no peer on site, and **Gate C falls on it**, which makes the `compliance_status` cut trigger a solo decision. Peter's tasks are Fri 9, Mon 12, Tue 13.

**Peter's return buys back the verification independence.** He takes the S6 signature test, `verify.py` and live S2/S3 containment — all three against code Takawira wrote. Without him, one person writes both sides of every control and the claim that the verifier is independent stops being true.

**Pre-agreed cut trigger:** at Gate C, Saturday 10 October, drop `compliance_status` if behind schedule. Cutting Saturday is still a decision; cutting Wednesday is a discovery.

### 6.1.1 Phase 13.2 — vector dataset (deferred, design complete)

`G2_VECTOR_DATASET_DESIGN.md` is complete and Option C is stamped. It is **deferred out of Phase 13** for two reasons, both structural:

1. **There is no float to absorb it.** Takawira is already at 168% of his calendar with a 38.0 h overtime load. Adding a second access path to warehouse data in the same window as the first is how a tenancy defect gets introduced.
2. **A second unscopable read path multiplies R-AI-11** rather than reducing it, until the first one is proven under attack.

**Gate V8 — the question Phase 13.2 must answer before it starts:** *does semantic retrieval beat `ILIKE` on this corpus?* The design already shows the corpus is 2 244 findings with short free-text fields, that 112 of 172 departments hold fewer than 5 findings, and that a k-anonymity floor of 5 would suppress two thirds of it. If retrieval cannot beat a filtered `ILIKE`, it is cost without capability.

### 6.2 Team shape

| Role | Allocation | Notes |
|---|---|---|
| Lead Dev (Takawira) | 0.6 FTE | Router, gateway, tenancy enforcement, prompts |
| Second Dev (Peter Rashaya) | 0.5 FTE *in POC* | **Verifier and containment proofs.** Returns to the POC window; Addendum A's 61 PD is re-baselined, not deleted |
| Head of AI Research (Richard) | 0.5 FTE *advisory in POC* | Model pull, latency measurement, gate and freeze review. Owns no production code in the POC |
| Data Engineer | 0.5 FTE | Triage table, batch job, EPSS ingest |
| Data Scientist | 0.4 FTE | Eval harness, confidence calibration, risk signal |
| DevOps | 0.3 FTE | Ollama, nginx, monitoring |
| Compliance Analyst | 0.2 FTE | POPIA/ISO mapping, AG disclosure wording |
| **New: MLOps engineer** | **0.5 FTE** | Model serving, eval CI, drift. **Nobody currently owns this** — see R-AI-5 |

> **Plan hygiene, resolved 7 October 2026.** The master flight plan's *Project Teams* sheet names **Peter Rashaya** as Technical Lead and *Project Plan* R11 reads "Project Lead Takawira and Peter". **Peter returns to the POC window and takes the verification tasks.** The AI lead for the POC is Takawira with Peter as second builder; Richard is advisory. The master workbook and Addendum A should be corrected so the documents agree.

---

## 7. Phase detail and exit criteria

### 7.1 Phase A — AI platform foundation (26 Oct – 13 Nov)

Promote the POC's proof-of-shape into reusable platform capability.

| Item | Effort |
|---|---:|
| `app/ai/config.py` — prompt registry, model routing, digest-pinned model registry | 2.0 |
| `app/ai/redaction.py` — PII/OEM-payload scrubber, **mandatory pre-egress gate**, records what it stripped | 2.0 |
| `app/ai/capability.py` generalised to a platform-wide route/table guard (supersedes POC-scope version) | 1.5 |
| Eval harness in CI — golden fact packs as a release gate | 2.5 |
| `llm_*` settings promoted to `app/config.py`; `_guard_non_dev_defaults` extended | 0.5 |
| Prometheus collectors `llm_requests_total{model,capability,outcome}`, `llm_request_duration_seconds`, `llm_tokens_total`, `llm_circuit_state`; wire up the `setup_metrics()` stub | 1.5 |
| Redis narrative cache keyed `(role, scope_hash, fact_pack_hash, prompt_version, model_digest)` | 1.5 |
| **Total** | **11.5** |

**Exit:** redaction corpus shows 0 PII egress in CI · eval suite gates a model change · a non-dev environment with `llm_enabled=True` and no cluster-local `llm_base_url` **fails at startup** · `llm_*` metrics visible in Grafana · cache isolation proven by S5.

### 7.2 Phase B — Narrative & briefings (16 Nov – 11 Dec)

| Item | Effort |
|---|---:|
| Remaining 6 report types: `soc_shift_handover`, `appsec_posture`, `dbsec_posture`, `department_monthly`, `peer_benchmark`, + compliance variants | 8.0 |
| Frontend: `frontend/src/api/reportsAi.ts`, `useReport<T>()`, `ReportPanel.tsx` rendering through the **existing** `ExplainOverlay` (DOMPurify already in place). Mounted via the `DashHeader` `children` slot — **no route changes** | 4.0 |
| `GET /reports-ai/grounding/{report_id}` — return the exact fact pack the narrative was written from | 1.5 |
| CSV/PDF export of generated reports. **Grafana stays numeric-only** — it must never be given a model endpoint | 2.0 |
| **Total** | **15.5** |

**Exit:** all 8 report types render, offline and online, with identical numbers · every figure traceable to a fact pack · `ExplainOverlay` unchanged · a kill switch turns AI off for a tier without a deploy.

### 7.3 Phase C — Analyst copilot (19 Jan – 27 Feb)

```
user question
    ↓
LLM #1 → JSON-Schema-constrained intent      (no free text output)
         { entity, filters{severity,source,app,category,status,date_range}, agg{type,group_by,top_n} }
    ↓
DETERMINISTIC COMPILER → SQLAlchemy Core
         • fields map to an explicit ALLOWLIST (no dynamic attrs)
         • every enum validated against Severity/AlertStatus/RiskBucket
         • date range ≤ 400 days · top_n ≤ 50 · hard row cap 200
    ↓
scope = tenant_filter(claims, model)          ◀── INJECTED BY CODE, NOT PROMPT
    ↓
compiled = scope.apply_to(constructed)       ◀── scope cannot be omitted
    ↓
execute → aggregate (k-anonymity floor 5) → redact → LLM #2 → prose
                                                  + cited finding IDs
                                                  + the executed query plan shown to the user
```

The model proposes *what to look for*; the code decides *what it may see*. `tenant_filter` is a straight-line statement in our code, not an instruction in a prompt.

**Exit:** a `dept`-scoped user asking "show findings in KwaZulu-Natal" gets **zero** rows outside scope, with the query plan displayed · P0-4 self-test green · streaming works in production, not just dev (`frontend/nginx.conf` needs `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout`; Vite's dev proxy does not buffer, so streaming **works in dev and silently breaks in production** without the fix).

### 7.4 Phase D — Finding triage assist (14 Dec – 15 Jan)

**Out-of-band**, after the normaliser and warehouse write. A slow model must never stall `processing` consumers.

```python
# input: redacted raw_data excerpt, title, description, category, app tier + owner
# JSON-schema output:
{ suggested_severity, cwe_id, exploitability: low|med|high,
  confidence: 0..1, rationale, requires_human_review }
```

**Hard rules:**
- **AI never mutates `warehouse.findings.severity`.** For scores that are AG-audited, an autonomous severity change is indefensible.
- Suggestions below the confidence floor (default **0.70**) are not surfaced at all.
- Every suggestion and every accept/reject is written to `warehouse.finding_triage` and `audit.action_audit`.

**Schema — a new table, not a new column.** `findings` already has row-width/TOAST bloat as an open risk; a JSON triage blob on the same row worsens it. A separate versioned table gives history and rollback for free. Tenancy columns are denormalised onto it at write time, exactly as `app/lake/writer.py:74-77` does for every other table.

**Exit:** no suggestion below 0.70 rendered · every accept writes a triage row **and** an audit row with actor and model/prompt version · the labelled dataset accumulates toward the ≥2 000 decisions that make fine-tuning viable.

### 7.5 Phase E — EPSS/KEV as a 5th risk signal (2–20 Mar)

The master plan records *"static weights fail to capture 0-day urgency → future: CVE EPSS score as 5th signal (+0.10 weight shift from Sa)"*. This phase is that work.

**Exit:** EPSS ingested and joined to findings · a scored 5th signal in `fused_risk` with the weight shift documented and regression-tested · `APPSCAN_CEILING_PERCENTILE` recalibration re-run (`risk_engine.py:17-19`).

### 7.6 Phase F — Assurance & AG reporting (23 Mar – 3 Apr)

The AG narrative question (open decision OD-3) resolves **here**, not in Phase B. Options are a separately-signed AI narrative artefact, or advisory-only. The default remains **separate** — `build_attestation()` is pure and unit-tested without a database (`tests/test_exports_ag.py:71-109`), and nondeterministic text inside it would make the ECDSA signature attest to text nobody verified deterministically.

**Exit:** the chosen position implemented and evidenced · POPIA/ISO mapping reflects actual AI output · the ATTESTATION narrative remains byte-identical to its deterministic form unless OD-3 explicitly amends it.

---

## 8. Requirement register

| ID | Requirement | Target | Verification | Phase |
|---|---|---|---|:---:|
| **NFR-AI-01** | Narrative P95 latency | ≤8 s cached, ≤20 s cold | `llm_request_duration_seconds` | A |
| **NFR-AI-02** | Copilot query P95 | ≤15 s | same | C |
| **NFR-AI-03** | Triage throughput | ≥200 findings/min sustained | batch job metrics | D |
| **NFR-AI-04** | Numeral fidelity | **100%** — any ungrounded figure discards the output | eval suite, CI gate | POC→A |
| **NFR-AI-05** | PII leak rate | 0 across the redaction corpus | CI gate, synthetic corpus | A |
| **NFR-AI-06** | Cross-tenant leak rate | 0 | scope-escape CI suite | POC→A |
| **NFR-AI-07** | Availability | AI failure must not degrade any dashboard | fault injection | A |
| **NFR-AI-08** | Model reproducibility | model + prompt pinned by digest/version, recorded in every audit row | audit assertion | POC |
| **NFR-AI-09** | Prompt inventory | every prompt versioned, reviewed like code | `app/ai/config.py` registry | A |
| **NFR-AI-10** | Human oversight | every AI recommendation traceable to a named decider | `audit.action_audit` | D |
| **NFR-AI-11** | **`identity.users` and `audit.action_audit` are unreachable from the agent** | zero read paths | `capability()` raises; no accessor references them | POC→A |
| **NFR-AI-12** | **Every fact carries a typed disclosure class** | 3 classes, no free text | envelope assertion | POC |
| **NFR-AI-13** | **Fallback and model paths read the identical filtered fact view** | structural, not conventional | object-identity test | POC |
| **NFR-AI-14** | **Unknown province slug fails loudly** | named error, never a silent empty scope | unit test | POC |
| **NFR-AI-15** | **Risk-bucket divergence band stays empty** | 0 rows with `30 < fused_score < 45` | tripwire test | POC→P0-5 |

**Observability.** `setup_metrics()` (`app/monitoring/metrics.py`) is currently a no-op stub. Wiring it is part of Phase A, not an optional extra.

**Configuration.** AI settings use their own `Settings(BaseSettings)` in `app/ai/settings.py` during the POC. Phase A promotes them to `app/config.py` and extends the existing non-dev guard so that `llm_enabled=True` without a cluster-local `llm_base_url` and a pinned model digest **fails at startup**. Use `SecretStr` — the existing plain-`str` secret fields are the root of the `.env`-handling problem.

---

## 9. Verification suites

Every claim in §3 and §4 is worth only as much as its test. All are CI-gated.

| Suite | Method | Pass criterion | Phase |
|---|---|---|:---:|
| **S1 Role matrix** | For each of the **14** roles from `ROLES_HIERARCHY` × 8 report types | Exactly the §10 matrix holds; unknown role → 403; a role-count change fails the suite | POC (2 types) → B |
| **S2 Scope containment** | Scoped `soc` requests a report; inspect every returned figure | Zero rows with `department_id` outside the province-expanded set | POC |
| **S3 Scope non-escalation** | Scoped user attempts to name another province | Verifier rejects; `expression.false()` yields empty, **never** estate-wide | POC |
| **S4 Claim permission** | `exec` requests a report; scan output for `CVE-\d{4}-\d+`, alert UUIDs, owner names, rule ids | Zero violations of unheld claim classes | POC |
| **S5 Cache isolation** | Generate as provincial user, replay cache key as national user | Different `scope_hash` → cache miss, no cross-serve | A |
| **S6 Structural enforcement** | Import `accessors.py`; assert `scope: ReportScope` is the first positional parameter of every public function | 100% compliance — **the suite that prevents regression** | POC |
| **S7 Capability classification** | Enumerate `Base.registry`; assert every mapped class is classified | No table escapes; `users`/`action_audit` raise | POC→A |
| **S8 Numeral fidelity** | Extract every number from generated prose; assert membership in the fact pack | 100%; any failure discards the output | POC |
| **S9 Adversarial** | Prompt injection via free-text warehouse fields; attempts to name another province, widen scope, leak a CVE | All rejected **at the verifier even where the prompt permitted it** | POC |
| **S10 Redaction** | Synthetic PII corpus through `redaction.py` | 0 egress | A |

---

## 10. Report catalogue — RBAC × tenancy matrix

`—` = denied at Gate 1. **POC delivers `executive_briefing` and `compliance_status`; the rest are Phase B.**

| Report type | exec | compliance | soc | appsec | dbsec | transversal-admin | Scope class |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `executive_briefing` | ✓ | ✓ | — | — | — | ✓ | tenant (province/estate) |
| `peer_benchmark` | ✓ | ✓ | — | — | — | ✓ | tenant + anonymised peers |
| `compliance_status` | ✓ | ✓ | — | — | — | ✓ | **estate-wide — disclosed** |
| `department_monthly` | — | — | — | ✓ | ✓ | ✓ | tenant (single dept) |
| `soc_shift_handover` | — | — | ✓ | ✓ | — | ✓ | tenant |
| `appsec_posture` | — | — | ✓ | ✓ | — | ✓ | tenant |
| `dbsec_posture` | — | — | — | — | ✓ | ✓ | tenant |

**Claim classes — the RBAC layer inside the output.** A role may be permitted to *request* a report but not to *see everything in it*.

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

**This matrix is signed as drafted.** Any addition to the `exec` set requires fresh Compliance approval **before** implementation, not after — with role-aware prompting, a claim class in the prompt is a class the model will *try* to use. "For completeness" is how control identifiers end up in executive prose.

**Why claim classes exist at all.** An `exec` sees *"Estate risk is 25.2; all 15 283 applications in the safe band"* — no CVE list, no owner names. A `soc` user sees *"CVE-2026-31429 on payment-gateway, alert a1b2…, owner Payment Ops"*. Same report family, materially different disclosure. Today the platform differentiates by *which dashboard* you land on; this differentiates by *what your narrative is permitted to say*.

---

## 11. Endpoint contract

All data routes are **POST** under `/api/v1/reports-ai/…`.

| Method | Path | Auth |
|---|---|---|
| `POST` | `/api/v1/reports-ai/generate` | Gate 1 + Gate 2 |
| `GET` | `/api/v1/reports-ai/available` | Returns only the report types **this caller** may request |
| `GET` | `/api/v1/reports-ai/audit/{report_id}` | Own reports only; reveals nothing about scope size |

Response envelope — **authorisation facts are part of the contract, not metadata**:

```json
{
  "report_id": "…",
  "report_type": "executive_briefing",
  "narrative_html": "<h3>…</h3>…",
  "authorisation": {
    "granted_by_role": "exec",
    "permission": "report_ai:executive",
    "scope_class": "tenant_scoped",
    "scope_hash": "sha256:9f2c…",
    "departments_in_scope": 173,
    "claim_classes_applied": ["headline_metrics","risk_buckets","app_names",
                               "department_names","aggregate_compliance"]
  },
  "disclosure": [
    { "scope_class": "estate_wide",               "source_table": "compliance_snapshots", "rows": 456 },
    { "scope_class": "derived_estate_wide",       "source_table": "risk_scores",          "note": "fused_score incorporates an estate-wide compliance component" }
  ],
  "provenance": { "model_id": "qwen2.5:3b", "model_digest": "sha256:…",
                  "prompt_id": "executive_briefing", "prompt_version": 1,
                  "generated_at": "2026-10-15T09:14:22Z", "latency_ms": 6120 },
  "verification": { "numerals_checked": 47, "ungrounded": 0,
                    "claims_violations": 0, "scope_violations": 0, "passed": true },
  "scope_hash": "sha256:9f2c…",
  "fact_pack_hash": "sha256:4b71…",
  "fallback_used": false
}
```

`disclosure` is **not optional.** The compliance limitation must travel with the payload so no consumer can present estate-wide figures as department-scoped. `scope_hash` must be identical in the envelope, the cache key and the audit row.

---

## 12. Data model

### 12.1 `ai` schema — POC (D1: main database, not a separate one)

A separate database breaks audit atomicity: `audit.action_audit` is in the main database, and across two stores the generation row and the audit row stop being one atomic commit — which is precisely the property the audit design exists to protect.

```sql
CREATE SCHEMA IF NOT EXISTS ai;
CREATE TABLE IF NOT EXISTS ai.report (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  report_type     varchar(40)  NOT NULL,
  actor           varchar(255) NOT NULL,
  scope_hash      varchar(80)  NOT NULL,
  scope_class     varchar(20)  NOT NULL,
  department_ids  jsonb        NOT NULL,
  branch_ids      jsonb        NOT NULL,
  prompt_version  integer      NOT NULL,
  model_id        varchar(100) NOT NULL,
  model_digest    varchar(80),
  fact_pack_hash  varchar(80)  NOT NULL,
  narrative_html  text,
  verification    jsonb,
  disclosure      jsonb,
  fallback_used   boolean      NOT NULL DEFAULT false,
  latency_ms      integer,
  created_at      timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_report_actor_idx ON ai.report (actor, created_at DESC);
CREATE INDEX IF NOT EXISTS ai_report_scope_idx ON ai.report (scope_hash, report_type, created_at DESC);
-- Append-only by convention. Immutability is G1 Phase 0 P0-2 (this plan's P0-2).
```

Retention: **same as `audit.action_audit`** (D5). Two retention periods across two audit stores is the kind of divergence an audit finding is written about. **Retention is not immutability** — the two must not be conflated in the record.

### 12.2 `warehouse.finding_triage` — Phase D

Separate versioned table, tenancy denormalised at write time. See §7.4 for the schema and the reasoning.

---

## 13. Risk register — consolidated

| ID | Risk | L | I | Mitigation | Phase |
|---|---|:---:|:---:|---|:---:|
| **R-AI-1** | Cross-tenant leak via copilot | M | **Severe** | §7.3 architecture; P0-4 route self-test; S2/S3/S9; k-anonymity floor 5 | C |
| **R-AI-2** | Hallucinated figures in an AG-audited narrative | M | **Severe** | Four-check verifier + deterministic fallback + signature chain; S8 | POC |
| **R-AI-3** | Model unavailable at scale event | M | M | Breaker reuse, deterministic fallback, sovereign DR | A |
| **R-AI-4** | Analysts over-trust triage suggestions | **High** | **High** | Confidence floor 0.70; advisory-only; accept/reject logged and fed back | D |
| **R-AI-5** | **No MLOps capability on the team** | **High** | M | Fund/contract in Phase A, else Phase C slips | A |
| **R-AI-6** | Sovereign DR becomes an egress path under pressure | L | **Severe** | Same redaction gate on the DR route; network egress allow-list | C |
| **R-AI-7** | GPU CAPEX not approved | — | — | **CLOSED** — Ollama/CPU satisfies the POC at zero CAPEX (C1) | POC |
| **R-AI-8** | Prompt drift after model upgrade silently degrades quality | **High** | M | Model + prompt pinned by digest/version; eval suite in CI as a release gate | A |
| **R-AI-9** | Inference latency/cost on large estates | M | M | Row/token caps, cache, CPU-first sizing, batch not interactive | A |
| **R-AI-10** | Phase 0 exposes pre-existing debt with no owner | — | — | **DOWNGRADED** — 3 of G1's 10 items are not-applicable; 6 remain, 3.75 PD (§2.2) | 0 |
| **R18** | One developer at 168% — Takawira 94.0 h against 56 h, 16.0 h peaks on both gate days, Saturday solo | **High** | **High** | Stated, not hidden; cut trigger at Gate C (Sat 10 Oct); Peter carries the verifier so the heaviest load is deterministic; Richard reviews the freeze diff; Jerry packs the evidence | POC |
| **R20** | Model not pulled — download on critical path | M | M | Pull day 1. Fallback serves identical numbers. Pre-agreed degradation | POC |
| **R21** | CPU-only inference latency under demo conditions | M | M | Token cap decided **day 1** on measured latency, not rehearsal day; rehearse day 7 | POC |
| **R22** | **Non-interference not literally provable** — one `include_router` line is unavoidable | **High** | M | Restate the claim precisely (C5); brief the client **before** the demo | POC |
| **R23** | **`users`/`action_audit` agent-readable if the capability gate is rushed** | M | **Severe** | `NEVER_READ` raises at import; S7; no accessor path exists | POC |
| **R-AI-11** | **Silent estate-wide compliance data presented as scoped** | **High** | **Severe** | Typed 3-class disclosure; attribution check in the verifier; default-deny at Gate 1 | POC |
| **R-AI-12** | Model upgrade changes behaviour with no regression signal | **High** | M | Eval suite in CI as a release gate; digest pinning | A |

---

## 14. Explicit non-goals

Stated so they are not quietly added later:

1. **No free-form text-to-SQL, ever.** Intent schema + allowlisted compiler only.
2. **No autonomous change to finding severity, risk scores, or alert suppression.**
3. **No AI inside the ingestion or dispatch hot path.**
4. **No fine-tuning before the eval harness and ≥2 000 labelled decisions exist.**
5. **No raw `Finding.raw_data` to any model.** Redaction is a hard gate.
6. **No AI text inside the AG attestation** without passing the verifier and an explicit approved change.
7. **No SaaS LLM.** Self-hosted; sovereign cloud only as DR, behind the same redaction gate.
8. **No default-allow.** A role absent from `ROLE_REPORT_AI` gets nothing.
9. **No scope held in prompt text.** The prompt discloses scope; code enforces it.
10. **No modification to `ROLES_HIERARCHY`.** An additive namespace only.

---

## 15. Open decisions

| # | Decision | Owner | Needed by | Default if not amended |
|---|---|---|---|---|
| **OD-1** | Accept Takawira's 38.0 h overtime and the single-person Saturday, or cut `compliance_status` at Gate C | Jerry, Kagiso | **Gate C, Sat 10 Oct** | Cut at Gate C |
| **OD-2** | Victoria's 6.0 h of BA support — confirm it lands entirely on Fri 9 Oct | Jerry | **Day 1, Wed 7 Oct** | Confirm as planned |
| **OD-3** | Is AI output permitted inside an AG attestation, or advisory-only? | AG liaison + Compliance | Phase F | **Separate** |
| **OD-4** | Brief the restated non-interference claim (R22) and the restated verification-independence claim (D-A9) | Jerry | Day 4 | — |
| **OD-5** | `DERIVED_FROM_ESTATE_WIDE` disclosure wording | Victoria → Compliance | **Gate C, Sat 10 Oct** | Envelope-only typed class, no prose |
| **OD-6** | Funding the 0.5 FTE MLOps engineer | PM | Phase A | Phase C slips |
| **OD-7** | Is a model trained on accepted triage decisions a "decision" requiring its own POPIA/AI-governance approval? | Compliance Analyst | Phase D | Treat as yes |
| **OD-8** | Sovereign-cloud region/provider for the DR endpoint | DevOps + Compliance | Phase C | No DR endpoint |
| **OD-9** | Does Phase 0's revealed debt change the go-live date? | PM | Immediate | No change |
| **OD-10** | Scope isolation: separate reporting database vs `ai` schema (D1) | Data Architect, DevOps | **POC day 1** | **`ai` schema in main DB** |
| **OD-11** | AI tooling for the POC — private local Ollama confirmed? | Richard, Kagiso | **POC day 1** | **Local private Ollama.** Overturning it adds a redaction build task, a gateway-provider abstraction and a blocking POPIA DPA review, and retires R21 |

**Standing rule:** *a decision not amended by its deadline is adopted at the stated default.* The programme proceeds; later amendments are change control.

---

## 16. Traceability

| Requirement | Phase | Deliverable | Test |
|---|---|---|---|
| NFR-AI-04 numeral fidelity | POC | `verify.py` | S8 |
| NFR-AI-06 cross-tenant | POC | `scope.py`, `accessors.py` | S2, S3, S6 |
| NFR-AI-08 reproducibility | POC | `ai.report` + `ActionAudit` | audit assertion |
| NFR-AI-11 never-read | POC | `capability.py` | S7 |
| NFR-AI-12 typed disclosure | POC | `disclosure.py` | envelope assertion |
| NFR-AI-13 identical fact view | POC | `generate.py` | identity test |
| NFR-AI-14 loud slug failure | POC | `scope.py` | unit test |
| NFR-AI-15 bucket tripwire | POC | `test_ai_bucket_band.py` | tripwire |
| NFR-AI-01/07 latency, availability | A | `gateway.py`, metrics | fault injection |
| NFR-AI-05 PII | A | `redaction.py` | S10 |
| NFR-AI-09 prompt inventory | A | `config.py` | registry test |
| NFR-AI-03 throughput | D | triage batch | metrics |
| NFR-AI-10 oversight | D | `finding_triage` | audit assertion |
| NFR-AI-02 copilot latency | C | copilot router | metrics |

---

*Master AI integration plan, 6 October 2026. Environment, database and git-history claims verified live against `sita` and the repository at commit `57e080d`. Supersedes `G1_AI_Integration_Plan.md` and `G2_AI_Report_Generation_Plan.md`; corrections to both are itemised in §2 and are load-bearing.*