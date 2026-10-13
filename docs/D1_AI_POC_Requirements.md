# SITA Platform — AI Narrative Reporting
# Deliverable D1: POC Requirements Register (v1.0)

**Managing Authority:** State Information Technology Agency (SITA)
**Technical Lead:** SITA Platform Engineering
**Coordinating Lead:** Peter (Business Analyst & Governance Lead)
**Source Specification:** `docs/AI_INTEGRATION_PLAN_MASTER.md` (`AI-MASTER-R1`, 6 Oct 2026)
**Baseline Platform Register:** `docs/C1_Requirements_Traceability_Matrix.md` (R-01 … R-16) — this register continues it at **R-17**
**Architecture of Record:** `architecture-ai.html`
**Target Milestone:** POC client demonstration, **15 October 2026**

---

## 1. What this document is, and what it is not

This is the **proposed requirements list** for the AI narrative reporting capability. It exists so that the capability can be reviewed, signed off, built and tested against an agreed list — rather than against a narrative.

It continues the `R-NN` numbering of the baseline platform register so that both registers can be read as one.

> ### This is a **proof of concept**, not a production release
>
> Three consequences the reader must hold throughout, because they change what "done" means:
>
> 1. **The demonstration scope is two report types, not eight.** The catalogue target is 8; the POC delivers `executive_briefing` and `compliance_status`. The remaining six are Phase B, after the demonstration.
> 2. **The blocking work is not AI.** Phase 0 (6 items, 3.75 PD, one week) is security remediation of the *existing* platform, including one item that is **not about AI at all** — an unauthenticated outbound HTTPS proxy at `GET /admin/ipinfo`. No AI that is resident in the platform may start until it is closed.
> 3. **Runtime is CPU-only and local.** Ollama on `localhost:11434` with `qwen2.5:3b`. Zero CAPEX, zero GPU, zero procurement. This is a deliberate scope decision (correction C1) and it is why the latency budgets in §9 are tight.

---

## 2. How to read this register

| Column | Meaning |
|---|---|
| **ID** | `R-NN`, continuous with the baseline register |
| **Requirement** | What the capability must do, stated as an observable behaviour |
| **Pri** | **P1** = must pass for the 15 Oct demonstration · **P2** = must pass for Phase A/B completion · **P3** = deferred phase, recorded for traceability only |
| **Acceptance** | The test the Business Analyst can witness or verify. Not an implementation detail. |
| **Verify** | The suite or artefact that proves it |

**Standing rule:** a decision not amended by its deadline is adopted at the stated default. The programme proceeds; later amendments are change control.

---

## 3. Scope summary

| Scope block | Weeks | Calendar | Pri |
|---|---|---|---|
| **§4 POC demonstration** | 1 | 7–14 Oct build, **15 Oct demo** | P1 |
| **§5 Phase 0 — governance gate** | 1 | 19–23 Oct | P1 (blocking) |
| **§6 Phase A — platform foundation** | 3 | 26 Oct – 13 Nov | P2 |
| **§7 Phase B — narrative & briefings** | 4 | 16 Nov – 11 Dec | P2 |
| **§8 Deferred phases** | 16 | Dec 2026 – Apr 2027 | P3 |

---

## 4. POC demonstration scope — P1 (build 7–14 Oct, demo 15 Oct)

**Objective:** prove Capability 1 — narrative from live data under role-aware prompting — on **two** report types, and prove that the security properties hold **without a model running**.

| ID | Requirement | Pri | Acceptance criterion | Verify |
|---|---|:---:|---|---|
| **R-17** | **Default-deny report authorisation.** A caller may request a report type only if their role is explicitly granted it. Absence is a denial, never a default grant. | P1 | A role absent from the grant list receives a refusal. An unknown role receives HTTP 403, not an empty report. | S1 |
| **R-18** | **Frozen, hashed request scope.** Every request resolves to an immutable scope object carrying department and branch lists, a scope class, and a `scope_hash` (SHA-256 over the canonical scope tuple). | P1 | The same hash appears identically in the response envelope, the cache key and the audit row. | R-18 test, envelope assertion |
| **R-19** | **Delegated tenancy scoping.** The AI capability reuses the platform's existing scoping primitive. It must never re-implement, wrap or substitute it. | P1 | Code inspection plus S2: a scoped SOC user requesting a report sees **zero** rows whose department is outside the province-expanded set. | S2 |
| **R-20** | **Live scoping baseline.** The demonstration must use real data, and the numbers shown must match the warehouse. | P1 | `exec` sees 2 244 findings; `soc` scoped to `home-affairs-digital` sees **745**; `dept-admin` with no scope sees **0**. Max `fused_score` is 25.2 and all 15 283 rows bucket `safe`. | Live query |
| **R-21** | **Canonical fact folder.** One folder per scope, built in a single database pass through the scoping primitive. No row reaches the capability that has not passed that primitive. | P1 | Every fact in the folder carries a stable ID and a typed disclosure class. `identity.users` and `audit.action_audit` are unreachable. | S7, NFR-AI-11 |
| **R-22** | **Typed disclosure on every fact.** Every fact carries exactly one of three classes: tenant-scoped, estate-wide, or derived-from-estate-wide. No free-text disclosure. | P1 | Every entry in the envelope's `disclosure` array is one of the three typed values. | NFR-AI-12 |
| **R-23** | **Estate-wide compliance data is labelled, never filtered.** The 456 `compliance_snapshots` and 228 `compliance_gaps` rows have no tenancy columns. They must be presented as estate-wide and attributed as such in the prose. | P1 | A national `exec` report containing compliance figures carries the estate-wide disclosure class **and** the prose says so. No compliance figure appears without it. | R-42, R-AI-11 |
| **R-24** | **Scope-first accessor signature.** Every accessor takes scope as its mandatory first positional argument. | P1 | Signature inspection of the accessor module: 100% compliance. An accessor that omits scope cannot be called. | **S6** |
| **R-25** | **Prompt is not the control.** The prompt states the restriction; an independent verifier enforces it. The prompt text is not a security mechanism. | P1 | With the prompt deliberately weakened, output violating a restriction is still rejected by the verifier. | S9 |
| **R-26** | **Numeral fidelity, 100%.** Every figure in generated prose must exist in the fact folder. No tolerance. | P1 | Extract every number from the narrative; 100% are members of the folder. Any ungrounded figure discards the output. | **S8**, NFR-AI-04 |
| **R-27** | **Claim-class enforcement.** A role may be permitted to *request* a report but not to see everything in it. Sentences containing unheld classes are discarded. | P1 | An `exec` narrative contains zero occurrences of `CVE-\d{4}-\d+`, alert UUIDs, owner names or rule IDs. | **S4** |
| **R-28** | **Scope non-escalation.** A scoped user attempting to name another province receives nothing widened. | P1 | Verification rejects; the empty result is an empty result, **never** estate-wide. | **S3** |
| **R-29** | **Four-check verifier, discard on failure.** Numeral fidelity, claim class, scope containment, attribution. Any failure returns a deterministic template and **never** model text. | P1 | Each of the four checks has a failing fixture that provably discards the draft. | S4, S8, S3, R-42 |
| **R-30** | **Deterministic fallback.** With the model unavailable, the capability must serve a deterministic template over the **identical** fact folder. | P1 | With Ollama stopped, the report renders and its numbers are identical to the model path. The response states `fallback_used: true`. | Fault injection, NFR-AI-07 |
| **R-31** | **Identical fact view, proven structurally.** The fallback and model paths read the same folder — asserted by object identity, not by comparing outputs. | P1 | Identity test passes. Two independently computed figures that merely agreed would **fail** this requirement. | NFR-AI-13 |
| **R-32** | **Adversarial rejection at the verifier.** Prompt injection through free-text warehouse fields, scope-widening attempts and disclosure-bait must be rejected at the verifier even where the prompt permitted it. | P1 | All adversarial fixtures rejected at the verification layer, not by prompt wording. | **S9** |
| **R-33** | **Full role matrix.** All **14** roles in the role hierarchy are enumerated and tested against every report type in scope. | P1 | A change to the role count fails the suite. Hardcoding a subset of roles fails the suite. | **S1**, correction C3 |
| **R-34** | **Bucket-divergence tripwire.** Three baseline implementations bucket risk differently (≤30 vs <45). The divergence band must be detected, not assumed absent. | P1 | Tripwire asserts 0 rows in the 30–45 band. **Known:** 0 rows live in the band today, so this is latent, not harmless. | **T33**, NFR-AI-15 |
| **R-35** | **Loud failure on unknown geography.** An unrecognised province or scope slug returns a named error, never a silent empty result. | P1 | A probe using a full name (e.g. `gauteng`) rather than the slug (`gp`) fails loudly. An empty result is always distinguishable from a mis-typed parameter. | NFR-AI-14 |
| **R-36** | **Disclosure not optional in the payload.** The disclosure array travels with the response so no downstream consumer can present estate-wide figures as scoped. | P1 | `disclosure` is absent never; an empty array is not accepted as a substitute. | Envelope assertion |
| **R-37** | **Provenance recorded.** Model identity, digest, prompt identity and version, and generation time are recorded on every narrative. | P1 | Every row in the AI ledger carries model digest and prompt version. An audit assertion fails the build otherwise. | NFR-AI-08 |
| **R-38** | **Example prompts rebuilt from live data.** Prompt examples and evaluation fixtures must be generated from live fact folders. | P1 | No example or fixture contains a figure that is not present in live data. **Known:** the prior plan's example figure of 62 does not exist live (max is 25.2) and would teach the model to produce 62. | Correction C4 |
| **R-39** | **Independent verification authoring.** The verifier and the scope-containment proofs must be authored by someone other than the prompt author. | P1 | Delivery record shows the verifier, the signature test and the containment proofs were produced against code they did not write. | Delivery record, D-A9 |
| **R-40** | **Non-interference, restated precisely.** The integration adds **one** router registration line and **zero** deletions, plus an enumerated set of security fixes. | P1 | Exactly one added line in the application entry point. No deletions. No changes to the pipeline, the models or the frontend in the demonstration scope. | Code diff |
| **R-41** | **Proven claims, not asserted claims.** The three load-bearing claims must each be demonstrable on a machine with no model installed. | P1 | Layers 1, 2 and 4 execute and pass their tests with the model runtime stopped. | S2, S6, S8 with model stopped |

---

## 5. Phase 0 — Governance gate (19–23 Oct) — P1, **BLOCKING**

**No AI that is resident in the platform may begin until these six items are closed.** Total 3.75 PD. This is remediation of the existing platform; **item 1 is not an AI finding.**

| ID | Requirement | Pri | Acceptance criterion | Verify |
|---|---|:---:|---|---|
| **R-41a** | **Remove the unauthenticated outbound proxy.** `GET /admin/ipinfo` takes no auth dependency and issues a live external HTTPS request. | **P1** | The route is gone. A CI rule fails the build if any route can reach an external host without an explicit egress allow-list entry **and** an auth dependency. | Exit criteria |
| **R-41b** | **Make the audit trail genuinely immutable.** `audit.action_audit` is currently append-only by convention only — `CREATE TABLE` plus two indexes, with no trigger, rule or revoke. | **P1** | `UPDATE` and `DELETE` against the table are rejected **at the database**, not merely discouraged in application code. | Exit criteria |
| **R-41c** | **Reusable audit helper.** Alert acknowledge/resolve, user CRUD and connector reset are currently unaudited. | **P1** | Every privileged mutation writes an audit row, verified by test. | Exit criteria |
| **R-41d** | **Route self-test for scoping.** Scoping is opt-in per query with no middleware, so no test can currently prove every data route is scoped. | **P1** | A startup self-test enumerates routes and **fails the build** if a new data route omits the scoping primitive. **This is the hard prerequisite for the analyst copilot.** | Exit criteria |
| **R-41e** | **Consolidate risk-bucket definitions.** Three implementations disagree for scores in 30.0–44.9. | **P1** | One implementation. The other two delegate to it. | Exit criteria |
| **R-41f** | **Deactivation takes effect within one request.** The token validator trusts the JWT, so a revoked role survives until token expiry (12 h default). | **P1** | Deactivating a user takes effect within one request. | Exit criteria |

> **Note for the reader:** G1's three credential-purge items (P0-1/2/3) are **closed as not-applicable**. Verified against the full git history of every branch: the files were never committed, `git ls-files` returns empty for the relevant patterns, and all three are gitignored. No credential rotation is required on the evidence.

---

## 6. Phase A — Platform foundation (26 Oct – 13 Nov) — P2, 11.5 PD

| ID | Requirement | Pri | Acceptance criterion | Verify |
|---|---|:---:|---|---|
| **R-42** | **Mandatory pre-egress redaction gate.** No code path from narrative assembly to the model call may bypass it. | P2 | 0 PII egress across the synthetic corpus in CI. Redaction emits a record of everything it removed. | **S10**, NFR-AI-05 |
| **R-43** | **Redaction positioned outside the gateway.** A gateway-provider change must not be able to bypass it. | P2 | Replacing the gateway provider leaves the redaction gate in the path. | Design + test |
| **R-44** | **Digest-pinned model registry.** Model identity is a digest, not a tag. | P2 | Re-pulling a tag cannot silently change behaviour. Model and prompt identity recorded on every request. | NFR-AI-08 |
| **R-45** | **Evaluation harness as a release gate.** Golden fact folders gate any model or prompt change in CI. | P2 | A model change that fails the golden set cannot be released. Closes two drift risks at once. | CI gate |
| **R-46** | **Observability for inference.** The existing metrics module is a no-op stub. | P2 | Request count, latency, token usage and circuit state are visible, with latency measured against the stated budgets. | `llm_*` collectors |
| **R-47** | **Startup misconfiguration guard.** | P2 | A non-development environment with inference enabled but no cluster-local endpoint or pinned digest **fails at startup**, not at first request. | Exit criteria |
| **R-48** | **Narrative cache with five-part key.** Role, scope hash, fact-folder hash, prompt version, model digest. | P2 | The same facts read by a different scope produce a different key. | **S5**, NFR-AI-06 |
| **R-49** | **Cache isolation proven before use.** | P2 | Generating as a scoped user and replaying the key as a wider user yields a **cache miss and no cross-serve**. | **S5** |
| **R-50** | **Per-tier kill switch.** | P2 | Inference can be disabled for a tier **without a deployment**. | Exit criteria |

---

## 7. Phase B — Narrative & briefings (16 Nov – 11 Dec) — P2, 15.5 PD

| ID | Requirement | Pri | Acceptance criterion | Verify |
|---|---|:---:|---|---|
| **R-51** | **All eight report types render.** The POC delivers 2; the catalogue target is 8. | P2 | All 8 render **offline and online, with identical numbers.** | Exit criteria |
| **R-52** | **Every figure traceable to a fact folder.** | P2 | A reader can retrieve the exact folder a narrative was written from. | `/grounding` |
| **R-53** | **Third reporting mode, existing switch.** The AI narrative is a third state of the existing overlay switch, not a new page or route. | P2 | Zero route changes. The control mounts through the existing header slot on all six dashboards and inherits each dashboard's role gating. | Code review |
| **R-54** | **Existing explanatory overlay unchanged.** | P2 | The narrative renders through the existing sanitising overlay, which is **not modified**. This is a literal exit criterion, because it is the injection surface. | Exit criteria |
| **R-55** | **Existing fixed visuals unchanged.** | P2 | All dashboard widgets continue to render from the existing data path. The AI capability does not replace, restyle or re-source them. | Visual regression |
| **R-56** | **Export of generated reports** to CSV and PDF. | P2 | Export available for all 8 types. | Exit criteria |
| **R-57** | **Monitoring surface stays numeric-only.** Infrastructure monitoring must never be given a model endpoint. | P2 | The number on a monitoring panel is the number in the metric. No generated prose appears in any alerting surface. | Design rule |
| **R-58** | **Every figure traceable to a named source.** | P2 | No figure appears in a narrative that cannot be resolved to a row in the fact folder it claims. | `/grounding`, S8 |

---

## 8. Deferred phases — P3, recorded for traceability only

**Not committed to a date. Recorded so the register is complete and nothing is quietly re-added later.**

| ID | Requirement | Phase | Why deferred |
|---|---|---|---|
| **R-59** | **Analyst copilot** — intent schema, allowlisted query compiler, streaming with query-plan display. No free-form text-to-SQL, ever. | C (6 wk) | Highest-risk capability. **Must not start before the route self-test (R-41d) lands**, because it is the one place a scoping defect becomes an interactive leak rather than a report. |
| **R-60** | **Query compiler bounds** — explicit field allowlist, enum validation, date-range and row-count caps, k-anonymity floor. | C | Deterministic bounds only; no free-text query surface. |
| **R-61** | **Finding triage assist** — advisory suggestions on normalised findings. | D (5 wk) | Out-of-band. Must never mutate finding severity, which is Auditor-General-audited. |
| **R-62** | **Confidence floor and human oversight** — sub-threshold suggestions not surfaced at all; every accept/reject written to both a triage table and the audit trail. | D | Over-trust risk rated High/High; mitigated by advisory-only design and a mandatory feedback loop. |
| **R-63** | **Labelled decision dataset.** | D | Accumulate toward the ≥2 000 labelled decisions that make any future fine-tuning viable. Fine-tuning is forbidden before this exists. |
| **R-64** | **EPSS/KEV as a fifth risk signal**, with documented and regression-tested weight shift. | E (3 wk) | A deterministic weight change, not a model call. Requires the verifier to already exist, because it changes what counts as estate-wide. |
| **R-65** | **Assurance and Auditor-General reporting position.** | F (2 wk) | Resolves whether generated narrative may appear in an Auditor-General-facing artefact. **Default: separate and advisory-only.** The attestation remains deterministic and byte-identical unless explicitly amended. |
| **R-66** | **Vector retrieval dataset.** | 13.2 (deferred) | Blocked behind an empirical gate: *does semantic retrieval beat a filtered substring search on this corpus?* Corpus is 2 244 findings with short free-text fields; 112 of 172 departments hold fewer than 5 findings; a k-anonymity floor of 5 would suppress two thirds of it. A second access path also multiplies tenancy risk until the first is proven under attack. |
| **R-67** | **Model serving ownership.** 0.5 FTE MLOps engineer for serving, evaluation CI and drift. | A (fund) | **Nobody currently owns model serving.** Unfunded, the copilot phase slips. Highest-leverage non-technical item in the programme. |

---

## 9. Quality attributes — measurable targets

| ID | Attribute | Target | Verified by |
|---|---|---|---|
| **R-68** | Narrative latency, warm | ≤ 8 s at 95th percentile | Latency histogram |
| **R-69** | Narrative latency, cold | ≤ 20 s at 95th percentile | Latency histogram |
| **R-70** | Cross-tenant leak rate | **0** | Scope-escape suite |
| **R-71** | PII leak rate | **0** across the redaction corpus | Redaction corpus, CI |
| **R-72** | Numeral fidelity | **100%** — any ungrounded figure discards the output | Verification suite |
| **R-73** | Availability | An inference failure must not degrade any dashboard | Fault injection |
| **R-74** | Human oversight | Every AI recommendation traceable to a **named decider** | Audit trail assertion |
| **R-75** | Model reproducibility | Model and prompt pinned by digest and version, recorded on every request | Audit assertion |

---

## 10. Prompt-driven reporting — P2 (adds flexibility without widening access)

**Requested capability:** the user prompts for the specific report they want from the fact folder, rather than selecting from a fixed list. Five design gaps this opened are closed below.

| ID | Requirement | Pri | Acceptance criterion | Verify |
|---|---|:---:|---|---|
| **R-76** | **Complete claim map for all 14 roles.** Nine roles had no claim set at all. | **P2** | All 14 roles resolve to a claim set **derived from their existing read permissions**, not asserted alongside them. A claim can never exceed the permission it rests on. | R-33 |
| **R-77** | **Permission wildcard ≠ claim wildcard.** Two roles hold an all-permissions grant. | **P2** | Holding a wildcard grant confers **no** claim class implicitly. Claim sets resolve explicitly. Widening any row requires Compliance approval **before** implementation. | S4, Compliance sign-off |
| **R-78** | **Unknown role resolves to the empty set**, never to a default. | P2 | An unrecognised role receives 403 and an empty claim set. | S1, S4 |
| **R-79** | **Bounded selection step.** A prompt selects from the fact folder; it cannot widen it. | P2 | Selection returns **fact identifiers only** — never rows, never unfiltered text. Every returned identifier is a member of the folder it addresses. | Set membership |
| **R-80** | **Quality and safety axes kept separate.** Emphasis is not policed; falsity is. | P2 | Selecting a low-signal figure over a high-signal one is permitted (bad brief, not a security event). Selecting a figure not in the folder is impossible. | R-26, R-79 |
| **R-81** | **The catalogue becomes editable seeds, not permissions.** | P2 | The 8 catalogue entries are offered as starting points the user may modify. Seed availability is derived from the claim map and is **never a grant**. Editing a seed beyond its original scope does not widen the claim set. | R-76 |
| **R-82** | **The prompt is audited.** | P2 | The ledger stores the redacted prompt as submitted — including the user's edits, not the pristine template — plus the prompt source, the resolved claim set and the selected fact identifiers. Without this a narrative cannot be reproduced or reviewed. | Audit assertion, R-75 |
| **R-83** | **Redaction covers input.** The user prompt is untrusted text. | P2 | It is scrubbed before it is persisted and before it is placed in any prompt. | S10 |
| **R-84** | **Free-text prompting is gated on the widened claim-permission suite.** | **P2 gate** | With fixed templates the template constrained the output shape. Free text leaves the claim filter as the **only** control. The claim-permission suite must be widened to arbitrary prompts from every role and be **green before** free-text prompting is enabled. | **S4 (gated)** |
| **R-85** | **Prompt-extraction returns nothing.** | P2 | A prompt asking the capability to reproduce its instructions, claim list or claim-set contents returns none of them. | S4 |

**Non-negotiable across R-76 … R-85:** free-text prompting widens **what may be asked**, never **what may be seen**. The model still receives no row that has not passed the scoping primitive.

---

## 11. Explicitly NOT in this POC

Stated so they are not quietly added later.

| ID | Exclusion |
|---|---|
| **R-86** | **No free-form text-to-SQL, ever.** Intent schema plus an allowlisted compiler only. |
| **R-87** | **No autonomous change** to finding severity, risk scores or alert suppression. |
| **R-88** | **No AI inside the ingestion or dispatch hot path.** |
| **R-89** | **No fine-tuning** before the evaluation harness and ≥2 000 labelled decisions exist. |
| **R-90** | **No raw finding payload to any model.** Redaction is a hard gate. |
| **R-91** | **No AI text inside the Auditor-General attestation** without passing the verifier and an explicit approved change. |
| **R-92** | **No externally hosted LLM service.** Self-hosted; sovereign cloud only as disaster recovery, behind the same redaction gate. |
| **R-93** | **No default-allow.** A role absent from the grant list gets nothing. |
| **R-94** | **No scope held in prompt text.** The prompt discloses scope; code enforces it. |
| **R-95** | **No modification to the role hierarchy.** An additive namespace only. |
| **R-96** | **No claim class outside the 14-role map** — including for a role holding a permission wildcard. |
| **R-97** | **No AI-generated chart geometry.** Components decide how to draw; the fact folder decides the numbers; the model decides only which verified figures to feature and how to describe them. Geometry is not verifiable by set-membership, so it is not delegable to a model. |

---

## 12. Assumptions and constraints — for validation, not acceptance

| # | Assumption or constraint | Validate with | If it fails |
|---|---|---|---|
| **A-1** | A local, private inference runtime is confirmed for the demonstration. | Richard, Kagiso | Overturning it adds a redaction build task, a gateway-provider abstraction and a blocking data-protection review, and retires the CPU latency risk |
| **A-2** | Latency targets are achievable on CPU-only hardware. | Measured day 1, not rehearsal day | Fix the token cap on measured latency on day 1; rehearse on day 7 |
| **A-3** | A 0.5 FTE MLOps engineer is funded. | PM | Copilot phase slips |
| **A-4** | Compliance signs the 9 newly-derived claim rows. | Compliance Analyst | Those roles receive nothing (default-deny) — safe but visibly unavailable in a demo |
| **A-5** | The demonstration scope is two report types. | Client, at Gate C | Pre-agreed cut trigger: drop `compliance_status` if behind schedule at Gate C |
| **A-6** | The single-person Saturday on 10 Oct is accepted, or overtime is approved. | Jerry, Kagiso | Stated, not hidden — the lead developer is at 168% of calendar with a 38 h overtime load |
| **A-7** | Phase 0's revealed debt does not move the go-live date. | PM | Default is no change |

---

## 13. Traceability index — requirement to proof

| Proof suite | Proves | Requirements |
|---|---|---|
| **S1** Role matrix | All 14 roles × report types; unknown role → 403; role-count change fails the suite | R-17, R-33, R-78 |
| **S2** Scope containment | Scoped request returns zero out-of-scope rows | R-19, R-70 |
| **S3** Scope non-escalation | Cross-province attempt yields empty, never estate-wide | R-28 |
| **S4** Claim permission | Zero unheld-class artefacts; claim set is a subset of the role's entry; wildcard confers nothing; prompt extraction returns nothing | R-27, R-77, R-84, R-85 |
| **S5** Cache isolation | Different scope hash → cache miss, no cross-serve | R-48, R-49 |
| **S6** Structural enforcement | Scope is the first positional parameter of every public accessor | R-24 |
| **S7** Capability classification | No table escapes classification; identity and audit tables raise | R-21 |
| **S8** Numeral fidelity | 100%; any failure discards the output | R-26, R-72 |
| **S9** Adversarial | Rejected at the verifier even where the prompt permitted it | R-32 |
| **S10** Redaction | 0 PII egress | R-42, R-43, R-83 |
| **T33** Bucket tripwire | 0 rows in the 30–45 divergence band | R-34 |
| **Identity** | Fallback and model read the same folder, by identity | R-30, R-31, R-73 |
| **Grounding** | Exact fact folder retrievable per narrative | R-52, R-58, R-82 |

---

## 14. Decisions required from the client

| # | Decision | Owner | Needed by | Default if not amended |
|---|---|---|---|---|
| **D-1** | Accept the lead developer's 38 h overtime and the single-person Saturday, or cut the second report type at Gate C | Jerry, Kagiso | **Gate C, Sat 10 Oct** | Cut at Gate C |
| **D-2** | Confirm the baseline support hours land entirely on the planned day | Jerry | **Day 1, Wed 7 Oct** | Confirm as planned |
| **D-3** | Is generated output permitted inside an Auditor-General artefact, or advisory-only? | AG liaison + Compliance | Phase F | **Separate** |
| **D-4** | Brief the restated non-interference claim and the restated verification-independence claim | Jerry | Day 4 | — |
| **D-5** | Wording of the derived-from-estate-wide disclosure class | Compliance | **Gate C, Sat 10 Oct** | Typed class in the envelope only, no prose |
| **D-6** | Fund the 0.5 FTE MLOps engineer | PM | Phase A | Copilot phase slips |
| **D-7** | Is a model trained on accepted triage decisions a "decision" requiring its own governance approval? | Compliance Analyst | Phase D | Treat as yes |
| **D-8** | Sovereign-cloud region for the disaster-recovery endpoint | DevOps + Compliance | Phase C | No DR endpoint |
| **D-9** | Does Phase 0's revealed debt change the go-live date? | PM | Immediate | No change |
| **D-10** | Scope isolation: separate reporting database or schema in the main database | Data Architect, DevOps | **POC day 1** | **Schema in the main database** — a second store would break audit atomicity |
| **D-11** | Private local inference runtime confirmed for the POC? | Richard, Kagiso | **POC day 1** | **Local private runtime** |

---

## 15. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Business Analyst | Peter Rashaya | Requirements complete and correctly scoped for a POC | |
| Technical Lead | Takawira Mazando | Requirements buildable within the stated window | |
| Head of AI Research | Richard Masukume | Model runtime, latency assumptions, gate review | |
| Compliance Analyst | — | Claim map, disclosure wording, governance items | |
| Project Manager | — | Capacity, funding, calendar | |
| Client representative | — | Demonstration scope accepted | |

> **Note on the claims being made.** The three load-bearing claims — no unscoped row reaches the model; the prompt is not the control; a missing model changes no security property — are each demonstrable **with the model runtime stopped**. If they cannot be demonstrated that way, they are not claims, and the demonstration should not proceed.

---

*Deliverable D1 · AI POC Requirements Register v1.0 · derived from `AI-MASTER-R1` (6 Oct 2026) · continues `C1` at R-17 · 97 requirements, 11 non-negotiable exclusions · architecture of record `architecture-ai.html`*
