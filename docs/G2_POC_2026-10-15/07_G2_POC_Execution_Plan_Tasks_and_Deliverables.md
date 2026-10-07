# G2 — POC Execution Plan: Tasks and Deliverables

**Document ID:** G2-EXEC-PLAN-R2 · **Prepared:** 6 October 2026 · **Re-planned:** 7 October 2026
**Window:** Wed 7 Oct → Wed 14 Oct 2026 (7 build days, **Saturday 10 October included**) · **Demonstration:** Thu 15 Oct 2026
**Team:** Takawira Mazando (Lead Developer, G2) + Peter Rashaya (Second Developer, G2) as builders · Richard Masukume advisory · 1 PD = 8.0 h
**Derives from:** `01` G2-POC-PLAN-R3 · `02` G2-POC-DEC-R3 · `04` G2-POC-EVID-R3 · `05` G2-ARCH-R1 · `06` G2-ADR-R1
**Baseline commit:** `57e080d`

This is the build-level plan. It turns the seven architecture decisions in `06` into work items with owners, dependencies, named deliverables and testable acceptance criteria, and it states plainly where the work does not fit.

---

## 1. How to use this document

- **Sections 4 and 5** are the operational core: the capacity arithmetic and the work-item register.
- **Every acceptance criterion is a test.** If it cannot be made into an assertion, it is not an acceptance criterion and should be rewritten until it is.
- **Gates are stop-or-advance points.** A failed gate is handled by the pre-agreed response in §8, not by improvisation.
- Work items are additive to `01` §7. Where `01` and this plan differ, **this plan wins** — the differences are itemised in §4.2.

---

## 2. Standing rules

| # | Rule | Enforced by |
|---|---|---|
| **R1** | No model, no SQL, no database handle, no tools reach the narrative layer. | Layer 3 signature takes a serialised fact pack, not a session |
| **R2** | Retrieval is delegated to `tenant_filter()` (`app/api/auth.py:210`). Never re-implemented. | S6 signature test |
| **R3** | Scope is the **first positional argument** of every accessor. | S6 signature test, introspection over `app/ai/accessors.py` |
| **R4** | Default-deny. An unrecognised role receives nothing. | Gate A |
| **R5** | Fail closed. Empty or invalid scope → `expression.false()` → zero rows, never the estate. | Gate A |
| **R6** | Any verifier failure returns the **deterministic template**. Never partial credit, never model text with a warning. | `verify.py` return type is a union, not a nullable string |
| **R7** | Every generated report writes one `audit.action_audit` row **and** one `ai.report` row in the same commit. | D5 |
| **R8** | `ROLES_HIERARCHY` is not modified. `app/ai/` is an additive namespace. | `git diff` review at freeze |

---

## 3. Capacity — read this before allocating

**1 PD = 8.0 hours.** The binding constraint on this plan is one person's calendar, so every figure is carried in hours as well as days.

| | PD | Hours |
|---|---:|---:|
| Capacity: 2 builders × 7 build days at 100% | **14.00** | **112.0** |
| Build demand (register, builders only) | **13.25** | **106.0** |
| **Float** | **+0.75** | **+6.0** |

The register **fits**. That is not the same as the plan being comfortable, and the per-person split is where the risk actually lives:

| Resource | Tasks | PD | Hours | Share of 56 h | Position |
|---|---:|---:|---:|---:|---|
| Takawira Mazando | 34 | 11.75 | **94.0** | **168%** | **+38.0 h overtime** |
| Peter Rashaya | 3 | 1.50 | 12.0 | 21% | — |
| Richard Masukume *(advisory)* | 1 | 0.50 | 4.0 | — | +4.0 h review outside the register |
| Jerry Mokone | 1 | 0.50 | 4.0 | — | evidence pack |
| **Register total** | **39** | **14.25** | **114.0** | | |
| Victoria Nedombeloni *(support)* | — | — | 6.0 | — | all of it Fri 9 Oct |

**Takawira's 94.0 h is real overtime**, and the 6.0 h of float is Peter's unused capacity — which cannot be lent to a 16.0 h gate day. This is stated here rather than hidden behind a capacity total that balances.

**Daily loading (hours, every resource):**

| Day | Date | T | P | R | V | J | Total |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Wed 7 | 12.0 | — | 0.5 | — | — | 12.5 |
| 2 | Thu 8 | **16.0** | — | 1.0 | — | — | 17.0 |
| 3 | Fri 9 | 14.0 | 2.0 | 1.0 | 6.0 | — | 23.0 |
| 4 | **Sat 10** | **16.0** | — | — | — | — | **16.0 — Takawira alone** |
| 5 | Mon 12 | 8.0 | 8.0 | 1.5 | — | — | 17.5 |
| 6 | Tue 13 | 14.0 | 2.0 | 1.0 | — | — | 17.0 |
| 7 | Wed 14 | 14.0 | — | 1.0 | — | 4.0 | 19.0 |
| 8 | Thu 15 *(demo)* | — | — | 1.5 | — | — | 1.5 |
| 9 | Fri 16 | — | — | 0.5 | — | — | 0.5 |
| | | **94.0** | **12.0** | **8.0** | **6.0** | **4.0** | **124.0** |

### 3.1 What changed, and why

Peter Rashaya returns to the window and takes the three **verification** tasks. Richard moves to advisory. The build starts Wednesday 7 October because design days 2, 5 and 6 October are complete, and Saturday 10 October becomes a build day.

| Change | Effect |
|---|---|
| Peter returns — takes the S6 structural test, the four-check verifier, and live containment | Verifier author ≠ prompt author. **Control claim 1 holds.** |
| Richard advisory — T01 only, plus gate/freeze/demo review | −0.0 PD of build demand, but removes 15 tasks of self-review |
| Design days 2/5/6 Oct complete; build 7–14 Oct | Same 7 build days, Saturday now working |
| Saturday 10 Oct worked by Takawira alone | Gate C falls on a single-person day — see R18 |
| `capability.py` introspection + `NEVER_READ` | +0.5 PD (ADR D-A5) — the `users`/`action_audit` denial |
| Disclosure widening, third class | +0.25 PD (ADR D-A3) |
| Eval set, 6 packs with distinct `scope_hash` | +0.75 PD (ADR D-A4) — a Gate C prerequisite, previously assumed free |
| Bucket-band tripwire | +0.25 PD (ADR D-A7) |
| `mappers.ts` port removed | −0.75 PD (ADR Amendment A1) — aggregate in SQL |

### 3.2 The three control claims, as they now stand

1. **The verifier is not written by the prompt author. HOLDS.** W17 (`verify.py`) is Peter's; W15 (prompt builder and templates) is Takawira's.
2. **Ground truth is not authored by the model author. DOES NOT HOLD** in the structural sense originally claimed — Takawira owns the scope, capability, accessor and context layer *and* the prompt builder. **Restated:** scope and capability *delegate* to `tenant_filter()` and SQL introspection, neither of which can be widened from a prompt; the prompt builder only serialises facts the pack already contains (`pack.serialise(allowed=claims)`); and the containment proof is run live by Peter, not by the author of the prompt. **The original claim must not be repeated in front of the client.**
3. **The structural filter cannot be bypassed by prompt text. HOLDS.** `pack.serialise()` is a code boundary, not a rule in prose.

### 3.3 Pre-agreed cut trigger

**At Gate C, Saturday 10 October** — if Takawira is behind schedule at end of day 4, **drop the `compliance_status` report type**. The cost is real and should be stated to the client in advance: it removes demo item 3 (`disclosure: [{estate_wide, 456}]`), which is the single best demonstration that the design surfaces its own limits.

Note where that trigger now sits: it lands on a **Saturday worked by one person with no peer review available**. Richard's advisory review moves to Monday 12 October, and the containment proofs land Tuesday 13 October as the real check. Deciding on the Saturday is still early enough to be a decision — but it is a solo decision, and D8 should say so.

### 3.4 Open decisions arising from this plan

| # | Decision | Owner | Needed by |
|---|---|---|---|
| **OD-1** | Accept Takawira's 38.0 h of overtime and the single-person Saturday, or cut `compliance_status` at Gate C | Jerry, Kagiso | **Gate C, Sat 10 Oct** |
| **OD-2** | Victoria's 6.0 h of BA support — confirm it lands entirely on Fri 9 Oct | Jerry | **Day 1, Wed 7 Oct** |
| **OD-3** | `DERIVED_FROM_ESTATE_WIDE` disclosure wording (ADR D-A6) | Victoria → Compliance | **Gate C, Sat 10 Oct** — non-blocking, envelope fallback exists |
| **OD-4** | Non-interference claim restated per ADR D-A8 — **brief the client before 15 Oct** | Jerry | **Day 4** |
| **OD-5** | AI tooling — confirm private local Ollama as the POC default | Richard, Kagiso | **Day 1, Wed 7 Oct** |

---

## 4. Work-item register

Owners: **T** = Takawira Mazando (Lead Developer, G2) · **P** = Peter Rashaya (Second Developer, G2) · **R** = Richard Masukume (advisory) · **V** = Victoria Nedombeloni (BA support) · **J** = Jerry Mokone (PM)

The two builders are peers. **No task is co-owned**, and the verifier (W17, Peter) is never written by the author of the prompt it polices (W15, Takawira).

### Day 1 — Wednesday 7 October

#### W12 · Pull `qwen2.5:3b` and benchmark latency on CPU
| | |
|---|---|
| **Owner** | R (advisory) · **0.5 PD / 4.0 h** · **Blocks:** W15, W16, W17 |
| **Deliverable** | `backend/bench/model_latency.md`, `backend/bench/probe_model.py` |
| **Actions** | `ollama pull qwen2.5:3b` (≈2.0 GB). Probe `/v1/chat/completions` at `max_tokens` 300 / 600 / 900 with a 200-fact prompt. Record p50 latency, tokens/sec, RSS. **Charged at 0.5 h on each non-Saturday day** rather than as a 4.0 h block on day 1: the pull happens day 1, the latency measurement is revisited as the token budget settles, and the table closes into the evidence pack on day 9. |
| **Acceptance** | Model present in `ollama list`. Latency table covers all three token budgets. If p50 at 900 tokens exceeds **90 s**, W16 caps `max_tokens` at 600 and `06`'s demo item on narrative length is reduced — **decided on day 1, not on rehearsal day.** |
| **If the pull fails** | Record it, continue. Fallback-only path is pre-agreed (R20). W15/W17 still build; Gate C moves to "fallback renders from a real fact pack". |

#### W01 · `ai` schema and `ai.report`
| | |
|---|---|
| **Owner** | T · **0.5 PD** |
| **Deliverable** | `infrastructure/scripts/init-ai-schema.sql` |
| **Actions** | `CREATE SCHEMA IF NOT EXISTS ai`. `CREATE TABLE IF NOT EXISTS ai.report` with: `id`, `generated_at`, `actor`, `report_type`, `scope_hash`, `fact_pack_hash`, `model_id`, `model_digest`, `prompt_version`, `latency_ms`, `fallback_used`, `disclosure` (JSONB), `verification` (JSONB). Two indexes: `(actor, generated_at DESC)` and `(scope_hash, report_type, generated_at DESC)`. |
| **Acceptance** | Script is idempotent — runs twice cleanly. Applied to the live `sita` instance. `information_schema.tables` shows `ai.report`. All D5 fields present (`model_id`, `model_digest`, `prompt_version`, `latency_ms`, `fallback_used`) — **a report is not evidence unless it is attributable to the exact model and prompt that produced it.** |

### Day 2 — Thursday 8 October

#### W02 · `permissions.py` — Gate 1
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** — |
| **Deliverable** | `backend/app/ai/permissions.py`, `backend/tests/test_ai_permissions.py` |
| **Actions** | `REPORT_AI_PERMISSIONS: dict[report_type, permission]`. `ROLE_REPORT_AI: dict[role, frozenset[report_type]]`. `require_report_permission(report_type)` dependency, mirroring the `require_roles` shape (`app/api/auth.py:75`). Default-deny. |
| **Acceptance** | (a) Unknown role → **403**. (b) `exec` requesting `soc_shift_handover` → **403**. (c) The suite enumerates **14** roles from `ROLES_HIERARCHY` and fails if the count changes — G2 §3.1 says "11 roles", the code defines 14 (`04` §6 correction 2), and a suite hardcoded to 11 passes while missing three. (d) No entry in `app/ai/permissions.py` mutates `ROLES_HIERARCHY`. |

#### W03 · `scope.py` — frozen scope and `scope_hash`
| | |
|---|---|
| **Owner** | T · **1.5 PD** · **Depends:** W02 |
| **Deliverable** | `backend/app/ai/scope.py`, `backend/tests/test_ai_scope.py` |
| **Actions** | `@dataclass(frozen=True)` `ReportScope`: `department_ids`, `branch_ids`, `province_ids`, `nationwide`, `roles`. `ScopeClass` enum. `resolve_report_scope(claims) -> ReportScope`. `scope_hash` = `sha256(canonical_json(sorted tuples))` — **reuse `canonical_json()` from `app/api/routers/exports_ag.py:48`, do not reimplement** (`06` §3.1). Delegates to `tenant_filter()`; never calls `model.department_id` itself. |
| **Acceptance** | (a) `scope_hash` order-independent — `["b","a"]` == `["a","b"]`; scope-sensitive — adding `treasury` changes it (both already proven, `04` §4). (b) **Unknown province slug raises loudly.** `04` §3.1: `province_ids=["gauteng"]` returned 0 rows — correct behaviour for an unknown slug, but indistinguishable from correct scoping. Slugs are two-letter; validate against `PROVINCES` and fail with a named error. (c) Frozen: assignment raises. (d) Department role with no scope → `expression.false()`. |

#### W13 · `claims.py` — claim classes and patterns
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** W02 |
| **Deliverable** | `backend/app/ai/claims.py`, `backend/tests/test_ai_claims.py` |
| **Actions** | `ClaimClass` enum (9 classes, `01` §6). `ROLE_CLAIMS` — **signed exactly as drafted in `01` §6**; D4's condition of approval is that signature. Any addition needs fresh Compliance approval *before* implementation, not after. `CLAIM_PATTERNS`: regex per class — `CVE-\d{4}-\d+`, alert UUID, rule id, department slug. |
| **Acceptance** | (a) `exec` holds none of `cve_ids`, `alert_ids`, `owner_names`, `rule_ids`. (b) The pattern registry matches a seeded corpus and no pattern is empty — an empty regex matches everything, which would discard every sentence. (c) A test asserts the `exec` set equals `01` §6 exactly, so a well-meaning "for completeness" addition fails CI. |

#### W14 · `disclosure.py` — three classes
| | |
|---|---|
| **Owner** | T · **0.75 PD** · **Depends:** W13 |
| **Deliverable** | `backend/app/ai/disclosure.py`, `backend/tests/test_ai_disclosure.py` |
| **Actions** | `DisclosureClass`: `TENANT_SCOPED`, `ESTATE_WIDE`, **`DERIVED_FROM_ESTATE_WIDE`** (ADR D-A3). `Disclosure` dataclass: `scope_class`, `rows`, `source_table`, `note`. `estate_wide_summary(pack)`. Wording per ADR D-A6, **defaulting to the envelope-only form until Compliance ratifies** — the typed control must never be blocked on a wording approval. |
| **Acceptance** | (a) `compliance_snapshots` (456 rows) and `compliance_gaps` (228 rows) tag `ESTATE_WIDE`. (b) Every figure sourced from `risk_scores` tags `DERIVED_FROM_ESTATE_WIDE` — **not just `signal_compliance_penalty`**. The estate-wide component is inside `fused_score` itself: 17.4 × 0.20 ≈ 3.5 points on every row, provincial and national alike, against an average row of 7.46. (c) No `REFERENCE` value is ever tagged — ADR D-A5. |

**GATE A** — end of Day 2, Thu 8 Oct. See §8. **Takawira's heaviest ordinary day is Thu 8 at 16.0 h.**

### Day 3 — Friday 9 October

#### W04 · `capability.py` — the introspection gate
| | |
|---|---|
| **Owner** | T · **0.5 PD** · **Depends:** W01 |
| **Deliverable** | `backend/app/ai/capability.py`, `backend/tests/test_ai_capability.py` |
| **Actions** | `TableCapability`: `SCOPABLE` / `REFERENCE` / `UNSCOPABLE` / `NEVER_READ`. `capability(model)` by `sa_inspect(model).columns` introspection. `NEVER_READ = {users, action_audit}` raises at import. `REFERENCE_TABLES = {departments, branches, provinces}`. |
| **Acceptance** | (a) Test enumerates `Base.registry` and asserts **every** mapped class is classified — no table escapes. (b) **`users` and `action_audit` raise.** `users` carries `email`, `password_hash`, `display_name`, `roles` and full tenancy assignment; `action_audit` carries `actor` and every prior user's `tenant_scope`. These get **no accessor at all** — not a filter, not a disclosure tag. An agent that can read either can enumerate the platform's entire identity and authorisation surface. (c) `departments`/`branches`/`provinces` are `REFERENCE`: readable **only** to resolve a display label for an id already inside `ReportScope`, never disclosed, never counted, never hashed into a fact pack as a value. Mis-tagging them `ESTATE_WIDE` would attach a false estate-wide notice to the name of a province in every provincial report. (d) `backend/tests/test_ai_accessors.py` asserts no accessor references a `NEVER_READ` model. |

#### W05 · `accessors.py` — scope-first retrieval
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** W03, W04 |
| **Deliverable** | `backend/app/ai/accessors.py`, `backend/tests/test_ai_accessors.py` (contains **S6**) |
| **Actions** | Two readers: `read_risk_scores(scope, db)` and `read_compliance(scope, db)`. Scope is the **first positional parameter** — no ambient auth, no request-scoped dependency. Each calls `capability(model)` before building a query. |
| **Acceptance** | **S6 (the signature suite):** introspection over every public function in the module asserts the first parameter is named `scope`. Three personas against live data: `exec` → 2 244 findings / 15 283 risk rows; `soc` scoped to `home-affairs-digital` → 745 findings; `dept-admin` with no scope → **0** (fail-closed). |

#### W15 · Role-aware prompt templates and injection harness
| | |
|---|---|
| **Owner** | T · **1.5 PD** · **Depends:** W13 |
| **Deliverable** | `backend/app/ai/prompts/executive_briefing.v1.py`, `.../compliance_status.v1.py`, `backend/app/ai/prompt_builder.py`, `backend/tests/test_ai_prompt.py` |
| **Actions** | Prompt is **assembled by code**, not hand-edited YAML (`06` §4.3). `build_prompt(scope, report_type, pack)`. Templates are versioned and immutable. Two properties enforced in code: (1) `pack.serialise(allowed=claims)` — the fact pack is **filtered to the claim set before it reaches the prompt**, so the CVE rows are not merely forbidden, they are absent. A prompt instruction becomes a data boundary. (2) The scope block is labelled `for_attribution` — disclosure, not a control. |
| **Acceptance** | (a) **Same report type, two roles, materially different serialised prompts** — the assertion is on `allowed_claim_classes` and on the facts present, not on string inequality. (b) A fact whose claim class the role does not hold is **absent from the serialised prompt**, not merely excluded by instruction. (c) The scope block carries `for_attribution: true`. |

**GATE B** — end of Day 3, Fri 9 Oct. See §8. Victoria's 6.0 h of BA support lands today, ahead of the eval set.

### Day 4 — Saturday 10 October — **Takawira alone**

> No other resource is scheduled today. Peter's three tasks fall on Fri 9, Mon 12 and Tue 13; Victoria's support all landed Fri 9; Richard's advisory review moves to Mon 12.

#### W06 · `context.py` — fact packs, aggregated in SQL

#### W06 · `context.py` — fact packs, aggregated in SQL
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** W05 |
| **Deliverable** | `backend/app/ai/context.py`, `backend/tests/test_ai_context.py` |
| **Actions** | `build_executive_context(scope, db)` and `build_compliance_context(scope, db)`. **Pure builders over already-scoped rows, in the shape of `build_attestation()` (`app/api/routers/exports_ag.py:62`)** — no DB, no session, no claims inside the builder, so it is unit-testable without a database. |
| **Acceptance** | (a) **Aggregation happens in SQL, not by porting `mappers.ts`** (ADR Amendment A1). The six frontend derivations exist because a browser cannot aggregate; server-side they are `GROUP BY` / `DISTINCT ON`. **There is no second implementation, so there is no divergence and no golden fixture.** (b) Unknown severities surface as an explicit `unknown` bucket rather than being folded into `info` (`mappers.ts:125`) or silently dropped (`mappers.ts:137-141`). The server's answer is the truthful one; the difference is recorded, not reproduced. (c) **`risk_scores.bucket` is read from the column and never recomputed** — ADR D-A7. Never mix a stored bucket with a recomputed one in one pack. (d) `fact_pack_hash` via `sha256_hex()` from `exports_ag.py:58`. (e) Builders testable with no database, mirroring `tests/test_exports_ag.py:71-109`. |

#### W18 · Eval set — 6 real fact packs
| | |
|---|---|
| **Owner** | T · **0.75 PD** · **Depends:** W06 · **Victoria supported this on Fri 9** |
| **Deliverable** | `backend/tests/fixtures/ai_eval/*.json`, `backend/tests/test_ai_eval.py` |
| **Actions** | 3 personas × 2 report types: `exec` (estate), DHA `soc` (branch), Gauteng `province-soc-lead` (province). Each fixture records the fact pack, the allowed numeral set, the held claim classes, and the expected `scope_hash`. |
| **Acceptance** | (a) All six `scope_hash` values **distinct** — a fixture set where two personas hash identically is testing nothing. (b) **No figure in any fixture exceeds that pack's own maximum.** `05` §3.4 flagged G2's "Estate risk is 62" as untrue against live data: max is **25.2**, avg **7.46**, all 15 283 rows `safe`, the `critical` bucket **empty**. A prompt seeded with 62 hallucinates 62 or produces prose incoherent against a pack saying 7.5. (c) Every numeral in a fixture is traceable to a live query. |

**GATE C** — end of Day 4, **Sat 10 Oct**. See §8. **This is the cut trigger (§3.3) — and it is a single-person decision.**

### Day 5 — Monday 12 October

#### W16 · `gateway.py` — Ollama client
| | |
|---|---|
| **Owner** | T · **0.5 PD** · **Depends:** W12 |
| **Deliverable** | `backend/app/ai/gateway.py`, `backend/app/ai/settings.py`, `backend/tests/test_ai_gateway.py` |
| **Actions** | `httpx` async client against `http://localhost:11434/v1/chat/completions`. **Reuse `CircuitBreaker` from `app/ingestion/circuit_breaker.py:11`** — do not reimplement. Own `Settings(BaseSettings)` in `app/ai/settings.py`: `ai_ollama_base_url`, `ai_model_id`, `ai_max_tokens`, `ai_temperature`, `ai_timeout_seconds`. |
| **Acceptance** | (a) Settings live in `app/ai/settings.py`, **not** added to `app/config.py` — keeps the non-interference claim at one edited line (ADR D-A8). (b) Timeout → breaker opens → fallback path taken, **not** an exception to the caller. (c) Circuit breaker is the existing class, asserted by identity, not a copy. |

#### W07 · `generate.py` — orchestration and fallback
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** W06, W15, W16 |
| **Deliverable** | `backend/app/ai/generate.py`, `backend/app/ai/fallback.py`, `backend/tests/test_ai_generate.py` |
| **Actions** | `generate(scope, report_type)` → resolve → access → assemble → prompt → generate → verify → return. Two renderers — model and template — over **one filtered view**: `facts = pack.serialise(allowed=claims)` computed once, upstream of both (ADR D-A1 refinement). Jinja2 deterministic templates. |
| **Acceptance** | (a) **The fallback cannot disclose more than the model.** Structural test: the fallback's input is the same object identity as the prompt's fact argument. (b) Gateway down → template renders, **identical numbers**, `fallback_used: true`. (c) Verify failure → template, never model text — enforced by the return type being a union, not a nullable string. (d) No model path can bypass `verify`. |

#### W17 · `verify.py` — the control
| | |
|---|---|
| **Owner** | **P** · **1.5 PD / 8.0 h — Peter's largest day** · **Depends:** W07 |
| **Deliverable** | `backend/app/ai/verify.py`, `backend/tests/test_ai_verify.py` |
| **Actions** | Four checks per ADR §4.4. **Numeral fidelity** — every number in the output is a member of the fact pack's value set. **Claim class** — per-sentence regex, discard the sentence. **Scope containment** — no entity outside the scope decomposition appears. **Attribution** — every `DERIVED_FROM_ESTATE_WIDE` figure carries estate-wide language in the same sentence. |
| **Acceptance** | (a) Each check has a **positive and a negative** test. (b) **Any single failure returns the deterministic template** — no partial credit, no warning-only mode. (c) Numeral fidelity catches a planted figure absent from the pack. (d) Claim filter discards **only** the offending sentence, and the rest survives. (e) `scope_hash` identical across envelope, cache key and audit row. (f) The verifier shares **no code path** with the prompt builder — a model-based critic inherits the writer's blind spots. **This is the most heavily tested module in the POC** (`06` §4.4). **(g) It is written by Peter; the prompt builder and templates it polices (W15) are Takawira's. That separation is the whole reason two builders are on this window — do not merge these two tasks under one owner for any reason of convenience.** |

#### W08 · Fallback templates (2)
| | |
|---|---|
| **Owner** | T · **0.5 PD** · **Depends:** W07 |
| **Acceptance** | Both templates render from a real fact pack with **no model installed** — the offline path is provable on 14 October regardless of R20. |

**GATE D** — end of Day 5, Mon 12 Oct. See §8.

### Day 6 — Tuesday 13 October

#### W09 · `reports_ai.py` — router and envelope
| | |
|---|---|
| **Owner** | T · **1.0 PD** · **Depends:** W07 |
| **Deliverable** | `backend/app/ai/routers/reports_ai.py`, **one added line** in `app/main.py` |
| **Actions** | `POST /api/v1/reports-ai/generate`, `GET /api/v1/reports-ai/available`. Response envelope: `authorisation`, `disclosure`, `provenance` (`model_id`, `model_digest`, `prompt_version`, `latency_ms`), `verification`, `scope_hash`, `fact_pack_hash`. |
| **Acceptance** | (a) **`git diff main` on this change is exactly one added line.** No deletions, no modified logic, nothing in `app/api/`, `app/processing/`, `app/tenant.py`, `app/models/` or the frontend (ADR D-A8). (b) `/available` lists report types the **caller** may request — filtered by their claims, not the full catalogue. (c) Envelope is complete on the fallback path too, including `model_id: null` and `fallback_used: true`. |

#### W10 · `ActionAudit` + `ai.report` write
| | |
|---|---|
| **Owner** | T · **0.5 PD** · **Depends:** W09 |
| **Acceptance** | One `audit.action_audit` row and one `ai.report` row in **one commit** — across two schemas in one database (D1), atomic. All D5 fields written. Retention matches `audit.action_audit` (D5). |

#### W19 · Live suites S2 / S3 / S4 and adversarial tests
| | |
|---|---|
| **Owner** | **P** (S2/S3 containment) + **T** (S4, adversarial) · **1.0 PD** · **Depends:** W09 |
| **Acceptance** | **S2 containment** — DHA `soc` 745 rows vs `exec` 2 244, different `scope_hash`. **S3 non-escalation** — provincial persona widening scope fails closed to empty. **S4 claims** — claim filter catches an injected CVE id, discards that sentence. **Adversarial** — attempts to name another province, widen scope, or leak a CVE id all fail **at the verifier even where the prompt permitted it** (`01` §5.1). **Peter runs the containment suites against W03/W04/W05, which Takawira wrote — the containment proof is not authored by the author of the scope layer it proves.** |

**GATE E** — end of Day 6, Tue 13 Oct. See §8.

### Day 7 — Wednesday 14 October

#### W11 · Bucket-band tripwire
| | |
|---|---|
| **Owner** | T · **0.25 PD** · **Depends:** W06 |
| **Deliverable** | `backend/tests/test_ai_bucket_band.py` |
| **Acceptance** | Asserts `count(fused_score between 30 and 45) == 0` over live data, failure message naming the defect and all three locations: `risk_engine.py:78` (safe ≤30), `exports_ag.py:40` and `benchmark.py:38` (both safe <45). **Currently passes — verified 6 Oct: all 15 283 rows fall in 5.0–25.2.** G2 does not fix the platform; G2 makes the platform tell us when the divergence goes live. |

#### W20 · Rehearsal, regression, freeze
| | |
|---|---|
| **Owner** | B · **0.5 PD** · **Freeze 17:00** |
| **Acceptance** | (a) `ruff check backend/` clean. (b) Full `pytest backend/tests` green — **no existing test regressed.** (c) All six gates evidenced. (d) `git diff main --stat` shown line by line: additions only. (e) Demo run sheet rehearsed end-to-end on day-7 hardware, timed — R21 is a CPU-latency risk and rehearsal is the only mitigation that works. |

---

## 5. Deliverable register

| ID | Deliverable | Path | Owner | Gate |
|---|---|---|---|:---:|
| DEL-01 | Latency benchmark | `backend/bench/model_latency.md` | R | A |
| DEL-02 | `ai` schema + table | `infrastructure/scripts/init-ai-schema.sql` | T | A |
| DEL-03 | Gate 1 — RBAC | `backend/app/ai/permissions.py` | T | A |
| DEL-04 | Gate 2 — scope + hash | `backend/app/ai/scope.py` | T | A |
| DEL-05 | Claim classes | `backend/app/ai/claims.py` | T | A |
| DEL-06 | Disclosure classes | `backend/app/ai/disclosure.py` | T | A |
| DEL-07 | Capability gate | `backend/app/ai/capability.py` | T | B |
| DEL-08 | Scope-first accessors + S6 | `backend/app/ai/accessors.py` | T | B |
| DEL-09 | Prompt templates + harness | `backend/app/ai/prompts/`, `prompt_builder.py` | T | B |
| DEL-10 | Fact packs | `backend/app/ai/context.py` | T | C |
| DEL-11 | Eval fixtures | `backend/tests/fixtures/ai_eval/` | T | C |
| DEL-12 | Model gateway + AI settings | `backend/app/ai/gateway.py`, `settings.py` | T | D |
| DEL-13 | Orchestration + fallback | `backend/app/ai/generate.py`, `fallback.py` | T | D |
| DEL-14 | **Verifier** | `backend/app/ai/verify.py` | **P** | D |
| DEL-15 | Router + envelope | `backend/app/ai/routers/reports_ai.py` | T | E |
| DEL-16 | Audit pair | W10 | T | E |
| DEL-17 | Live + adversarial suites | `backend/tests/test_ai_*.py` | P + T | E |
| DEL-18 | Bucket tripwire | `backend/tests/test_ai_bucket_band.py` | T | E |
| DEL-19 | Evidence pack | `docs/G2_POC_2026-10-15/08_Evidence_Pack.md` | **J** | F |
| DEL-20 | Frozen signed branch | tag `g2-poc-freeze-2026-10-14` | T | F |

**Total: 20 deliverables · 14.25 PD / 114.0 h in the register · 1 forced edit to an existing file.** DEL-19 is owned by Jerry so the evidence is assembled by someone who did not write the code it certifies.

---

## 6. Schedule

| Day | Date | Takawira | Peter | Gate |
|---|---|---|---|:---:|
| 1 | **Wed 7 Oct** | W01 · W02 | — | — |
| 2 | **Thu 8 Oct** | W03 · W04 · W13 · W14 | — | **A** |
| 3 | **Fri 9 Oct** | W05 · W15 | W04 (S6) · Victoria 6.0 h | **B** |
| 4 | **Sat 10 Oct** | W06 · W18 — **alone, 16.0 h** | — | **C — cut trigger** |
| 5 | **Mon 12 Oct** | W07 · W08 · W16 | **W17 — verifier, 8.0 h** | **D** |
| 6 | **Tue 13 Oct** | W09 · W10 · adversarial | W19 (S2/S3) | **E** |
| 7 | **Wed 14 Oct** | W11 · W20 · integration smoke | — (Jerry: evidence pack) | **FREEZE 17:00** |
| 8 | **Thu 15 Oct** | **DEMONSTRATION** | **DEMONSTRATION** | 🏁 |

Richard supports across days 1–3, 5–7 and the demonstration at 0.5–1.5 h/day (advisory: gates, freeze diff, demo controls). **Saturday 10 October has no second person on site.** Day 7 is the only buffer and it is also the freeze day. Day 8 is not a build day.

---

## 7. Verification commands

Run from the repository root. Both are already in CI (`.github/workflows/ci.yml`), so a green local run is a green CI run.

```powershell
# lint — CI runs exactly this
ruff check backend/

# full suite — 11 existing test modules must stay green
backend\.venv\Scripts\python.exe -m pytest backend/tests -q

# POC suites only, during the build
backend\.venv\Scripts\python.exe -m pytest backend/tests -q -k ai

# non-interference proof — must show additions only
git diff main --stat
git diff main -- backend/app/api backend/app/processing backend/app/tenant.py backend/app/models frontend
# ↑ the second command must return EMPTY

# model present
ollama list
```

---

## 8. Gate criteria and pre-agreed failure responses

| Gate | When | Pass criteria | If it fails |
|---|---|---|---|
| **A** | Thu 8 PM | Unknown role → 403 · empty scope → `expression.false()` · unknown province slug raises loudly · `NEVER_READ` raises at import | Do not start W15. A Gate 1 hole makes every later guarantee theatre. |
| **B** | Fri 9 PM | S6 green — every accessor takes `scope` first · `capability()` classifies all 20 registered models · two roles yield different `allowed_claim_classes` | Stop. Rework W05's signatures, not the tests. |
| **C** | **Sat 10 PM** | First generation from a real fact pack · 6 eval fixtures with distinct `scope_hash` · no fixture figure exceeds its pack max | **CUT TRIGGER.** Drop `compliance_status` (−1.5 PD). Pre-agreed response, decided Saturday rather than discovered Wednesday — **on a day with no peer available, so record the decision and its reason.** |
| **D** | Mon 12 PM | Verifier discards an ungrounded numeral · discards a sentence with an unheld claim class · fallback renders from the same filtered pack | **Cut narrative, keep control.** Ship fallback-only. R6 says the verifier is not negotiable; the model is. |
| **E** | Tue 13 PM | Adversarial scope-widening, province-naming and claim-leak attempts **all rejected** | **No demo of an unguarded agent.** Reduce the demo to the deterministic fallback and say why. |
| **FREEZE** | Wed 14 17:00 | Lint clean · full suite green · all gates evidenced · diff is additions only **and independently reviewed by Richard** | Do not ship a known defect into a client meeting. Demo the frozen evidence and log the gap. |

---

## 9. Risk register — changes from `01` §11

| ID | Change |
|---|---|
| **R18** **Critical** | **Changed shape, not gone.** The register fits (+0.75 PD float), but Takawira carries **94.0 h against 56 h — 38.0 h of overtime — with 16.0 h peaks on both gate days, and Saturday 10 October has no peer review.** Mitigation: Peter owns the verifier and the containment proofs so the heaviest load is the deterministic backend; the Gate C cut trigger on Saturday; Richard's freeze-diff review and Jerry's evidence pack sit outside Takawira's hands. |
| **R09** **Critical** | **New form.** Verification is concentrated in one person at 21% utilisation while the other runs at 168%. W02 tests, W15 harness, W11 tripwire and W20 regression become self-checks by the same author as the code. Mitigation: W17, W04 and W19 are Peter's against Takawira's code — three independent checks; Richard's 0.5 h day-7 advisory covers the W20 diff; Jerry owns the evidence pack. |
| **R22** **new · High** | **Non-interference is not literally provable.** One `include_router` line in `app/main.py` is unavoidable. If the claim is presented as "nothing existing modified" and a client runs `git diff main` on a projector, the strongest demo item in the pack fails on a technicality. **Mitigation: brief the restated claim (ADR D-A8) before 15 October.** OD-4. |
| **R23** **new · High** | **`users` and `action_audit` are agent-readable if W04 is skipped or rushed.** `05` did not consider this; ADR D-A5 does. `password_hash`, every user's role and tenancy assignment, every prior user's scope. **Mitigation: W04 acceptance (b) and (d); no accessor for either model.** |
| **R21** | Unchanged, but now decided on **day 1** (W12 acceptance) rather than rehearsal day — the 900-token cap is a day-1 decision. |
| **R20** | Unchanged. Fallback is pre-agreed degradation and is provable with no model installed (W08 acceptance). |
| **R02** **Critical** | Unchanged and **strengthened** by D-A3 — the exposure is not only unscopable tables but values already baked into in-scope numbers. |

---

## 10. Definition of done — POC level

The POC is complete on 14 October when all of the following hold:

1. Six gates evidenced, each by a named test that fails without the corresponding work item.
2. `ruff check backend/` clean; full `pytest backend/tests` green with **no existing test regressed**.
3. `git diff main --stat` consists of additions to `app/ai/`, `infrastructure/scripts/`, `backend/tests/` and **one** line in `app/main.py`.
4. Both report types render **with no model installed** and identical numbers.
5. All six eval fixtures carry distinct `scope_hash` values and no figure exceeding its own pack maximum.
6. `identity.users` and `audit.action_audit` are provably unreachable from the agent.
7. Every generation writes both audit rows in one commit, carrying `model_id`, `model_digest`, `prompt_version`, `latency_ms`, `fallback_used`.
8. Evidence pack (DEL-19) signed; tag `g2-poc-freeze-2026-10-14` pushed.
9. The demo run sheet has been rehearsed end-to-end on day-7 hardware and timed.

---

## 11. Out of scope — unchanged from `01` §10

Frontend viewer (activity 17.5, dropped by direction) · 5 of 7 report types · cache keyed on `scope_hash` · multi-agent orchestration · prompt v2 tuning · independent InfoSec review · k6 load test · chaos test · UAT · production deployment · `ai.report` immutability hardening (G1 Phase 0, P0-5) · adding tenancy columns to the compliance tables (a warehouse-programme change — **D2**).

---

*Execution plan for G2, build 7–14 October 2026 (Saturday 10 October included), demonstration 15 October. Database claims verified live against `sita` on 6 October 2026. Effort figures supersede `01` §7; all other content derives from `01`–`06` without change. Re-planned 7 October 2026: Peter Rashaya returns to the verification tasks, Richard Masukume is advisory, and the three control claims are restated in §3.2.*