# G2 — RBAC-Guided Prompting: Evidence from the Live System

**Document ID:** G2-POC-EVID-R3 · **Supersedes:** R1
**Produced:** 6 October 2026 · **Method:** executed against the running system. **No mocks, no synthetic data.**
**Purpose:** establish, by test rather than assertion, what the 15 October demonstration can rely on.

---

## 1. Environment as found

| Item | Value |
|---|---|
| Database | **PostgreSQL 18.1**, `localhost:5432`, database `sita` |
| Backend | `backend/.venv` (Python 3.13), FastAPI + SQLAlchemy 2.0 async |
| **LLM runtime** | **Ollama 0.35.1 — INSTALLED AND RUNNING**, PID 27452, port `11434` |
| Models installed | **0 — a model must be pulled** |
| Ollama registry | **Reachable** (HTTP 200) |
| Disk free | **84.3 GB** |
| RAM | **15.6 GB** |
| CPU | Intel i5-11400H, 6-core, **no GPU** |
| Docker | **Unavailable** — daemon not running; native PostgreSQL used |
| `backend/app/ai/` | **Does not exist** — no G2 code written |
| Frontend | Vite + React 18, `sita-frontend`, six role dashboards |

### 1.1 Recommended model

| Candidate | Size | Fit on this machine |
|---|---|---|
| **`qwen2.5:3b`** | ~2.0 GB | **Recommended.** Strong instruction-following for its size; runs on CPU; ~900-token outputs are tractable |
| `qwen2.5:1.5b` | ~1.0 GB | Fallback if 3b latency is unacceptable on a 6-core CPU |

```powershell
ollama pull qwen2.5:3b
```

**Self-hosted satisfies G2 §12(6) — no SaaS LLM — with zero CAPEX and zero procurement lead time.**

### 1.2 The correction to R1

R1 concluded there was *"no model infrastructure of any kind"* and withdrew D6. That was wrong on the runtime question: **Ollama was installed and serving on 11434.** What was true is narrower and still matters — **no model has been pulled**, so inference is unavailable until day 1. R1's `.env` observation stands, and is itself a defect: the model endpoint should be configured, not discovered.

---

## 2. Data inventory — what the agent can report on

| Table | Rows | Scopable? | Used in POC |
|---|---:|:---:|---|
| `warehouse.risk_scores` | 15 283 | ✅ | `executive_briefing` |
| `warehouse.waf_blocks` | 3 569 | ✅ | — |
| `warehouse.api_endpoints` | 2 752 | ✅ | — |
| `warehouse.database_inventory` | 2 577 | ✅ | — |
| `warehouse.findings` | 2 244 | ✅ | `executive_briefing` |
| `warehouse.alerts` | 551 | ✅ | — |
| `warehouse.departments` | 173 | — | scope reference |
| `warehouse.branches` | 347 | — | scope reference |
| **`warehouse.compliance_snapshots`** | **456** | ❌ **none** | `compliance_status` |
| **`warehouse.compliance_gaps`** | **228** | ❌ **none** | `compliance_status` |
| `audit.action_audit` | present | — | audit sink |

**684 compliance rows cannot be scoped.** The agent reports on real, substantial data.

---

## 3. Gate 2 — tenancy scoping verified live

`tenant_filter()` (`backend/app/api/auth.py:210`) applied to `warehouse.findings`:

| Persona | Claims | Result | Rows |
|---|---|---|---:|
| `exec` | `roles=[exec]` | `None` — whole estate | **2 244** |
| `compliance` | `roles=[compliance]` | `None` — whole estate | **2 244** |
| `soc` | `roles=[soc], department_ids=[home-affairs-digital]` | `department_id IN (…)` | **745** |
| `province-soc-lead` | `roles=[province-soc-lead], province_ids=[gp]` | province-expanded | scoped set |
| `dept-admin` | **no scope** | `expression.false()` | **0** |

**Established:**

1. **Fail-closed is real.** A department role with no assigned scope returns zero rows, not the whole estate.
2. **Scope genuinely narrows** — 2 244 → 745 for one department.
3. **Province expansion works** — `gp` expands to 15 Gauteng departments.

### 3.1 Trap: unknown province slugs fail silently

`PROVINCES` uses **two-letter slugs** — `ec, fs, gp, kzn, lp, mp, nc, nw, wc`. There is no `gauteng`.

An early probe using `province_ids=["gauteng"]` returned **0 rows** — correctly, because the slug is unknown, expansion is empty, and `tenant_filter` fell through to `expression.false()`. The failure was **silent and indistinguishable from correct scoping.**

> **Build requirement:** validate province slugs against `PROVINCES` and **fail loudly** on an unknown value. Added to Gate A.

### 3.2 `warehouse.provinces` is empty — cosmetic

The table has **0 rows**, but province expansion does not read it. `PROVINCE_DEPARTMENTS` is built in-memory at import (`backend/app/tenant.py:1095-1101`) from `PROVINCES` (9) and `_PROVINCE_FUNCTIONS`, yielding **113 provincial departments** (`gp` 15, `kzn` 13, `wc` 13, `mp` 13, `ec`/`fs`/`lp`/`nw` 12, `nc` 11).

**Scoping is unaffected.** A warehouse reporting gap, not an authorisation defect.

---

## 4. `scope_hash` determinism verified

Canonical JSON of `{sorted department_ids, branch_ids, province_ids, nationwide}`, SHA-256.

| Test | Result |
|---|---|
| Order independence — `["b","a"]` vs `["a","b"]` | ✅ identical hash |
| Scope sensitivity — adding `treasury` | ✅ different hash |

Suitable as the cache-key component and as the join key across response envelope, cache key and audit row.

---

## 5. R02 / Decision 2 — corrected finding

### 5.1 Column-level proof

| Table | Columns | Tenancy columns |
|---|---:|:---:|
| `warehouse.compliance_snapshots` | `id, framework, snapshot_date, overall_score, details, total_controls, passed_controls, computed_at` | **none** |
| `warehouse.compliance_gaps` | `id, framework, control_id, domain, description, owner, severity, due_date, status, evidence_count` | **none** |

### 5.2 Behaviour per caller

| Caller | `tenant_filter()` result | Rows | Error |
|---|---|---:|:---:|
| `exec` | `None` | **456 / 456** | none |
| `compliance` | `None` | **456 / 456** | none |
| `transversal-admin` | `None` | **456 / 456** | none |
| `soc` (scoped) | raises | 0 | `AttributeError` |

### 5.3 Why

`backend/app/api/auth.py:225-244`:

```python
conds = []
if depts:
    conds.append(model.department_id.in_(depts))   # never reached for a nationwide caller
...
if is_nationwide(claims):
    return None                                    # short-circuits first
```

A nationwide caller never reaches the `department_id` access, so no `AttributeError`. `None` means no filter — every row is returned. And the three nationwide roles above are **exactly** the three the G2 §5 matrix grants `compliance_status` to.

> **G2 §3.4 frames this as an `AttributeError` crash. The crash only occurs for scoped callers, who are denied the report by Gate 1 anyway. For the intended audience the failure is silent and total: 684 compliance rows, unscoped, undeclared, no error.**

### 5.4 Consequences

1. **Typed `ESTATE_WIDE` disclosure is the only control.** No code path will ever scope these tables — the columns do not exist.
2. **Decision 2 is strengthened.** Proceed with typed, disclosed estate-wide figures; raise tenancy columns as a separate approved change to the warehouse core.
3. **Strongest demo item.** `disclosure: [{scope_class: "estate_wide", rows: 456}]` on real data shows the design surfacing its own limits — the entire claim of G2.

---

## 6. Corrections to G2 identified by this evidence

| # | G2 says | Verified reality | Severity |
|---|---|---|---|
| 1 | `tenant_filter()` *"raises `AttributeError`"* on compliance tables (§3.4) | Raises **only for scoped callers**. Nationwide callers receive the full table silently | **High** — inverts the failure mode, hides the exposure |
| 2 | *"11 roles"* (§3.1, S1) | `ROLES_HIERARCHY` defines **14**: exec, soc, appsec, dbsec, compliance, sre, transversal-admin, dept-admin, branch-admin, province-soc-lead, province-dept-admin, local-appsec, admin, operator | **Medium** — an S1 suite hardcoded to 11 passes while missing 3 |
| 3 | Model hosting an open decision | **Ollama 0.35.1 installed and running**; 0 models pulled | **Resolved** — D6 answered by self-hosting, no CAPEX |
| 4 | Province expansion implied data-driven | In-memory; `warehouse.provinces` empty and unused | Low |
| 5 | — | Unknown province slugs fail **silently** to an empty scope | **Medium** — needs loud validation at Gate A |
| 6 | Activity 17.5 — report viewer page | **Dropped by direction.** Reports are generated by the agent, not rendered on a page | Scope change |
| 7 | Project Lead "Takawira and Peter" | **RESOLVED 7 Oct: Peter Rashaya returns** to the three verification tasks (S6 scope test, `verify.py`, live S2/S3 containment). Takawira and Peter are the builders; Richard Masukume is advisory in this window. The master workbook still names Peter as Technical Lead — that now agrees | **Medium** — plan hygiene across two workbooks |

---

## 7. What this evidence supports for 15 October

| Claim | Supported | How |
|---|---|---|
| Gate 1 default-deny | ✅ | Role matrix exercised live |
| Gate 2 scopes correctly | ✅ | 2 244 vs 745; fail-closed at 0 |
| Empty scope fails closed | ✅ | `expression.false()` → 0 rows |
| `scope_hash` deterministic | ✅ | Order-independent, scope-sensitive |
| Estate-wide facts typed and disclosed | ✅ **and necessary** | 456 rows demonstrated |
| Nothing existing modified | ✅ | `git diff` against `main` |
| Self-hosted model available | ⚠️ **Runtime yes, model no** | Ollama serving; `qwen2.5:3b` must be pulled day 1 |
| CPU inference latency acceptable | ⚠️ **Unproven** | No model to benchmark until pulled |
| Role-aware prompting produces divergent text | ⏳ **Unproven** | Requires the pull; benchmarked day 1, rehearsed day 7 |

**Two claims are unproven and both depend on the day-1 model pull.** That is the honest position: the authorisation architecture is demonstrated on live data today; the generation path is proven on 6 October and frozen on 14 October.

---

*All output produced by executing against the running system on 6 October 2026. Reproducible from `backend/.env`.*
