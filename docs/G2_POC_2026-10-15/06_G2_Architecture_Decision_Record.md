# G2 — Architecture Decision Record

**Document ID:** G2-ADR-R1 · **Prepared:** 6 October 2026 · **Status:** decided, binding on the 6–14 Oct build
**Resolves:** §7 of `05_G2_Agent_Architecture_Assessment.md` (7 open actions)
**Method:** each decision below was taken against the codebase at commit `57e080d` plus live database queries executed 6 October 2026. Where a decision **corrects** the architecture assessment, the correction is stated explicitly.

---

## 0. Summary

| ID | Decision | Outcome | Owner sign-off |
|---|---|---|---|
| **D-A1** | Four-layer split, single agent | **Confirmed**, with one refinement to the fallback | Victoria, Jerry |
| **D-A2** | `mappers.ts` port strategy | **No port — aggregate in SQL** (Amendment A1 supersedes the narrow port). Full port was barred by G2's non-interference constraint; the narrow port is superseded because no port is needed | Takawira |
| **D-A3** | `DERIVED_FROM_ESTATE_WIDE` | **Confirmed**, scope widened to the whole fusion chain | Victoria, Compliance |
| **D-A4** | Prompt examples / eval set | **Confirmed.** Gate C prerequisite; now quantified. Owned by Takawira in the current delivery split | Takawira |
| **D-A5** | Scopability detection | **Confirmed — and the assessment's table is wrong.** Introspection alone is insufficient | Takawira |
| **D-A6** | Disclosure wording | **Drafted.** Requires Compliance ratification because it reaches generated prose | Victoria → Compliance |
| **D-A7** | Three bucket definitions | **Logged as a master-programme defect + tripwire test.** Do not fix in G2 | Jerry |
| **D-A9** *(new, 7 Oct 2026)* | **Verification independence under the current delivery split** | **Confirmed, with one claim restated.** See below | Jerry, Kagiso |

**Two of the seven decisions required correcting the architecture assessment** (D-A2, D-A5). Both corrections are material to the build.

---

## D-A9 · Verification independence — CONFIRMED, and one claim must be restated (new, 7 October 2026)

**Why this is a decision at all.** The delivery split changed after this record was written. Peter Rashaya returns and takes the three verification tasks; Richard Masukume becomes advisory. That is good for the design — the verifier now has an author who did not write the prompt — but it means one of the three original control claims is no longer literally true.

| Claim | Status |
|---|---|
| **1. The verifier is not written by the prompt author.** | **HOLDS.** `verify.py`, the S6 signature test and live S2/S3 containment are **Peter's**. The prompt builder and templates are **Takawira's**. The two must never be merged under one owner. |
| **2. Ground truth is not authored by the model author.** | **DOES NOT HOLD** in the structural sense originally claimed. Takawira owns the scope, capability, accessor and context layer **and** the prompt builder. |
| **3. The structural filter cannot be bypassed by prompt text.** | **HOLDS.** `pack.serialise(allowed=claims)` is a code boundary, not an instruction in prose. |

**Restated claim 2 — the version that is true and checkable:**

> Scope and capability **delegate** to `tenant_filter()` (`app/api/auth.py:210`) and to SQL introspection over `Base.registry`. Neither is reachable from prompt text, and neither can be widened by anything the model writes. The prompt builder only **serialises facts the fact pack already contains** — it computes no figure and resolves no scope. The containment proof is run live against the database by the **second developer**, not by the author of the prompt.

**Why it must be restated rather than quietly dropped.** Claim 2 in its original form is the kind of claim a client repeats back in a status meeting. If it is stated and then shown to be false of our own delivery split, the credibility cost lands on claims 1 and 3, which are the ones that hold. The restated version is longer, and it is checkable in ten seconds by reading `prompt_builder.py`.

**Consequence for the build:** the prompt builder (`build_prompt`) must take no `Session` and no claims-resolving call. If that signature ever grows one, claim 2 becomes false again, and it will be false quietly.

---

## D-A1 · Four-layer split and a single agent — CONFIRMED

**Decision.** Adopt `05` §4.1 verbatim: Layer 1 scope resolution, Layer 2 fact assembly, Layer 3 narrative generation (the only model layer), Layer 4 verification. One writer agent plus a deterministic verifier. No planner/retriever/critic chain.

**Why it survives scrutiny.** Layers 1, 2 and 4 contain no model, so every security property in G2 — tenancy containment, default-deny, disclosure, numeral fidelity — is provable on 14 October whether or not the `qwen2.5:3b` pull succeeds. Ollama is confirmed running (0.35.1, PID 27452) with **0 models installed**, so R20 is still live.

**Refinement (new).** The deterministic fallback must be rendered from the **claim-filtered** serialisation of the fact pack, not from the unfiltered pack:

```python
facts = pack.serialise(allowed=claims)     # ONE filtering point
model_text = generate(build_prompt(scope, report_type, facts))
fallback_text = render_template(facts)     # same facts, same filter
```

`05` §4.1 said the fallback "reads the same fact pack" — which is true of the *pack* but not necessarily of the *filtered view*. If the template renders unfiltered facts while the model sees filtered facts, the fallback becomes the wider of the two disclosures. Filtering once, upstream of both renderers, makes the invariant structural rather than a convention to remember.

---

## D-A2 · `mappers.ts` port strategy — NARROW PORT (corrects `05` §2.1)

**Decision.** Port **only the six derivations the fact pack needs** as pure functions into `app/ai/context.py`. Do not port `mappers.ts` wholesale. Guard the duplication with committed golden fixtures generated by executing the TypeScript under Node.

**Why the full port is not on the table.** `05` §2.1 offered "port the derivations to `app/ai/context.py` as pure functions" as if it were a free choice between two implementations. It is not free, because `mappers.ts` is the frontend's rendering input:

- `frontend/src/hooks/useExecData.ts:23-49` fans out to six endpoints and feeds the raw responses into `mappers.ts`.
- Consolidating to one implementation means the **frontend calls a server-side facts endpoint** — i.e. editing existing frontend files.
- That directly violates G2's own non-interference commitment (`01` §3: *"What G2 does not touch: every existing router, export, dashboard … The existing Vite frontend is not modified"*), and demo run-sheet item **21–23 is `git diff main` showing nothing existing modified**. A full port spends the demo's strongest evidence to save a few hours of Python.

**What actually gets ported.** Six functions, all in `frontend/src/data/mappers.ts`:

| Function | Line | Ported? | Note |
|---|---|---|---|
| `severityCounts` | 119 | ✅ | Unknown severities fold into `info` (line 125). Reproduce exactly. |
| `findingsByAppSeverity` | 129 | ✅ | **Silently drops** severities outside `critical/high/medium/low` (137-141). Reproduce the drop. |
| `latestRiskPerApp` | 145 | ✅ | Ties broken by first-seen (149). Reproduce. |
| `riskTrendSeries` | 154 | ✅ | Date-grouped mean, rounded to 1dp (169). |
| `gapStatusCounts` | 177 | ✅ | |
| `groupAlertsByRule` | 185 | ✅ | Key falls back to `title` when `rule_id` is empty (188). |
| `_bucket` / bucket derivation | — | ❌ | **Deliberately excluded — see D-A7.** Read `risk_scores.bucket` from the column. |

**Divergence guard.** Node **v24.12.0** is available on this machine. A generator script produces one JSON fixture per derivation from a committed sample input; pytest asserts `context.py` reproduces each fixture exactly. Fixtures are committed, so the test runs in CI without Node.

> The drop-behaviour in `findingsByAppSeverity` is the trap. Two implementations that both look correct will disagree on any `info`-severity finding. Reproduce the quirk deliberately and note it in a comment, or the next maintainer will "fix" the Python and silently change a number.

**Cost.** ≈1.0 PD, not the 1.0 PD of a full port, and it does not touch the frontend.

### Amendment A1 (6 Oct 2026, post-decision-gate) — do not port at all; aggregate in SQL

On costing the narrow port against the fact pack's actual needs, **none of the six derivations requires porting.** All six exist in TypeScript for one reason: *a browser cannot aggregate*. Server-side the same fact is a single query.

| `mappers.ts` function | Server-side equivalent | Port needed? |
|---|---|:---:|
| `severityCounts` (119) | `GROUP BY severity` | ❌ |
| `findingsByAppSeverity` (129) | `GROUP BY app_name, severity` | ❌ |
| `latestRiskPerApp` (145) | `DISTINCT ON (app_name) … ORDER BY score_date DESC` | ❌ |
| `riskTrendSeries` (154) | `GROUP BY score_date` | ❌ |
| `gapStatusCounts` (177) | `GROUP BY status` | ❌ |
| `groupAlertsByRule` (185) | `GROUP BY rule_id` | ❌ |

**Revised decision: the fact pack aggregates in SQL. There is no second implementation, so there is no divergence to test and no golden fixture to maintain.** This is strictly better than the narrow port it replaces — it removes the class of defect rather than guarding it.

**The two quirks called out above become a benefit, not a trap.** `severityCounts` folds unknown severities into `info` and `findingsByAppSeverity` silently drops them. Server-side we instead emit an explicit `unknown` bucket. The two answers will differ whenever an unexpected severity exists — and the server's is the truthful one. Record the difference rather than reproducing the quirk, so a future divergence is a visible improvement instead of a mystery.

**Corrected effort:** the `mappers.ts` port removed from the build. **−0.75 PD**, and D-A2's cost becomes **0.0 PD**.

---

## D-A3 · `DERIVED_FROM_ESTATE_WIDE` — CONFIRMED, widened

**Decision.** Add the third disclosure class from `05` §2.2. Extend its reach from `signal_compliance_penalty` alone to the **entire fusion chain**: any figure derived from a `risk_scores` row is `DERIVED_FROM_ESTATE_WIDE`, because `fused_score` contains the compliance signal.

**Verified live, 6 Oct 2026.**

```
risk_scores:  n=15 283   min=5.0   max=25.2   avg=7.46   buckets: {safe: 15 283}
latest POPIA snapshot: 82.6 on 2026-09-10
```

`app/processing/risk_aggregator.py:69-76` reads that snapshot with **no tenancy filter**. `signal_compliance_penalty = 100 − 82.6 = 17.4`, weighted **0.20** (`DEFAULT_WEIGHTS`, `app/processing/risk_engine.py:14`), contributing **≈3.5 fused points to every row in the estate** — DHA and Gauteng alike. On an average row of 7.46 that is roughly half the score.

**Widening matters for the verifier.** Tagging only the compliance signal leaves the verifier unable to make a sound attribution check, because the estate-wide component is inside `fused_score` itself, and `fused_score` is the number the narrative quotes. Tagging the whole chain lets Layer 4 implement one clean rule: *any figure sourced from `risk_scores` requires the estate-wide notice within the same sentence.*

---

## D-A4 · Prompt examples and eval set rebuilt from live fact packs — CONFIRMED

**Decision.** `01`/`05` already require this; this record fixes the shape and the budget.

**Rule.** Every figure in a prompt example, a golden fact pack or a test assertion must (a) appear verbatim in that pack, and (b) not exceed the maximum in that pack. Any example containing a figure outside its own pack is a defect, not a style issue.

**Why, with numbers.** `05` §3.4 flagged `02`'s "Estate risk is 62" as untrue. Re-verified: max is **25.2**, avg **7.46**, all 15 283 rows bucket `safe`. No application is at 62; the `critical` bucket is empty. A prompt seeded with 62 either hallucinates 62 or produces prose incoherent against a pack saying 7.5.

**Eval set shape** (Takawira, Gate C prerequisite — Saturday 10 October; Victoria's 6.0 h of BA support lands Friday 9 October):

- 3 personas × 2 report types = 6 packs: `exec` (estate), DHA `soc` (branch), Gauteng `province-soc-lead` (province).
- Per pack: the numeral set the verifier will allow, and the claim classes each role holds.
- Each pack asserts a **different** `scope_hash` from the others — a test that passes when two personas hash identically is testing nothing.

---

## D-A5 · Scopability detection — CONFIRMED, but `05` §2.3 is wrong and introspection alone is insufficient

**Decision.** Detect scopability by introspection (`department_id` + `branch_id` present on the mapped class). **But scopability is a three-way classification, not a boolean**, and there is a hard denylist that has nothing to do with scopability.

### Correction 1 — the count is wrong, and the enumeration is incomplete

`05` §2.3 states *"Six of sixteen warehouse tables cannot be scoped at all."* Executed against the live `Base` registry on 6 Oct 2026:

```
warehouse  scopable    : alerts, api_endpoints, database_inventory,
                         dispatch_log, findings, risk_scores, waf_blocks
warehouse  UNSCOPABLE  : agents, branches, compliance_gaps, compliance_snapshots,
                         connector_health, departments, provinces, slo_metrics,
                         system_metrics
outside warehouse        : staging.rejected_records · identity.users · audit.action_audit
```

**Nine of sixteen warehouse tables are unscopable, not six.** The assessment's table omitted `branches`, `departments` and `provinces` — all warehouse tables, all unscopable — and it counted `persons`, which lives in the `identity` schema, as a warehouse table. A hardcoded list built from `05` §2.3 would have been wrong on day one. This is the strongest evidence for the introspection decision, arrived at by the route the decision was meant to prevent.

### Correction 2 — three classes, because "unscopable" conflates two different things

```python
class TableCapability(str, Enum):
    SCOPABLE  = "scopable"    # has department_id + branch_id → TENANT_SCOPED
    REFERENCE = "reference"   # tenant dimension — labels only, never disclosed
    UNSCOPABLE= "unscopable"  # domain fact with no tenancy columns → ESTATE_WIDE
```

`departments`, `branches` and `provinces` are **REFERENCE**, not UNSCOPABLE. They are unscopable because they *define* the scope — a department row cannot be filtered by department membership without circularity. Tagging them `ESTATE_WIDE` would attach "this figure is computed across the whole estate" to the name of a province in every report, including provincial reports. That is a false disclosure, and it is exactly the kind of error a typed disclosure model is supposed to prevent.

They may be read **only** to resolve a display label for an id that is already inside `ReportScope`. They are never a fact, never counted, never hashed into the fact pack as a value.

```python
REFERENCE_TABLES = frozenset({"departments", "branches", "provinces"})
```

### Correction 3 — a denylist that is not about tenancy (new; the assessment did not consider this)

`identity.users` and `audit.action_audit` are unscopable, but calling them "estate-wide" mischaracterises them. They are **sensitive and must never be agent-readable**:

- `users` — `email`, `password_hash`, `display_name`, `roles`, `department_ids`, `branch_ids`, `province_ids`.
- `action_audit` — `actor` identity and the `tenant_scope` of every prior action, including other people's scopes.

Layer 2 must have **no accessor to either**. Not a filter, not a claim class, not a disclosure tag — no read path at all. An agent that can read `users` can read the password hashes and every user's tenancy assignment; an agent that can read `action_audit` can enumerate the scope of every administrator.

```python
NEVER_READ = frozenset({"users", "action_audit", "password_hash", "email"})
assert_no_never_read(models)   # executed once at import; fails fast, not at request time
```

This is the one item on the list that `05` missed entirely, and it is the most serious.

### Detection

```python
def capability(model) -> TableCapability:
    name = model.__tablename__
    if name in NEVER_READ:
        raise NeverReadableTable(name)          # deny at the door
    if name in REFERENCE_TABLES:
        return TableCapability.REFERENCE
    cols = sa_inspect(model).columns
    if "department_id" in cols and "branch_id" in cols:
        return TableCapability.SCOPABLE
    return TableCapability.UNSCOPABLE
```

Enforced by a test that enumerates `Base.registry` and fails on any table whose capability is not classified, plus a test that asserts `accessors` reference no never-read model.

---

## D-A6 · `DERIVED_FROM_ESTATE_WIDE` wording — DRAFTED, needs Compliance ratification

**Decision.** Adopt the draft below as the notice text, pending Compliance sign-off.

> Risk figures in this report are scoped to {scope}. Each figure also incorporates a compliance component computed across the whole national estate; that component is not tenant-specific and cannot be attributed to any single department.

**Why this is a compliance question and not a writing question.** The sentence reaches generated prose on every executive and compliance briefing. It asserts a limitation about the completeness of a risk figure. That is the character of text the AG attestation is built to contain, so it should carry the same weight.

**Precedent, and the gap.** `exports_ag.py:195-201` already discloses the related limitation in production:

> *"Risk profile is scoped to the caller's province; compliance snapshot/gaps are estate-wide today (snapshots carry no department_id)."*

`05` §2.4 correctly notes this is documented, not hidden — and that G2's contribution is making it *typed* rather than free text inside an attestation note. The draft above is **not** covered by that precedent: the existing wording covers tables that *cannot be read* in scope, while `DERIVED_FROM_ESTATE_WIDE` covers a figure that *is* in scope but was *computed* estate-wide. A reader of the existing sentence would not understand the new one. They need both.

**Routing.** Victoria → Compliance Analyst. Blocking for Gate C, not for Layer 2 — the class is decided and typable today; only the string is outstanding. Default if unratified: emit the class name in the envelope's `disclosure` array and no prose notice, so the typed control is never blocked on a wording approval.

---

## D-A7 · Three bucket definitions — LOGGED, not fixed; add a tripwire

**Decision.** Do not change any existing file (G2 non-interference). Log as a master-programme defect owned by Jerry, and add a tripwire test inside G2's own suite.

**The defect, restated precisely.**

| Definition | Thresholds | Location | Role |
|---|---|---|---|
| `risk_bucket` | safe ≤30 · monitored ≤70 · critical >70 | `app/processing/risk_engine.py:78` | **writes** `risk_scores.bucket` |
| `_bucket` | safe <45 · monitored ≥45 · critical ≥70 | `app/api/routers/exports_ag.py:40` | **recomputes** for the attestation |
| `_bucket` | safe <45 · monitored ≥45 · critical ≥70 | `app/api/routers/benchmark.py:38` | **recomputes** for the leaderboard |

The two recomputing definitions agree with each other and disagree with the writer for any score in **30.0 – 44.9**.

**Live status, re-verified 6 Oct 2026: zero rows in that band.** All 15 283 rows fall in 5.0 – 25.2. Today this is a data-dependent accident, not a guarantee: the moment a score reaches 31, `risk_scores.bucket` says `monitored` while the AG attestation and the benchmark leaderboard say `safe`, and a generated narrative drawing on both would assert both.

**Two responses, both in G2's own files:**

1. **Agent rule.** Read `risk_scores.bucket` from the column. Never recompute. Never mix a stored bucket with a recomputed one in a single fact pack.
2. **Tripwire.** A test that asserts `count(fused_score between 30 and 45) == 0` over live data, with a message naming the defect. It passes today and converts a silent divergence into a *detected* one without touching a single existing file. G2 does not fix the platform; G2 makes the platform tell us when the bug goes live.

**Master-programme defect entry** should record the three locations, the divergent band, the fact that current data masks it, and the risk that it activates under realistic scoring once weights or signal scaling change.

---

## D-A8 · Non-interference is not literally provable — restate the claim precisely (new)

**Decision.** The demo claim *"nothing existing modified"* cannot be true, and must be restated before it is shown to a client.

**One existing file must change.** `app/main.py:122-133` is the only place routers are registered. A `reports_ai` router needs exactly one line there:

```python
app.include_router(reports_ai.router, prefix="/api/v1")
```

There is no way to serve a new endpoint from a single FastAPI process without it. Splitting G2 into a second ASGI app on a second port would avoid the edit but costs deployment surface, a second CORS origin, and a second origin for the demo — a real regression in exchange for a cosmetic one.

**A second file can be avoided.** `app/config.py:7-46` holds the platform `Settings`, and G2 needs five AI fields. Put them in `app/ai/settings.py` as its own `BaseSettings`. `app/ai` is deliberately an isolated additive namespace, five fields do not justify a cross-module dependency, and every avoidable edit to an existing file is a risk to the one claim the demo rests on.

**Restated claim, and it is stronger than the original because it is checkable:**

> Across the POC, exactly **one line** in one existing file is added — `app/main.py`, an `include_router` registration. **Zero deletions. Zero modifications to existing logic. Zero changes to `app/api/`, `app/processing/`, `app/tenant.py`, `app/models/`, or the frontend.** The `git diff main` shown on 15 October consists solely of additions to `app/ai/`, `infrastructure/scripts/`, `backend/tests/` and one registration line.

**Why restate it rather than quietly soften it.** "Nothing existing modified" invites a client to run `git diff main` and discover the `include_router` line themselves, on a projector, mid-mechanism. A precisely-stated claim is checkable in ten seconds and survives scrutiny. A sweeping one does not.

These are now settled and should not be re-litigated during the build:

| Build item | Consequence |
|---|---|
| `accessors.py` (Day 3) | Scope-first positional arg; `capability()` gate before any query; **zero accessors for `users`/`action_audit`** |
| `disclosure.py` (Day 2) | Three classes, not two; `REFERENCE` never disclosed; `NEVER_READ` raises at import |
| `context.py` (Day 4) | Six ported derivations only; bucket read from column; `DERIVED_FROM_ESTATE_WIDE` on the whole fusion chain |
| `verify.py` (Day 5) | Attribution rule: any `risk_scores`-sourced figure needs the estate-wide notice in the same sentence |
| fallback templates (Day 5) | Rendered from `pack.serialise(allowed=claims)` — same filtered view as the model |
| eval set (Day 4, Gate C) | 6 packs, per-pack numeral ceiling, distinct `scope_hash` per persona |
| tripwire (Day 5) | Zero rows in 30–45 band, with the defect named in the failure message |
| effort | D-A2's narrow port is **cheaper** than `05` §6 estimated (no frontend change). `DERIVED_FROM_ESTATE_WIDE` wording is the only remaining unknown. **Net schedule impact ≈0.** |

**Unchanged by this record:** zero schedule float (R18), the allocation ask (D8), and the withdrawal of the 29 Jan 2027 date (D7).

---

*Architecture Decision Record for G2. All database claims executed live against the local `sita` instance on 6 October 2026. No source file was modified in producing this record.*