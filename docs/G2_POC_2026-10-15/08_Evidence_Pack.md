# G2 — Evidence Pack

**Document ID:** G2-POC-EVIDENCE-R1 · **Owner:** Jerry Mokone (Project Manager)
**Workbook task:** `T36` · **Deliverable:** DEL-19 · **Frozen:** Wed 14 Oct 2026, 17:00
**Coverage:** Phase 13 build 7–14 October 2026 (Saturday 10 October included) · demonstration Thu 15 Oct 2026

> **Why the Project Manager owns this.** The pack certifies the build; it is assembled by someone who did not write the code it certifies. Under the delivery split that matters: Takawira carries 94.0 h of the build, Peter the verification, and this pack neither.

---

## 1. How to use this document

Every gate below is traced to a **named test that fails without the corresponding work**. A gate with no failing test is not evidenced — it is asserted.

Fill one row per gate as the build runs. Status values: `PASS` · `FAIL` · `DEFERRED`. **A `FAIL` at FREEZE means the demonstration shows a reduced claim set, never a defect carried into the meeting.**

This document is created empty on purpose. Rows are filled from test output, not from memory.

---

## 2. Gate evidence

| Gate | When | Pass criterion | Test that proves it | Status |
|---|---|---|---|---|
| **A** — RBAC and tenancy | Thu 8 Oct | Unknown role → 403 · empty scope → `expression.false()` · unknown province slug raises loudly · `NEVER_READ` raises at import | `test_ai_permissions.py` · `test_ai_scope.py` · `test_ai_capability.py` | |
| **B** — scope is structurally mandatory | Fri 9 Oct | S6 green: 100% scope-first coverage, asserted by introspection · `capability()` classifies every registered table · two roles yield different `allowed_claim_classes` | `test_ai_accessors.py` (**Peter's `T13`**, against Takawira's `T12`) · `test_ai_prompt.py` | |
| **C** — first generation **· CUT TRIGGER** | **Sat 10 Oct** | A narrative is produced from a real fact pack · 6 eval fixtures with distinct `scope_hash` · no fixture figure exceeds its own pack max | `test_ai_eval.py` · the run-sheet item 1 output | |
| **D** — the verifier is the control | Mon 12 Oct | An ungrounded numeral is discarded · a sentence holding an unheld claim class is discarded · the fallback renders from the same filtered fact view | `test_ai_verify.py` (**Peter's `T23`**) · `test_ai_generate.py` | |
| **E** — adversarial rejection | Tue 13 Oct | Scope widening, province naming and CVE injection are all rejected **at the verifier**, even where the prompt permitted them | `test_ai_adversarial.py` · `test_ai_containment.py` (**Peter's `T30`**) | |
| **FREEZE** | Wed 14 Oct, 17:00 | Lint clean · full suite green with no existing test regressed · diff is additions only · tripwire passes · integration smoke green | `ruff` · `pytest` · `git diff main --stat` · `test_ai_bucket_band.py` · `test_ai_integration.py` | |

**CUT TRIGGER — record the decision and its reason.** Gate C falls on **Saturday 10 October, worked by Takawira alone**. If `compliance_status` is dropped, this pack must record who decided, when, and why — because no peer was available to review it.

---

## 3. Non-interference proof

The claim is stated precisely, per ADR D-A8. Run these and paste the output.

```powershell
git diff main --stat
git diff main -- backend/app/api backend/app/processing backend/app/tenant.py backend/app/models frontend
# ↑ the second command must return EMPTY
```

| Assertion | Expected | Actual | Status |
|---|---|---|---|
| Lines added to `app/main.py` | exactly 1 (`include_router`) | | |
| Lines deleted anywhere | 0 | | |
| Changes under `app/api/`, `app/processing/`, `app/tenant.py`, `app/models/` | none | | |
| Changes under `frontend/` | none | | |
| `ROLES_HIERARCHY` modified | no | | |
| **Independently reviewed by** | Richard Masukume (0.5 h advisory, day 7) | | |

---

## 4. Verification-independence proof (ADR D-A9)

Two of three control claims hold; the third is restated. This table is the evidence.

| Claim | Status | Evidence |
|---|---|---|
| **1. The verifier is not written by the prompt author** | **HOLDS** | `verify.py`, `test_ai_accessors.py` (S6) and `test_ai_containment.py` authored by **Peter Rashaya**; `prompt_builder.py` and `prompts/*.v1.py` authored by **Takawira Mazando** |
| **2. Ground truth is not authored by the model author** | **RESTATED — the original wording is not used** | Scope and capability delegate to `tenant_filter()` and SQL introspection; `build_prompt` takes no `Session` and resolves no scope; live containment proof run by Peter |
| **3. The structural filter cannot be bypassed by prompt text** | **HOLDS** | `pack.serialise(allowed=claims)` — asserted by `test_ai_prompt.py` |

| Assertion | Expected | Actual | Status |
|---|---|---|---|
| `build_prompt` signature contains no `Session` / no DB handle | yes | | |
| `pack.serialise(allowed=claims)` present in the prompt path | yes | | |
| An unheld claim class is **absent** from the serialised prompt, not merely forbidden | yes | | |
| Verifier and prompt builder share no import path | yes | | |

---

## 5. Model latency table (T01 — Richard Masukume)

The token cap is decided from this table, not from rehearsal day. Re-measured across the window because T01 is charged at 0.5 h per non-Saturday day.

| `max_tokens` | p50 latency | p95 latency | tokens/sec | RSS |
|---:|---|---|---|---|
| 300 | | | | |
| 600 | | | | |
| 900 | | | | |

| Assertion | Expected | Actual | Status |
|---|---|---|---|
| `ollama list` shows `qwen2.5:3b` | yes | | |
| p50 at 900 tokens | ≤ 90 s | | |
| **`max_tokens` chosen from the measurement** | recorded above | | |
| Latency table closed into this pack | **day 9, Fri 16 Oct** | | |

**If the pull failed:** record it here and continue. The fallback serves identical numbers — pre-agreed degradation (R20), not a failure.

---

## 6. Live-data evidence

Every figure below was verified against the local `sita` instance on 6 October 2026 and is what the demonstration will show on 15 October.

| Fact | Value | Shown as |
|---|---|---|
| Risk rows | 15 283 | run sheet 1 |
| Findings in scope (`exec`) | 2 244 | run sheet 1 |
| DHA `soc` findings | 745 | run sheet 6 — tenancy containment |
| Compliance snapshots tagged `ESTATE_WIDE` | 456 | run sheet 3 |
| Compliance gaps tagged `ESTATE_WIDE` | 228 | run sheet 3 |
| **Total estate-wide rows** | **684** | the unscopable gap, declared |
| Live max `fused_score` | **25.2** (avg 7.46) | no fixture may exceed its pack max |
| Rows in the 30–45 bucket band | **0** | tripwire `T33` |
| Roles in `ROLES_HIERARCHY` | **14** | S1 enumerates, never hardcodes |

---

## 7. Demonstration record — Thu 15 October

| # | Run-sheet item | Result | Notes |
|---|---|---|---|
| 1 | `exec` → `executive_briefing`, model narrative | | |
| 2 | Envelope: authorisation, disclosure, provenance, verification | | |
| 3 | `exec` → `compliance_status`, `estate_wide` 456 | | dropped if the cut trigger fired |
| 4 | `exec` → `soc_shift_handover` → 403 | | |
| 5 | Role-aware prompting, `exec` vs `soc`, side by side | | |
| 6 | DHA `soc` vs `exec`: 745 vs 2 244, different `scope_hash` | | |
| 7 | Provincial widening → `expression.false()` → 0 | | |
| 8 | Injected CVE id → sentence discarded | | |
| 9 | `git diff main --stat`, one added line | | |

**Rehearsed on day-7 hardware within 23 minutes:** ☐ · **Timed rehearsal result:** ______

---

## 8. Acceptance checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Six gates evidenced, each by a named test that fails without the work | |
| 2 | `ruff check backend/` clean; full `pytest backend/tests` green, no existing test regressed | |
| 3 | `git diff main` is additions to `app/ai/`, `infrastructure/scripts/`, `backend/tests/` and **one** line in `app/main.py` | |
| 4 | Both report types render **with no model installed**, identical numbers | |
| 5 | Six eval fixtures with distinct `scope_hash`, no figure exceeding its own pack max | |
| 6 | `identity.users` and `audit.action_audit` provably unreachable from the agent | |
| 7 | Every generation writes both audit rows in one commit, carrying `model_id`, `model_digest`, `prompt_version`, `latency_ms`, `fallback_used` | |
| 8 | This pack signed; tag `g2-poc-freeze-2026-10-14` pushed | |
| 9 | Run sheet rehearsed end-to-end on day-7 hardware and timed | |
| 10 | **Verification-independence table (§4) complete** | |

**Not demonstrated in the POC** — stated to the client in advance, not discovered on the day: cache isolation (S5 — no cache is built in this window), independent InfoSec/tenancy review, k6 load test, model-failure chaos test, UAT, production deployment, and 6 of the 8 catalogue report types.

---

## 9. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Lead Developer, G2 | Takawira Mazando | | |
| Second Developer, G2 | Peter Rashaya | | |
| Head of AI Research (advisory) | Richard Masukume | | |
| Project Manager | Jerry Mokone | | |
| Business Analyst | Victoria Nedombeloni | | |
| Project Sponsor | Kagiso Mokgofa | | |

**Phase 2:** a **re-estimate**, not a date. The 29 January 2027 go-live in Addendum A came from a 145.5 PD estimate that assumed GPU hosting and is withdrawn.

---

*Evidence pack for G2 Phase 13. Database claims verified live against `sita` (PostgreSQL 18.1) on 6 October 2026. Task IDs are the granular register numbering from the Addendum B workbook; the `W##` numbering in `07` refers to work items, not this register.*
