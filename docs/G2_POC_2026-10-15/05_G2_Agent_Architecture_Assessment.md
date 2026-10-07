# G2 — Agent Architecture Assessment

**Document ID:** G2-ARCH-R1 · **Prepared:** 6 October 2026
**Subject:** how AI agent(s) should be integrated into `C:\sita-platform` to generate reports by prompting, role-aware and tenancy-compliant
**Basis:** direct study of the codebase. Every claim below is referenced to a file and line, or executed against the live database.

---

## 1. What the pipeline actually does today

### 1.1 Ingestion → warehouse

```
AppScan / Imperva DAM / Imperva WAF / API Security
        ↓  connectors/  (base, appscan, imperva, apisec, compliance)
        ↓  ingestion/   (circuit_breaker, token_bucket, retry, dlq, scheduler)
        ↓  dispatch/    (email, pagerduty, teams)
        ↓  lake/writer.py        ← tenancy denormalised onto every row here
warehouse.*  (16 tables)
```

Tenancy is written **once, at write time**, as four slug columns: `department_id`, `branch_id`, `ministry_id`, `cluster_id`.

### 1.2 Warehouse → risk fusion → REST → browser

```
warehouse.findings ─┐
warehouse.alerts  ──┤
compliance_snapshots┤  processing/risk_aggregator.py
                    ↓  processing/risk_engine.py  (fused_score, 4 weighted signals)
             warehouse.risk_scores
                    ↓
        api/routers/*.py   ← tenant_filter() applied HERE, per query
                    ↓
        frontend: 6 parallel fetches → mappers.ts → explanations.ts
```

**The canonical tenancy pattern, repeated in every router:**

```python
scope = tenant_filter(claims, Model)      # app/api/auth.py:210
q = select(...)
if scope is not None:                     # ← opt-in, per query, per model
    q = q.where(scope)
```

Seen at `dashboard.py:21-26`, `benchmark.py:168-179`, `exports_ag.py:175-177`.

### 1.3 The front end does the analysis

`frontend/src/hooks/useExecData.ts:23-47` fans out to **six endpoints**:

| Call | Feeds |
|---|---|
| `dashboard/summary` | `current_risk_score`, bucket counts |
| `findings?size=200` | `severityCounts`, `findingsByAppSeverity` |
| `risks?size=100` | `latestRiskPerApp` (top 5), `riskTrendSeries` |
| `compliance/popia` | `popia` score |
| `compliance/iso_27001` | `iso` score |
| `alerts?size=50` | `groupAlertsByRule` |

Then `frontend/src/data/mappers.ts` computes the derived views **in the browser**, and `frontend/src/data/explanations.ts` writes the prose about them.

### 1.4 Where narrative lives today

`explanations.ts` exports `buildExplain(role, facts)` and `buildLayman(role, facts)` — a `switch` over role returning **hand-authored HTML with facts interpolated**. It is already role-parameterised and already fact-driven. It is not a model.

**It has drifted, and nobody noticed.** Verified against the live database:

| `explanations.ts` claims | Reality (live) |
|---|---|
| "every national department (**60 departments**)" — `exec`, `appsec` | **173** departments |
| SOC: "MTTD & MTTR: **Not tracked by the backend yet**" | MTTD/MTTR genuinely absent, but the *sentence* is stale prose either way |
| DB Security: "Databases Monitored / Coverage: **not tracked** — no DAM inventory feed" | `warehouse.database_inventory` exists — **2 577 rows** |
| Service Ops: "System Health: CPU, memory, disk, queue metrics are **not tracked by the backend yet**" | `system_metrics` **95 rows**, `slo_metrics` **52 rows** |
| Compliance: "Regulatory Calendar: **not populated by the backend yet**" | no table — accurate |

**Hand-authored narrative rots silently.** A generated-from-fact-pack narrative cannot. This is the strongest practical argument for the agent, independent of the security argument.

---

## 2. Three structural facts that determine the agent design

### 2.1 Facts are computed client-side — there is no server-side fact pack to prompt from

`mappers.ts` holds the derivation logic. A server-side agent **cannot call TypeScript**. Every fact the prompt needs must be recomputed server-side.

**Consequence:** the largest single piece of POC work is not the agent — it is a server-side fact layer that reproduces `mappers.ts` deterministically. G2 §4 assumes `context.py` builders will be written fresh; that is correct, but the duplication must be a **conscious decision with a divergence test**, not an accident.

**Recommended:** port the derivations to `app/ai/context.py` as pure functions, and add a test that spot-checks a sample against `mappers.ts` output. Two implementations of "severity counts" will diverge.

### 2.2 Tenancy leaks through derived values, not just rows

This is the most important finding and it is not in G2.

```python
# app/processing/risk_aggregator.py:69-76
snap = (await session.execute(
    select(ComplianceSnapshot.overall_score)
    .where(ComplianceSnapshot.framework == "popia")
    .order_by(ComplianceSnapshot.snapshot_date.desc()).limit(1)
)).scalar_one_or_none()
```

**No tenancy filter.** One estate-wide POPIA score (latest = **82.6**, 2026-09-10) becomes `signal_compliance_penalty = 17.4`, which is weighted **0.20** in `fused_risk`, contributing **3.5 points to every application's fused_score in the estate** — provincial and national alike.

Verified: `DEFAULT_WEIGHTS = {appscan: 0.35, imperva: 0.25, exposure: 0.20, compliance: 0.20}`.

> **A provincial user's risk score is partly determined by an estate-wide figure, and no amount of row-scoping in the agent can change it.**

G2 §2 treats the compliance problem as *"which rows may the agent read."* It is also, and more subtly, **"what is already baked into the numbers."** This requires a **third** disclosure class:

```python
class DisclosureClass(str, Enum):
    TENANT_SCOPED             = "tenant_scoped"      # row-filtered by ReportScope
    ESTATE_WIDE               = "estate_wide"        # table has no tenancy columns
    DERIVED_FROM_ESTATE_WIDE  = "derived_estate_wide" # row in scope, value computed estate-wide
```

Every `fused_score`, every `signal_compliance_penalty`, every bucket derived from them carries `DERIVED_FROM_ESTATE_WIDE`. The agent must say so, or a provincial report presents a number that is partly global without saying so.

### 2.3 Six of sixteen warehouse tables cannot be scoped at all

| Table | `department_id` | `branch_id` | Scopable |
|---|:---:|:---:|:---:|
| `findings`, `alerts`, `risk_scores`, `database_inventory`, `api_endpoints`, `waf_blocks`, `persons`, `dispatch_log` | ✅ | ✅ | **yes** |
| `compliance_snapshots`, `compliance_gaps` | ❌ | ❌ | **no** |
| `system_metrics`, `slo_metrics`, `agents`, `connector_health`, `rejected_records` | ❌ | ❌ | **no** |

G2 names only the two compliance tables. The agent should treat **unscopable as a property discovered from the model**, not a hardcoded list — otherwise the next unscopable table is missed silently.

```python
def scopable(model) -> bool:
    return hasattr(model, "department_id") and hasattr(model, "branch_id")
```

### 2.4 Correction to my own earlier framing

`exports_ag.py:196-199` **already discloses** the compliance gap in prose:

> *"Risk profile is scoped to the caller's province; compliance snapshot/gaps are estate-wide today (snapshots carry no department_id)."*

So the limitation is **known and documented in production**, not hidden. What is missing is that it is **free text inside an attestation note**, not a typed, machine-readable field a consumer can enforce. G2's contribution is the typing — which is a smaller and more precise claim than "undisclosed".

---

## 3. What already exists to reuse

The codebase contains two patterns G2 should adopt rather than reinvent.

### 3.1 `build_attestation()` — the pure-builder pattern (`exports_ag.py:62`)

A pure function taking already-fetched, already-scoped rows and returning a dict. No DB, no session, no claims. Deterministic. Directly unit-testable.

**Reuse:** make the fact-pack builder this shape. If `build_attestation` can be tested without a DB (`tests/test_exports_ag.py:71-109`), so can `context.build_executive_context`.

**Also reuse, do not reimplement:**
- `canonical_json()` (`exports_ag.py:48`) — sorted keys, tight separators. G2's `scope_hash` and `fact_pack_hash` should call it. Reimplementing hashing is how two components end up disagreeing on what "the same" payload means.
- `sha256_hex()` (`exports_ag.py:58`)

### 3.2 `_build_benchmark()` — role-aware disclosure, already in production (`benchmark.py:46`)

This is the reference implementation of the exact principle G2 wants for prompts:

```python
label = PROVINCES[p] if (nationwide or is_you) else f"Peer Province {_PEER_LETTERS[peer_index]}"
leaderboard.append({..., "province_id": p if (nationwide or is_you) else None, ...})
```

A provincial executive sees peer provinces as **"Peer Province A/B/C"** with `province_id: None` — real data, blinded identity. A national executive sees all of them unblinded.

> **This is `ClaimClass` already working in deterministic Python.** G2's `ROLE_CLAIMS` is the same idea applied to generated text. The agent should be built to produce output of the same discipline — and `_build_benchmark` should be cited as the precedent when justifying D4.

### 3.3 Three bucket definitions that disagree

| Module | Thresholds | Role |
|---|---|---|
| `risk_engine.risk_bucket` (`:78`) | safe ≤30, monitored ≤70, critical >70 | **writes** `risk_scores.bucket` |
| `exports_ag._bucket` (`:40`) | safe <45, monitored ≥45, critical ≥70 | **recomputes** |
| `benchmark._bucket` (`:38`) | safe <45, monitored ≥45, critical ≥70 | **recomputes** |

They diverge for scores in **31.0–44.9**. Verified: all 15 283 current rows score **5.0–25.2** (avg 7.46), so **zero rows fall in the band today** and all three currently agree.

That is a **data-dependent accident, not a guarantee.** The moment a score lands at 35, `risk_scores.bucket` says `monitored` while the AG attestation and the benchmark leaderboard say `safe` — and a generated narrative that mixes sources would assert both.

**Agent rule:** read `risk_scores.bucket` from the column, never recompute it. Never mix a stored bucket with a recomputed one in one fact pack. Add a test that fails if a score falls in 31–44.

*(Not fixed here — G2's first guarantee is that no existing file is modified. This belongs to the master programme as a separate change.)*

### 3.4 G2's example prose contradicts the live data

G2 §6 illustrates `exec` output as:

> *"Estate risk is 62, critical exposure concentrated in 4 applications"*

**Live maximum `fused_score` is 25.2. Average is 7.46. Every row is bucketed `safe`.** There is no application at 62, and no critical bucket exists.

An agent whose prompt or golden examples are seeded with "risk is 62" will either hallucinate 62 or produce incoherent prose against a fact pack saying 7.5. **The eval set and prompt examples must be rebuilt from live fact packs before any quality claim is made** — this is the eval-set task on day 4 (Saturday 10 October), it gates Gate C, and it is owned by **Takawira** in the current delivery split, with Victoria's 6.0 h of BA support delivered in advance on Friday 9 October.

---

## 4. Recommended architecture

### 4.1 The model appears in exactly one layer

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1 · SCOPE RESOLUTION          deterministic · no model    │
│   ReportScope(claims) frozen · scope_hash · scopable(model)?    │
│   Delegates to tenant_filter() — never re-implements it         │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2 · FACT ASSEMBLY            deterministic · no model    │
│   accessors(scope, db) — scope FIRST POSITIONAL, no ambient auth │
│   disclosure tagging: TENANT_SCOPED | ESTATE_WIDE |              │
│                       DERIVED_FROM_ESTATE_WIDE                  │
│   pure builders → fact_pack + fact_pack_hash                   │
│   reuses canonical_json / sha256_hex / build_attestation shape  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3 · NARRATIVE GENERATION      ← THE ONLY MODEL LAYER     │
│   prompt = template + facts + allowed_claim_classes(from role)  │
│   scope stated for attribution only; enforcement is Layer 4      │
│   model receives NO db handle, NO sql, NO tools                  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4 · VERIFICATION            deterministic · no model     │
│   ① numeral fidelity   every figure ∈ fact pack                 │
│   ② claim class        DISCARD sentences holding unheld classes │
│   ③ scope containment  no entity outside ReportScope named      │
│   ④ attribution        estate-wide facts said to be estate-wide │
│   any failure → deterministic template, NEVER model text        │
└─────────────────────────────────────────────────────────────────┘
```

**Why this shape.** Layers 1, 2 and 4 contain no model. That means:

- Every security property is **testable without a model** — the model is not required to prove tenancy is enforced.
- The **fallback is not a degraded path**, it is Layers 1+2 with a template in place of Layer 3. It cannot show different numbers, because it reads the same fact pack.
- Swapping models, or having none, changes **only Layer 3**.

### 4.2 One agent, not several

The request said "agent(s)". My recommendation is **one writer agent plus a deterministic verifier**, not a planner → retriever → writer → critic chain.

Reasons, specific to this deployment:

- **CPU-only inference.** A 3B model on a 6-core i5 has no headroom. Each extra model pass multiplies demo latency (R21).
- **The verifier must be independent of the prompt.** A model-based critic shares the writer's blind spots and can be talked into the same error. A regex-and-set-membership verifier cannot.
- **Retrieval is already deterministic and already correct.** Layer 2 is `tenant_filter` — there is nothing for a retriever agent to decide. A retrieval agent would be a place to *lose* the tenancy guarantee, not gain capability.

Phase 2 may add a critic agent **if** a latency budget and a measured need appear. It should not be built now for appearance's sake.

### 4.3 Prompt assembly is a compiler, not a template

The role-aware prompt should be assembled by code that can be inspected and tested, not hand-edited YAML:

```python
def build_prompt(scope: ReportScope, report_type: str, pack: FactPack) -> Prompt:
    claims = ROLE_CLAIMS[next(r for r in scope.roles if r in ROLE_CLAIMS)]  # default-deny
    return Prompt(
        template=templates[report_type],              # versioned, immutable
        facts=pack.serialise(allowed=claims),         # facts filtered TO the claim set
        allowed_claim_classes=claims,
        scope=scope.describe_for_attribution(),        # disclosure only, not enforcement
        estate_wide_notice=pack.estate_wide_summary(), # "the following figures are estate-wide"
    )
```

Two properties worth enforcing in code:

1. **`pack.serialise(allowed=claims)`** — the fact pack itself is filtered to the claim set before it reaches the prompt. The model is not merely *told* it may not mention CVEs; the CVE rows are not in its context. That converts a prompt instruction into a data boundary.
2. **The scope block is labelled** `for_attribution` so a reviewer can see it is disclosure, not a control.

### 4.4 Verification is where the security claim is earned

Layer 4 is the only place G2's guarantees are actually proven, and it should be the most heavily tested layer in the codebase:

| Check | Method | Failure action |
|---|---|---|
| Numeral fidelity | Extract every number from output; assert membership in fact pack values | Discard whole output |
| Claim class | Per-sentence regex for `CVE-\d{4}-\d+`, alert UUIDs, department names, rule ids, owner names; discard matching sentences | Discard sentence |
| Scope containment | Assert no department/branch/province id in output is outside `scope_hash` decomposition | Discard whole output |
| Attribution | Assert every `ESTATE_WIDE` fact's figure appears with estate-wide language nearby | Discard whole output |
| Hash consistency | `scope_hash` identical in envelope, cache key, audit row | Fail the request |

**Every failure path returns the deterministic template, never the model text.** No partial credit, no warning-only mode.

---

## 5. Where G2 is right, and where it needs amending

| G2 | Verdict |
|---|---|
| RBAC and tenancy as the primary design constraint | **Right.** The codebase confirms it: `tenant_filter` is opt-in and repeated per query |
| Scope as a required positional parameter, enforced by S6 | **Right.** Prevents the exact omission mode present today |
| Two independent gates before any row is read | **Right** |
| `ROLES_HIERARCHY` untouched; additive namespace only | **Right** |
| Attestation stays deterministic | **Right** |
| Verifier independent of the prompt | **Right** — and it should be the strongest layer, not an afterthought |
| Compliance unscopable, typed disclosure required | **Right, but incomplete** — add `DERIVED_FROM_ESTATE_WIDE` for values computed estate-wide (§2.2) |
| "11 roles" | **Wrong.** 14 in `ROLES_HIERARCHY`. Enumerate from the dict |
| `AttributeError` as the compliance failure mode | **Wrong for the intended audience** — silent full-table return for nationwide roles |
| Prompt example: "Estate risk is 62" | **Untrue against live data.** Max is 25.2; every row is `safe` |
| 7 report types | **Unnecessarily ambitious for a POC.** Two prove the pattern |
| Activity 17.5 report viewer page | **Correctly dropped.** The agent is the reporting surface |
| Multi-agent orchestration | **Defer.** §4.2 |

---

## 6. What this means for the 15 October POC

The architecture assessment **reduces** the POC's risk profile in one respect and **adds** work in another. Both should be visible to the client.

**Added work (was not in the R3 plan):**
- A server-side fact layer that reproduces `mappers.ts` derivations — this is the single biggest item and it was previously assumed free. **≈1 PD more**, and it is pure deterministic code, which is the good kind of work.
- Rebuild prompt examples and the eval set from live fact packs (Gate C prerequisite).
- A divergence test between `context.py` and `mappers.ts`.

**Reduced risk:** Layers 1, 2 and 4 need no model. **Tenancy containment, default-deny, disclosure and numeral fidelity are provable on 14 October whether or not the model pull succeeds.** The model only affects narrative *quality*, not a single security property. That is a much stronger position to present than the R2 draft claimed.

**Unchanged:** zero schedule float (R18), allocation ask (D8), the compliance disclosure decision (D2), and the withdrawal of the 29 Jan 2027 date (D7).

---

## 7. Recommended next actions

| # | Action | Owner | Why |
|---|---|---|---|
| 1 | Confirm the four-layer split and the one-agent decision | Victoria, Jerry | It is an architecture commitment, not a build detail |
| 2 | Decide: port `mappers.ts` to `context.py`, or accept two implementations with a divergence test | Takawira | Cheapest decision now; expensive later |
| 3 | Add `DERIVED_FROM_ESTATE_WIDE` to the disclosure model | Victoria, Compliance | Without it, provincial reports present partly-global figures silently |
| 4 | Rebuild prompt examples and eval set from live fact packs | Takawira *(Victoria supports)* | G2's "risk is 62" is untrue; it will poison generation |
| 5 | Test `scopable(model)` by introspection, not a hardcoded table | Takawira | Six unscopable tables today; the seventh would be missed otherwise |
| 6 | Decide `DERIVED_FROM_ESTATE_WIDE` disclosure wording with the Compliance Analyst | Victoria → Compliance | It appears in generated prose, so it is a legal wording question |
| 7 | Log the three bucket definitions as a master-programme defect | Jerry | Latent today, live the moment a score lands in 31–44 |

---

*Architecture assessment against `C:\sita-platform` at commit state of 6 October 2026. All database claims executed live. No source file was modified in producing this assessment.*
