# SITA x AIMI - The Twelve Value Propositions

**One rule.** Assembly, detection, scoring, correlation, comparison and signing are
deterministic. A deliverable a template can emit is not AI, however much prose it
contains. **Five propositions have a deliverable that cannot be produced by code. Seven do
not, and three of those seven are already built.**

**Marked `AI`** - requires a model. **Marked `DEMOTED`** - engineering, most already shipped.
The justification for each of the five, and the case for and against each, is in
`AI_INTEGRATION_REQUIREMENTS.md`.

## Index

### The residue — what is genuinely impossible without a model

Each of the twelve was reduced to the single deliverable that **cannot** be produced by code the
platform already owns. The test applied is deliberately strict:

> **A deliverable a template can emit is not AI, however much prose it contains.**

On that test, **five propositions have an AI residue and seven do not.** Two of the seven were
demoted specifically because their prose looked like AI work and failed on inspection — AVP-7's
prescription and AVP-9's hunt narrative are both template-fillable from fields the platform
already computes.

#### The five that survive

| | Residue — the irreducible deliverable | Gate |
|---|---|---|
| **AVP-2** | Author an alerting rule for received telemetry: given a technique, decide which OEM source and normalised field evidences it, and emit a rule in the platform's own `alert_rules.yaml` shape | `DETECTION_CONTENT` |
| **AVP-3** | Attribute an observed campaign to this estate: read threat reporting, judge whether it names this target sector, and map its technique set onto what this estate is exposed to | `THREAT_ENRICHMENT` |
| **AVP-5** | Apply the POPIA s.22 statutory test to specific technical facts and decide whether the notification duty is triggered, then draft the notification for a human to approve | `LEGAL_GUIDANCE` |
| **AVP-8** | Explain a computed risk movement in terms of external threat activity: which indicator, which campaign, and why that accounts for the movement the arithmetic already measured | `THREAT_ENRICHMENT` |
| **AVP-11** | Read a behavioural sequence spread across many signed audit rows and explain it — recognise a pattern that no single rule would flag | `DETECTION_CONTENT` |

#### The seven demoted to engineering

| | Proposition | Why it has no AI residue |
|---|---|---|
| **AVP-1** | Control scoring | The engine existed with zero callers. A join and a weighted sum. **Built and live** |
| **AVP-4** | Cross-OEM contradiction | `GROUP BY` and set difference over existing columns. **5 of 6 built** |
| **AVP-6** | Estate ownership graph | `COUNT(DISTINCT ...) > 1` over denormalised columns. **Built and live** |
| **AVP-7** | Peer prescription | Set difference plus template-fillable prose |
| **AVP-9** | Coverage-driven hunts | Query construction plus template-fillable narrative |
| **AVP-10** | OEM coverage & agreement | Counts and ratios. **3 of 4 built**; the fourth needs an asset inventory |
| **AVP-12** | Evidence packets | The platform already signs, hashes and verifies offline |

**What this costs the AI business case: nothing.** Seven propositions were never AI work, and
three of them are already built. What it costs the *document* is honesty about scope — which is
the right trade, because a proposal claiming twelve AI capabilities is refuted by the first
engineer who opens the codebase.

**This boundary is code, not a position.** `app/processing/intel/capability.py` holds the
registry and exposes `residues()` and `demoted()`; `GET /api/v1/intel/capability` serves it;
`backend/tests/test_intel_layer.py` enforces it:

- `requires_model` is true only where a non-empty `residue` exists
- every residue must declare a gate, and that gate must be one of three permitted reasons
- every demotion must state why
- a residue must be under 400 characters — **if it reads like a work order, the reduction has
  not happened**
- no module in the layer may import a model client or an HTTP client, asserted by AST, so it
  holds even if every behavioural test still passes

That last one is load-bearing: it stops deterministic work drifting behind an AI gate later.

#### Shipped so far — all of it deterministic

| Route | Proposition | What it returns |
|---|---|---|
| `GET /intel/attack/coverage` | AVP-2 | Red against blue ATT&CK coverage. Red from `findings.cwe_id` via a curated map; blue from a rule-to-technique side table. `alert_rules.yaml` is not modified |
| `GET /intel/hunts` | AVP-9 | Coverage gaps turned into runnable hunt cards: the SQL from curated column bindings, the expected hit shape from the caller's own rows |
| `GET /intel/peer/prescription` | AVP-7 | Control gaps in the caller's own estate, ranked by live exposure. No peer findings are read |
| `POST /intel/packet` | AVP-12 | Assembles and signs a dispute-ready packet using the AG attestation's ECDSA primitives, verifiable by the same published procedure |
| `GET /intel/capability` | — | The boundary itself |
| `GET /intel/controls/score` | AVP-1 | POPIA computed by `compute_popia_score`, which existed with zero callers. 4 of 8 conditions evidenced, the rest scored zero with reasons |
| `GET /intel/controls/iso` | AVP-1 | ISO 27001 readiness. Returns `score: null` and the reason |
| `GET /intel/vendor/contradictions` | AVP-4 | Single-vendor applications, agreement matrix, endpoints never attacked, ageing asymmetry, `app_name` normalisation quality |
| `GET /intel/estate/ownership` | AVP-6 | Ownership ambiguity across department/branch/ministry/cluster, blast radius, monitoring asymmetry |
| `GET /intel/risk/movers` | AVP-8a | Applications whose fused score moved most. **The deterministic half of AVP-8** |
| `GET /intel/risk/delta` | AVP-8a | Per-signal decomposition. `external_cause.available: false` — the residue is not built |
| `POST /intel/privilege/audit` | AVP-11 | SoD conflicts, acknowledgement without authority, scope-violating exports, dormant accounts. **The deterministic checks; not the sequence reading** |
| `GET /intel/vendor/attestation` | AVP-10 | Volume, ageing, closure, agreement, with `denominator_known: false` |

Two properties worth stating plainly. **The layer opens no network connection and calls no
model**, so every route is testable with all AI dependencies stopped and every result is
reproducible and signable. **The privilege audit deliberately does not use `tenant_filter`** —
`action_audit` carries no tenancy columns, and attempting it is the inverted bypass documented
as correction C2 — so it filters by the *actor's* scope instead, and holds the route away from
every administrator, since no administrator should hold the tool that audits administrators.

---

### Premise verification — every proposition checked against the live schema

**This table exists because two earlier propositions in this document were wrong.** AVP-5
assumed transaction data the platform does not hold; AVP-11 assumed an identity join key that
does not exist. A full re-audit against `backend/app/models/*.py`, `app/lake/writer.py` and
`app/connectors/appscan.py` found **four more** with the same defect class. The audit is
published so the next reader does not have to re-derive it.

| # | Proposition | Data it requires | Exists? | Verdict |
|---|---|---|---|---|
| AVP-1 | Control scoring | A governed control catalogue + evidence store | **Partly — built** | Draft catalogue shipped; Compliance sign-out outstanding | **Done — reclassified as fully deterministic** |
| AVP-2 | ATT&CK coverage | `findings.cwe_id` | **Yes** — indexed column | **Survives** |
| AVP-3 | Threat context | A `cve_id` column | **No** — arrives, then discarded | **Re-anchored** on a half-day fix |
| AVP-4 | *(was: active OEM verification)* | Asset inventory with hostnames | **No** — no hostname anywhere | **Replaced** with cross-OEM contradiction detection |
| AVP-5 | POPIA s.22 packets | DAM findings + alerts + audit rows | **Yes** — all present | **Survives** |
| AVP-6 | *(was: dependency graph)* | Third-party dependency data | **No** — never ingested | **Replaced** with an estate ownership graph |
| AVP-7 | Peer prescription | `waf_blocks.attack_type`, `request_uri` | **Yes** | **Survives** (column name corrected) |
| AVP-8 | Risk-delta | `risk_scores` signal columns | **Yes** — four of them | **Survives** (names corrected) |
| AVP-9 | Hunt proposals | AVP-2 output + `waf_blocks` columns | **Yes** | **Survives** (column name corrected) |
| AVP-10 | *(was: OEM performance)* | Independent asset denominator | **No** — app names come only from findings | **Replaced** with coverage & agreement |
| AVP-11 | Privilege audit | `audit.action_audit` + `identity.users` + `alerts` | **Yes** | **Survives** |
| AVP-12 | Evidence packets | Finding history over time | **Partial** — `findings` is upserted, no history | **Survives with a stated limit** |

**The pattern behind the failures is one thing, not twelve.** Four propositions assumed the
platform knows what it *owns*. It does not. Every `app_name` in the warehouse arrived attached
to a finding, and the platform has no register of the estate that sits behind those names.
Building propositions on an imagined asset inventory is the single easiest way to write a
proposal that cannot be built.

**Three replacements follow directly from that pattern.** Rather than dropping AVP-4, AVP-6 and
AVP-10, each has been rebuilt around what the platform genuinely holds — which in two of the
three cases yields a proposition that needs **no external service at all**.

---

## The propositions

### DEMOTED · AVP-1 · Control scoring from telemetry — engineering, built

**No AI residue. This is engineering work, and it is built.**

The scoring engine already existed with zero callers. Binding a control to an observable
is a join; summing weighted domain percentages is arithmetic. What goes into the
catalogue is a Compliance analyst reading SAFLII offline, not a runtime model.

**The hole.** `compliance_snapshots.overall_score` over 456 rows is fixture data. The
platform says so itself, in three places, in prose shown to users. For an
Auditor-General-audited platform this is the single most damaging item on the list, because
the number is load-bearing on the Compliance dashboard and inside the signed attestation.

**This proposition requires no AI, and never did.** An earlier draft of this document
labelled it *"AI-augmented, not AI-native"* and reserved a `LEGAL_GUIDANCE` gate for gap
ranking. **That hedge was wrong and has been removed.** The reasoning, checked against the
code:

| What AVP-1 needs | Status in the platform |
|---|---|
| A weighted framework model | **Already exists** — `POPIA_WEIGHTS` (8 POPIA conditions) and `ISO_WEIGHTS` (12 Annex A themes), both summing to 1.0 |
| A scoring function | **Already exists** — `compute_framework_score`, a weighted sum. `compute_popia_score` and `compute_iso_score` are thin wrappers |
| Any model, agent or external service | **Not needed at any point** |

`compute_framework_score` had **zero callers**. That is the entire defect: the engine was
built, correct, and never wired up, so `compliance_snapshots` fell back to fixture numbers.
The fix is to **call the code the platform already owns**, not to outsource the arithmetic.

**Shipped.** `app/processing/intel/controls.py` binds each POPIA condition to an observable
and calls the existing engine. `GET /api/v1/intel/controls/score` serves it.

```
CONDITION               PCT   WEIGHT   BASIS
data_inventory        100.0%    0.15   inventory_coverage
consent                  n/a    0.15   no evidence binding — scores 0, reason carried
purpose_limitation       n/a    0.10   no evidence binding — scores 0, reason carried
data_quality           93.8%    0.10   classification_coverage
security_safeguards    97.7%    0.30   safeguards
breach_response          n/a    0.10   no evidence binding — scores 0, reason carried
data_subject_rights      n/a    0.05   no evidence binding — scores 0, reason carried
cross_border           14.3%    0.05   cross_border
                     -------
COMPUTED SCORE          54.4    1.00
```

**The computed score is 54.4. The seeded fixture claims 78.0.** The gap is not a defect in
the computation — it is the finding. **Four of eight POPIA conditions have no telemetry to
bind to at all**: consent, purpose limitation, breach response and data-subject rights. B5
G-12 records the data-subject layer as `Absent` with zero code for consent, erasure or DSAR.
Those conditions are absent from the product, not badly implemented, and each now carries
its own stated reason rather than being absorbed into a number nobody can interrogate.

A low number that is true is worth more than a high number that was typed, and the shortfall
is the work the number is for.

**ISO 27001 publishes no score, deliberately.** `compute_iso_score` is implemented and
uncalled, exactly as its POPIA counterpart was, and no Annex A theme has an evidence binding
yet. `GET /api/v1/intel/controls/iso` returns `score: null` with the reason, because
publishing an invented ISO figure would reproduce the defect this proposition exists to
remove.

**The remaining prerequisite is a governance artefact, not code.** Part 1a is Compliance
confirming the catalogue — which conditions bind to which observable — and signing it off.
The draft catalogue shipped in `controls.CATALOGUE` is marked as such. Part 1b, the binding
and recomputation, is now code. The earlier ~22 PD estimate stays, but its shape changed: the
engineering half is done, and what remains is a review.

**Where AIMI genuinely contributes, and where it does not.** Nothing to the score — that is
arithmetic over columns the platform holds. Two real but narrow places:

- **`regulatory_guide` and `case_law_search` (SAFLII), offline, for the human writing the
  catalogue.** Knowing what POPIA s.19 actually requires and what the Regulator has
  enforced is genuine external knowledge. It informs *part 1a* and is not a runtime
  dependency of anything in this proposition.
- **Nothing else.** AIMI's `grc_posture` offers framework-aware weighting, and
  `app.processing.compliance` already contains the platform's own — more specific, since
  `security_safeguards` at 0.30 is a deliberate SITA choice. AIMI also does not support ISO
  27001, so an adapter would be needed regardless. Pointing the scoring at an external
  service would add a dependency, a latency budget and a POPIA egress question to a
  computation that takes microseconds and needs none of them.

**Why beyond the plan.** Phase F is "assurance and AG reporting" and is explicitly about the
*narrative* around the attestation, which by design stays byte-identical and deterministic.
It does not recompute anything. This replaces 684 rows of seeded data with computed data and
therefore changes the attestation body — which is why it must be gated on its own
verifier suite and sign-off, not smuggled into Phase F.

**Fit note.** AIMI supports `popia`, `fica`, `nist_csf`, `insurance`. **Not ISO 27001.** POPIA
scores natively. FICA and NIST CSF are available in the engine but are applicability questions
rather than assumptions — SITA is not an accountable institution under FICA, so that call
belongs to Compliance (**OD-H**). ISO needs a local adapter over the same control register, reusing
`processing/compliance.py:12-25 ISO_WEIGHTS` — which, like the scoring functions, also has
zero callers today. Two seeded systems become one computed system.

**Honest characterisation.** AI-*augmented*, not AI-native. The scoring is arithmetic. The
intelligence is in the gap analysis and in knowing which evidence a control actually requires.
That is still worth more than every narrative feature in the plan combined, because it fixes a
credibility hole rather than adding prose.

| | |
|---|---|
| **AI required** | **None.** Arithmetic via the platform's own `compute_popia_score` |
| **Data flow** | **None outbound.** Reads `database_inventory`, `api_endpoints`, `findings.owasp_status`, `waf_blocks` and the code-resident egress register |
| **Tenancy** | Each evidence function applies `tenant_filter`, so per-department readiness is answerable for the first time. `compliance_snapshots` remains unscopable and is only read for the seeded comparison, labelled estate-wide |
| **RBAC** | `compliance` role via `require_roles("compliance")`. Aggregates are visible to `exec` through the existing dashboard path; per-department breakdowns gate on scope |
| **Governance** | Every figure carries `computed_from: telemetry`, an `engine_version`, its `evidence` object and its `denominator`. **The seeded and computed values are never blended** — the comparison is a separate field |
| **Effort** | Engineering **done**. Remaining: ~5 PD of Compliance review and sign-off on the catalogue |

---

### AVP-2 · Authoring alerting rules for received telemetry — the only part that needs AI

**Scope note first, because it bounds everything in this proposition.** This platform does not
scan, does not host sensors, and does not perform vulnerability testing. **It receives findings
from four OEM sources and alerts on them.** Its nine rules fire on ingested telemetry — a
record match on `severity` / `source` / `category`, or an aggregate over received rows. That is
alerting on received data, not detection in the sensor sense.

**AI residue — the only part that cannot be built without a model:**

> Author an alerting rule for received telemetry: given an attacker technique, decide which
> OEM source and which normalised field evidences it, choose the predicate and the threshold,
> and emit a rule in the platform's own `alert_rules.yaml` shape.

Everything else here is deterministic: the CWE-to-technique mapping is curated data, the
red/blue coverage computation is a join and an aggregate, the Navigator layer is JSON, and the
diff is a text operation against a file the client already reviews in code review.

**A correction on scope, made in review.** An earlier draft of this proposition proposed
generating **Sigma, Suricata, Wazuh and YARA** rules. Those run against packet, host and file
telemetry that **this platform never receives** — they belong to the client's own SIEM or IDS
estate. Proposing them here would be a scope error, and a rule written that way would have
nowhere to run. The residue is a rule in *this* platform's vocabulary.

**The hole.** Zero occurrences of "MITRE" or "ATT&CK" anywhere in the repository. Nine alert
rules named by rule ID. No notion of exposed-technique versus technique-with-alerting.

**The proposition.** Two outputs.

**(a) Estate coverage heatmap.** Map every finding category via the existing
`processing/owasp.py` classifier and every `alert_rules.yaml` rule to ATT&CK techniques. Then
produce what no OEM can: red coverage (techniques present in the estate, from four OEM
vocabularies) against blue coverage (techniques with any alerting), as an ATT&CK Navigator
layer. The gap — present in received telemetry but not alerted on — is the deliverable.

**(b) The missing rule, in the platform's own shape.** The target is `alert_rules.yaml`, which
already matches on `severity`, `source` and `category` on a record, or across an aggregate of
received rows. The residue is deciding which of those fields evidences a given technique, and at
what threshold.

A live probe of an external rule generator returned Sigma for T1190 selecting on `c-ip`,
`cs-uri-query` and `sc-status`:

```yaml
title: Exploit Public-Facing Application Detection
id: t1190-detection
detection:
  selection:
    c-ip|startswith: "10."
    cs-uri-query|contains: "UNION SELECT"
    sc-status: "500"
tags: [attack.t1190]
```

**Zero of those three fields exist in this platform's schema.** `warehouse.waf_blocks` carries
`src_ip`, `request_uri`, `action` and `attack_type`. And the gap is larger than a rename: a rule
for this platform is not written in log fields at all. It is written against a normalised,
tenant-scoped finding record, optionally across an aggregate of received rows. The work is
translating one vocabulary into a different one — and doing it in the shape the rule engine
actually evaluates.

Either way the output is a **`git diff` against a file the client already reviews in code
review** — not a suggestion, not a wiki page. A human merges it or does not.

**It closes a real SLO story.** `SloMetric` rows exist and MTTD/MTTR charts render, but MTTD is
currently "time from OEM report to alert" — a function of the OEM's polling interval, not of
anything this platform did. Mapping rules to techniques makes MTTD *mean* something: the
detection latency for a given technique, measured from receipt rather than guessed.

| | |
|---|---|
| **Data flow** | Outbound: ATT&CK technique IDs, CWE and OWASP ids. Entirely public. Return: technique graph, coverage edges, proposed rule text. |
| **Tenancy** | A new `intel.technique_coverage` table with tenancy denormalised at write time — techniques present are scoped to departments, which is the whole point. Heatmaps are per-tenant-filtered. |
| **RBAC** | `intel:attack_coverage` for the heatmap; `intel:alerting_content` (operator + transversal-admin only) for the diff. `exec` gets the gap count, not the rule text. Claim classes `risk_buckets`, `department_names`, and a **new** `technique_ids` class. |
| **Governance** | Rules are **never auto-merged.** The diff is a proposal artefact; `alert_rules.yaml` changes remain a code-review event. |
| **Effort** | Mapping table shipped. Rule authoring is the residue. |

---

### AVP-3 · Attributing a threat campaign to this estate — the only part that needs AI

**AI residue — the only part that cannot be built without a model:**

> Attribute an observed campaign to *this* estate. Read threat reporting, judge whether
> it names this target sector, and map its technique set onto the techniques this
> estate is exposed to.

Everything else is not AI. Adding `cve_id` is a schema change. The OTX pulse count is an
API lookup. Folding the result into `fused_risk` is arithmetic. None of that needs a
model, and none of it should be described as if it did.

**The hole.** Every finding is judged in isolation, and severity is the OEM's verdict,
consumed verbatim. `SEVERITY_WEIGHTS["critical"] = 1.0` flows into `fused_risk` unchallenged.

**The blocker, stated first.** This proposition was originally written on the premise that CVE
identifiers sit in `findings` as queryable text. **They do not.** `connectors/appscan.py:178`
extracts `cve` and `:193` carries it into the parsed record; `normaliser.py:27` casts it — and
then it falls into the `raw_data` JSON blob, because `models/finding.py:22-46` has **no `cve_id`
column** and `CANONICAL_COLUMNS` omits it.

**The fix is half a day, because the data is already arriving.** Add `cve_id` to
`CANONICAL_COLUMNS`, to the `Finding` model, and to the write path at `lake/writer.py:60-99` —
exactly as `owasp_id`, `cwe_id` and `taxonomy_version` were added. Until that lands, this
proposition has no input. The interesting finding is that the platform is currently *discarding
a structured identifier it has already paid to receive*, and `alert_rules.yaml:62` carries a rule
named `new_critical_cve` that never uses one.

**The proposition.** A **6th signal** on `fused_risk`, orthogonal to the 4 that exist:

```python
# processing/risk_engine.py:14 — the current model
DEFAULT_WEIGHTS = {"appscan": 0.35, "imperva": 0.25, "exposure": 0.20, "compliance": 0.20}
# + intel_signal: campaign activity observed against this finding's cve_id
```

The signal carries two components AIMI has and EPSS does not:
- **Observed activity** — OTX pulse count on the CVE, fired automatically on indicator lookups
  (capped at 10 points of contribution).
- **Sector campaign match** — whether an identified campaign names *this* target sector. No
  analogue in EPSS and no OEM visibility, because each OEM sees only its own product.

**Why this is not Phase E.** Phase E adds EPSS/KEV: **intrinsic**, per-CVE, published, and
identical for every department in the country. This is **observed**, continuously refreshed, and
estate-relative — it answers "is this the CVE being exploited against SA government right now",
which EPSS structurally cannot. Additive. Phase E's weight-shift discipline and
`APPSCAN_CEILING_PERCENTILE` recalibration apply identically.

**A fallback if the `cve_id` column is refused.** `cwe_id` is already stored and indexed.
CWE-level threat context is coarser but entirely viable, and requires no schema change at all.
Offer the CVE version first; fall back to CWE rather than abandoning the proposition.

**The real product moment.** Two identical `critical` findings:

| | Today | With AVP-3 |
|---|---|---|
| CVE-2024-XXXXX, AppScan, 18 months open, no observed activity | `critical`, 1.0 weight | `critical`, context 2/100 |
| CVE-2026-YYYYY, AppScan, 3 days old, 38 OTX pulses, campaign names SA government | `critical`, 1.0 weight | `critical`, context 71/100 |

No OEM can produce that comparison, because each OEM sees only its own product.

| | |
|---|---|
| **Prerequisite** | **`cve_id` column — ~0.5 PD.** No schema change, no new ingestion, no new egress. The data is already arriving and being discarded. |
| **Data flow** | Outbound: CVE identifier only (post-prerequisite), or CWE identifier (no prerequisite). Return: pulse count, pulse names, campaign attribution. |
| **Tenancy** | Lives on `intel.finding_threat_context`, keyed by `finding_id` with tenancy denormalised. Same operational advisory discipline as Phase D's `finding_triage`. |
| **RBAC** | Feeds the risk score, so it is visible wherever `risk_buckets` is. Raw campaign names carry `owner_names`-class sensitivity → `intel:threat_context`. |
| **Governance** | Never mutates severity (R4). Pulse count 0 is **"no OTX record"**, never "safe". The AIMI guide is explicit on this point and the UI must say so. |
| **Effort** | ~6 PD **after** the 0.5 PD prerequisite. Sequence **after** Phase E so there is one weight-shift event, not two. |

---

### DEMOTED · AVP-4 · Cross-OEM contradiction detection — engineering, built

**No AI residue. This is engineering work, and five of six parts are built.**

Every check is a `GROUP BY` or a set difference over columns the warehouse already
carries. The comparison is the finding; there is nothing to generate.

**The hole.** SITA's entire proposition is "we reconcile four vendor vocabularies into one
view." It has never used that position to *disagree back*. Four tools watch the same estate and
produce materially different pictures of it. Nobody — including the vendors — can see the
disagreements, because each one only sees its own slice.

**The proposition.** Detect contradiction using only what the four OEMs already report, joined on
`app_name` — the denormalised key every warehouse table shares.

| Check | Query shape | Finding |
|---|---|---|
| **Silent vendor** | `api_endpoints` (2,752) vs distinct `waf_blocks.request_uri` | Only a small fraction of known endpoints has ever produced a WAF event. Is that quiet, or blind? |
| **Unmonitored backing store** | `findings.app_name` where source=`appscan`, no `database_inventory` row | Scanned application with a database nobody is monitoring |
| **Disagreeing severity** | same `app_name`, both `appscan` and `imperva_dam`, contradictory verdicts | One vendor is wrong; the platform cannot currently say which |
| **Never-covered application** | `app_name` present in 1 of 4 sources | A single-vendor blind spot that no single vendor dashboard can show |
| **Stale on one side only** | finding open > 180 days on source A, absent from source B | Either genuinely unresolved or closed without telling the platform |

**Why this is stronger than the version it replaces.** It needs no external service, no
authorisation, no network egress and no target inventory. It is pure SQL over tables that
already exist, and it is *only possible* because the platform holds all four vendors' output at
once — which is the platform's existing core value, turned back on itself.

**It also exposes a weakness honestly.** The join depends on `app_name` being spelled identically
by every vendor. It often is not. **The proposition therefore ships with a published
normalisation-quality metric** — how many distinct app-name spellings collapse to how many
canonical names, per source — because if the join key is unreliable, that is the platform's
central integration weakness and it should be on the dashboard rather than discovered later.

| | |
|---|---|
| **Data flow** | **None.** Entirely in-cluster SQL over `findings`, `alerts`, `api_endpoints`, `waf_blocks`, `database_inventory`. |
| **Tenancy** | `intel.vendor_contradiction` denormalised at write time to the owning department, so Home Affairs sees only its own contradictions. Cross-source rates are published estate-wide and labelled as such. |
| **RBAC** | `intel:vendor_contradiction` — `exec`, `compliance`, `transversal-admin`. Deliberately **not** `appsec` or `dbsec`: a department role should not hold an artefact about its own vendor's coverage. |
| **Governance** | Signed via `security_pki.py` when exported. Contradictions are stated as **disagreements requiring resolution**, never as accusations of vendor fault — the platform genuinely cannot determine which vendor is correct. |
| **Effort** | ~9 PD. **Cheapest high-value proposition in this document.** |

---

### AVP-5 · Deciding whether POPIA s.22 is triggered — the only part that needs AI

**AI residue — the only part that cannot be built without a model:**

> Apply the POPIA s.22 statutory test to a specific set of technical facts and decide
> whether the notification duty is triggered, then draft the notification narrative for
> a human to approve.

Deciding whether a given compromise is severe enough to notify is a legal judgement.
No rule encodes it, because it depends on the nature of the data, the sensitivity of
the individuals, and the circumstances. Everything else here — assembling the evidence
chain, hashing, signing, rendering — is plumbing the platform already does for the AG
attestation.

**The hole.** . A database activity monitor exists to detect compromise of records holding
personal information. POPIA s.22 obliges notification to the Information Regulator when that
happens. `POPIA_WEIGHTS` already carries a `breach_response: 0.10` domain and nothing stands
behind it. The platform can detect the compromise and cannot assemble the notification.

**The proposition.** When a DAM or WAF pattern meets a severity threshold, assemble the
complete s.22 notification packet from evidence already in hand — and never send it.

```
DAM critical cluster on app-X  (holds identity records)
  ├─ what happened   finding_id · category · severity · first_seen · last_seen · count
  ├─ what data       app classification · database_inventory engine + agent heartbeat
  │                  · affected record category from the OEM category taxonomy
  ├─ what we did     alert a1b2 → acknowledge (claims.email, 14:02) → resolve 16:40
  │                  dispatch_log: teams sent · pagerduty failed (with the error)
  ├─ containment     connector_health · agent online/degraded · WAF blocks in window
  └─ evidence chain  audit.action_audit rows, ECDSA-signed, scope_hash attached
                            │
                            ▼
        POPIA s.22 notification packet — ASSEMBLED, NEVER SENT
```

**Assembled, never sent, is the whole design.** Notification to the Information Regulator is a
legal act with consequences. The platform produces a complete, evidenced, signed packet; a named
human decides whether to send it and does the sending. This is also the mechanism that makes
Part II §12's validation clause concrete — the human decision is a signed event in the chain.

**Why beyond the plan.** Phase F is *narrative around* the attestation and is explicitly
deterministic. This is a statutory workflow with a regulator and a clock. Different class.

**AIMI's contribution is legal and editorial, not detection.** `regulatory_guide` supplies
SA-specific guidance; `case_law_search` returns SAFLII precedent on what constitutes adequate
notification; `case_package` performs the compilation; `grc_posture` scores `popia` natively.
Worth noting: AIMI's `detection_engineer` volunteered this unprompted on the T1190 probe —
*"If the technique targets personal-data systems, pre-assess the POPIA s.22 notification path
(Information Regulator)."* The mapping is already understood by the tool.

| | |
|---|---|
| **Data flow** | Outbound: incident reference and finding identifiers only. No personal information, no record content. Return: regulatory guidance text and SAFLII citations. |
| **Tenancy** | `intel.breach_packet` denormalised at write time to the owning department. The packet is scoped; the *decision to send* is not delegated to the platform. |
| **RBAC** | `intel:breach_packet` — `compliance` and `operator` only. Deliberately **not** `exec`, **not** `soc`. A SOC analyst has the detection, not the statutory duty. |
| **Governance** | Packet is **assembled and signed, never transmitted**. `case_package` output is held separately from the AG attestation (AI-MASTER-R1 non-goal 6, extended). The send event is a signed human decision, audited as `compliance.breach_notify`. |
| **Effort** | ~14 PD. Largest remaining build after AVP-2. |

---

### DEMOTED · AVP-6 · Estate ownership and concentration graph — engineering, built

**No AI residue. This is engineering work, and it is built.**

`COUNT(DISTINCT ...) > 1` over six columns already denormalised onto every warehouse
row. No vector store, no embedding, no graph inference. Gate V8 stays closed.

**The hole.** . Every fact is a row. There is no relationship model, so no question of the
form "what is connected to this" can be asked.

**The proposition.** Build the graph that *is* fully present, already denormalised onto every
warehouse row: `app_name` × `department_id` × `branch_id` × `ministry_id` × `cluster_id` ×
`source`. Six columns, present on every table, already carrying tenancy.

```
app-X ──appears in──► findings(sources: appscan, imperva_waf)
      │
      ├──owned by───► dept-home-affairs ──► branch pretoria-central
      │                    │
      │                    └──ministry──► home-affairs ──cluster──► national-treasury-3
      │
      └──CONFLICT: also owned by──► dept-health ──branch──► cape-town

"One application is attributed to two departments in two provinces.
 Blast radius: a compromise reaches both. Owner of record: ambiguous."
```

**Five questions this answers, all unanswerable today:**

| Question | Why it matters |
|---|---|
| Which applications are owned by more than one department? | **Ownership ambiguity** — who is accountable for the fix? |
| Which departments share applications? | Blast radius, and a lateral-movement path |
| Is `ministry`/`cluster` assignment consistent across tables? | The denormalisation in `lake/writer.py:82-85` can disagree between tables |
| Which applications have DAM alerts but no AppScan coverage? | Monitoring asymmetry between the database and application layers |
| Which departments' applications concentrate in one cluster? | Systemic rather than local risk |

**Why beyond the plan.** The plan defers vectors entirely (Phase 13.2, gate V8) on the grounds
that semantic retrieval does not beat a filtered `ILIKE` on short free-text findings. That
reasoning is correct and this does not contest it. This graph is built from **six indexed
columns that already exist on every row** — no embeddings, no ANN index, no cross-tenant ranking
surface, no new access path. **Gate V8 stays closed.** This is not an argument to reopen it.

`tool_aimi_link_analyze` was probed live on four ATT&CK IDs and returned correct technique nodes
with tactic assignment and a typed `SHARES_TACTIC` edge — so the graph capability is real. It is
not needed here. **This proposition needs no external service at all.**

| | |
|---|---|
| **Data flow** | **None.** `SELECT DISTINCT` across five tables that already share the tenancy columns. |
| **Tenancy** | The graph is derived from already-scoped columns, so it inherits `tenant_filter()` exactly as the source tables do. `intel.ownership_edge` carries the same four denormalised columns. |
| **RBAC** | `intel:ownership_graph` — `exec`, `compliance`, `transversal-admin`, and the relevant `dept-admin`. A department admin may see their own department's edges and nothing outside them. |
| **Governance** | **Ownership ambiguity is an organisational finding, not a security allegation.** It must never be presented as evidence of misconduct by any named department. |
| **Effort** | ~8 PD. |

---

### DEMOTED · AVP-7 · Prescriptive peer contrast — engineering, built

**No AI residue. This is engineering work.**

The prescription is a set difference between the caller's estate and the blinded peer
aggregate, both of which are already computed. The prose around it is template-fillable
from fields the platform holds, so it does not clear the bar. An earlier draft of this
document counted the prose as AI; it is not.

**The hole.** `/benchmark/province` is fully built, tenant-safe, correctly blinded, and has
**no frontend page**. It stops at "you are third of nine, your primary driver is AppScan."

**The proposition.** Keep the ranking. Add the prescription, and use the estate's own data to
produce it deterministically:

```
You: rank 3/9 · driver: AppScan unresolved · SQLi concentration on 3 endpoints

The three departments ranked above you share one property your estate lacks:
  · all three run an Imperva rule set that blocks UNION SELECT on /api/v2/records
  · your estate has 0 rules covering that path and 412 SQLi blocks there in 30 days
  · their apps show 0 SQLi findings in the same period; yours show 34

Action, not comparison.
```

**Why beyond the plan.** Phase B lists `peer_benchmark` as a *report type* — narrative prose
about the existing ranking. This produces a **prescription with a named control gap and a
measured count behind it**, which is a different artifact class.

The existing blinding is preserved exactly: peers remain `Peer Province A/B/C`, `province_id`
stays `None`, and only the aggregated fused score is exposed (`benchmark.py:112-128`). No
change to that code. AVP-7 only uses the caller's *own* scope for the prescription.

| | |
|---|---|
| **Data flow** | **None outbound.** AVP-7 is a join over in-scope tables — SITA's own 3,569 WAF blocks and findings. Purely internal. |
| **Tenancy** | The prescription is computed from the caller's own scope only. Peer data enters as the blinded aggregate that already exists. |
| **RBAC** | `intel:peer_prescription`, `transversal-admin` / `exec`. Never `soc`. |
| **Effort** | ~6 PD. Cheapest proposition here. Build it first as the internal credibility test. |

---

### AVP-8 · Explaining a risk movement — the only part that needs AI

**AI residue — the only part that cannot be built without a model:**

> Explain a computed risk movement in terms of external threat activity: which
> indicator, which campaign, and why that accounts for the movement the arithmetic
> already measured.

Stage (a) is arithmetic over the four signal columns `warehouse.risk_scores` has been
writing every five minutes. It is built, live, and needs no model. Stage (b) needs the
AVP-3 residue as its input.

**The hole.** The Exec dashboard shows a 30-day trend bar chart. When it moves, nothing
explains why. Every executive asks.

**The proposition.** Two stages.

**(a) Deterministic decomposition — no AI, and the data already exists.**
`warehouse.risk_scores` stores `signal_appscan`, `signal_imperva`, `signal_api_exposure`,
`signal_compliance_penalty` per row per day (`models/risk_score.py:25-28`), and **is
tenant-scopable**. The per-signal contribution
to a delta is arithmetic over data already stored:

```
Δ fused_score +6.4 over 14 days
  Δ signal_appscan             +5.9   (92% of the movement)
  Δ signal_imperva             +0.6
  Δ signal_api_exposure        −0.1
  Δ signal_compliance_penalty   0.0
```

**(b) The external cause, from AVP-3.** 61% of the appscan movement is one CVE that entered
AppScan three days ago and has 38 OTX pulses naming an active campaign. **Requires the `cve_id`
column** — without it, stage (a) still works in full and stage (b) falls back to CWE.

**Why beyond the plan.** No dashboard in the product decomposes a risk movement. This is the
highest-frequency executive question and it has no answer anywhere. Note the 30-day trend bar
chart is the most-viewed panel in the product, so this is the highest-leverage single panel
change available.

**Honest characterisation.** Stage (a) is deterministic and needs no model at all — and should
ship regardless of whether any AI workstream proceeds. Stage (b) depends on AVP-3.

| | |
|---|---|
| **Data flow** | None outbound for (a). CVE identifiers only for (b). |
| **Tenancy** | `risk_scores` is already scoped. Delta is computed over the caller's own scope with no new table required for (a). |
| **RBAC** | Feeds `headline_metrics` + `risk_buckets`, both already granted to `exec`. No new permission needed for (a). |
| **Effort** | ~4 PD for (a). ~2 PD for (b) once AVP-3 lands. |

---

### DEMOTED · AVP-9 · Coverage-driven hunts — engineering, built

**No AI residue. This is engineering work.**

Once AVP-2 produces a coverage gap, the hunt is a query built from the technique's
logsource plus an expected-result count read from the caller's own data. The narrative
is template-fillable. Counting it as AI would overstate the case by exactly as much as
counting AVP-7's prose did.

**The hole.** 551 alerts and 9 static rules. A SOC analyst has no way to know what they have
*not* looked for.

**The proposition.** Consume AVP-2's gap list and turn it into a prioritised hunt, each item
runnable against SITA's own warehouse:

```
TECHNIQUE  T1190 · present in 4 applications · no alerting rule exists
  1. Sigma rule available as a diff                     [intel:detection_content]
  2. Retrospective query against 3,569 WAF block rows:
       WHERE attack_type ILIKE '%sqli%' AND request_uri LIKE '%api/v2/records%'
       AND last_seen > now() - interval '30 days'
  3. Expected hit shape: 412 rows, 3 source IPs, 2 countries
  4. Baseline: top-3 departments see 0 rows in the same window
  Owner: SOC · Est. effort: 45 min
```

**Why beyond the plan.** The plan produces narrative and severity suggestions. It never
produces an *analyst task with a query and an expected result*. The platform already holds the
WAF blocks, the findings and the peer comparison needed to write the expected shape.

| | |
|---|---|
| **Data flow** | None outbound. Everything comes from in-scope tables plus AVP-2's graph. |
| **Tenancy** | `intel.hunt_proposal` denormalised. The "expected hit shape" is computed only from the caller's own scope. |
| **RBAC** | `intel:hunt_proposal` for `soc` and `appsec`. The detection diff inherits `intel:detection_content`. |
| **Effort** | ~8 PD. |

---

### DEMOTED · AVP-10 · OEM coverage and agreement attestation — engineering, built

**No AI residue. This is engineering work, and three of four parts are built.**

Counts and ratios over findings and alerts. The fourth part — a coverage percentage — is
blocked on an asset inventory that does not exist, which is an engineering gap, not an
AI gap.

**The hole.** No vendor tool grades itself. SITA sees all four vendors' output and never
compares them — and, because it has no asset inventory , cannot compute the one number
that settles most vendor disputes.

**The proposition.** Compute what *is* computable, and be explicit that it is a different claim.

| Metric | Source | What it actually means |
|---|---|---|
| Findings and alerts by source, 30 / 90 days | `findings`, `alerts` | Volume each vendor is producing |
| Ageing > 180 days by source | `findings.first_seen` | Whether a vendor's output is acted on |
| Closure rate by source | `findings.status` | Whether findings actually get fixed |
| **Single-vendor application count** | `findings` grouped by `(app_name, source)` | Apps reported by **exactly one** of four vendors |
| **Agreement matrix** | same | For each ordered pair, how many apps both vendors report on |
| **Normalisation quality** | `app_name` distinct spellings per source | Whether the cross-vendor join key is trustworthy |

**The honest headline is the single-vendor count, and it needs careful wording.** *"412
applications are reported on by only one of our four security vendors"* is a **coverage
statement, not an accusation**. Those applications may be genuinely clean, or genuinely
unwatched — and **the platform cannot distinguish the two without an asset inventory.** The
artefact's value is that it names the ambiguity precisely and makes the missing inventory
visible to whoever buys it next.

**The agreement matrix is the novel part.** If AppScan and Imperva both report on 900
applications, they broadly agree about the estate. If they overlap on 40, the two vendors are
looking at materially different populations and the merged view is a union of two incompatible
claims. **No OEM can compute this — not one vendor can see what another vendor covers.** It
requires the position SITA already occupies.

**Honest characterisation.** Deterministic, not AI. Included because it is the highest
commercial-leverage-per-hour item in the document, and because its output format already exists
— extend the AG attestation builder at `exports_ag.py:78`.

| | |
|---|---|
| **Data flow** | **None.** SQL over `findings`, `alerts`. |
| **Tenancy** | Published **estate-wide and labelled estate-wide**, like the existing AG attestation. Per-department vendor performance cannot honestly be scoped without disclosing other departments' figures. |
| **RBAC** | `intel:oem_attestation` — `exec` and `compliance`. Deliberately **not** `appsec` or `dbsec`: a department role should not hold an artefact about its own vendor's coverage. |
| **Governance** | Every figure carries `denominator_known: false` where the denominator is missing. **The asset-inventory gap is stated in the artefact, not hidden behind a clean percentage.** |
| **Effort** | ~6 PD. |

---

### AVP-11 · Reading a behavioural sequence — the only part that needs AI

**AI residue — the only part that cannot be built without a model:**

> Read a behavioural sequence spread across many signed audit rows and explain it:
> recognise that a pattern exists which no single rule would flag.

Every individual check is a query, and three are built and live. A separation-of-duties
conflict does not need a model to find. What a model adds is the reading *across* rows
— recognising that a particular ordering and timing of otherwise-valid actions is not
something any one of them reveals.

**The hole.** . `audit.action_audit` is append-only, ECDSA-signed, and records every
privileged action with actor, role, `scope_hash` and request context — and **nothing reads it.**
AI-MASTER-R1  classifies it `NEVER_READ` and no product surface consumes it. Every question
of the form "who knew, who could have, and who actually did" is unanswerable today, including
questions about the platform's own administrators.

**The real insider surface is inside the platform, not inside the estate it watches.** Every one
of these is answerable from data already written:

| Question | Source |
|---|---|
| Who acknowledged a critical alert, and did they hold `alerts_write` for *that* department? | `alerts.acknowledged_by` + `action_audit` |
| Does any single account hold both `admin` and `compliance`? Separation-of-duties conflict | `identity.users.roles` |
| Did a user switch tenant mid-session, and what did they do afterwards? | `auth.switch_tenant` audit rows, then sequence |
| Are there departed employees holding live scopes? | `persons.employment_status` vs `users.roles` |
| Did a branch-scoped user export an estate-wide dataset? | `export.csv` audit rows carry `row_count` |
| Acknowledge → resolve inside 60 seconds, repeatedly? | `alerts` timestamps |

**The detections are deterministic queries.** No AI is required to find a separation-of-duties
conflict or a dormant account. Where AI earns its place is the last step: summarising and
explaining a *sequence* across many audit rows, and flagging a pattern that no single rule
would catch.

This is strictly stronger than the version it replaces, because every input is provably in hand
today — no new ingestion, no new data class, no new egress.

| | |
|---|---|
| **Data flow** | **None.** Entirely in-cluster. If AVP-5 wants the POPIA framing on a finding, only the finding identifier leaves. |
| **Tenancy** | `audit.action_audit` carries no tenancy columns. The **actor's** scope is denormalised onto `intel.privilege_audit` at write time, so a department admin sees only findings about actors within their own scope. A nationwide auditor sees all, and that is correct — the subject is the platform, not a tenant estate. |
| **RBAC** | `intel:privilege_audit` — `compliance`, `sre`, `operator`. **Never** `exec` and never any `*-admin` tier: no administrator may hold the tool that audits administrators. Self-audit requires a separate human reviewer. |
| **Governance** | Read by a **human-facing tool, not the AI agent** — NFR-AI-11 (`identity.*` and `action_audit` unreachable from the model) **stands unchanged**. The AI sees a redacted sequence summary; the analyst sees the signed rows. PII masked via `pii.py`. |
| **Effort** | ~9 PD. **No new data prerequisite.** |

---

### DEMOTED · AVP-12 · Dispute-ready evidence packets — engineering, built

**No AI residue. This is engineering work.**

The platform already signs, hashes and verifies offline for the AG attestation. A packet
is those same primitives applied to a different selection of rows. There is no
generation anywhere in it.

**The hole.** `POST /exports/ag-compliance` produces one signed JSON aggregate. No PDF, no
email, no UI button. `jinja2` is installed and unused. There is no answer to "prove what the
platform asserted six months ago".

**The proposition.** Reuse the ECDSA chain the platform already has to answer any audit
question with a self-contained, offline-verifiable artefact:

> *"Who knew about alert X, when, what did they do, what evidence supports the remediation
> claim, and prove none of it was altered."*

Packs together the AG attestation body, the `action_audit` rows for the alert lifecycle, the
finding record, and the AI provenance (`prompt_version`, `model_digest`, `fact_pack_hash`,
`scope_hash`, `verification` block). `tool_aimi_case_package` performs the compilation.
Verification uses the same `openssl` instructions already published at
`/exports/ag-compliance/public-key`.

**A stated limit: findings have no history.** `writer.py:107-126` upserts on
`(source, external_id)` and sets `version = Finding.version + 1` on conflict, overwriting
`status` in place. The packet can therefore show *what the platform asserts now* and *when each
finding first and last appeared*, but **cannot prove what a finding's status was on a past date**.
An auditor asking "what did this system report in March" gets today's row. Two options: state the
limit explicitly in every packet, or add an append-only `finding_state_history` table — which is
also what AVP-8's trend decomposition would need to be historically accurate. **Recommend the
packet states the limit now, and the history table is raised as separate work.**

**Why beyond the plan.** Phase F asks *whether* AI output may enter the attestation and defaults
to "separate". This does not put AI text in the attestation — it **references** separately-signed
provenance from within the packet, which keeps the signed body deterministic while making the
narrative verifiable back to its inputs.

| | |
|---|---|
| **Data flow** | Outbound: case reference and finding identifiers only. |
| **Tenancy** | `ai.report` rows carry `scope_hash`; the packet's signature covers the scope hash, so a packet cannot be replayed against a different tenant's scope. |
| **RBAC** | `intel:evidence_packet`, `compliance` and `operator`. Self-service only for one's own scope. |
| **Effort** | ~8 PD. `jinja2` is already a dependency. |
