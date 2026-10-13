# AI Integration Requirements — SITA Consolidated Security Reporting

**Document ID:** AIR-R1 · **Version:** 1.0 · **Date:** 12 October 2026
**Prepared for:** Executive approval · **Classification:** Internal — Commercial in Confidence
**Baseline:** `sita-platform` commit `eca4852` · **Status:** For decision

---

## 1. Decision sought

Approval to integrate **five AI-assisted security capabilities** into the platform, supplied
under an enterprise agreement with AIMI, on the terms in §8.

**No approval is sought for the deterministic work described in §7.** That work is either already
built and in production, or is ordinary engineering with a known cost. It is listed here only so
the committee can see the boundary between the two and is not being asked to fund it as AI.

---

## 2. Executive summary

The platform ingests security telemetry from four OEM sources, reconciles six vendor
vocabularies into a single versioned taxonomy, fuses the result into a tenant-scoped risk score,
and serves six role-scoped dashboards with a cryptographically signed compliance attestation.

**It does not scan, does not host sensors and does not perform vulnerability testing.** It
receives findings from its OEM sources and alerts on them.

**That pipeline is deterministic and it works.** An assessment of twelve proposed AI capabilities
found that **seven of the twelve need no AI at all** — they are arithmetic or database queries
over data the platform already holds. Three of those seven are already built and in production.
This document requests funding for the remaining **five**, each of which has a deliverable that
cannot be produced by code.

**The five capabilities are:**

| | Capability | Delivered to |
|---|---|---|
| **R1** | Authoring alerting rules for received attacker techniques | Security operations |
| **R2** | Attributing active threat campaigns to this estate | Risk owners, executives |
| **R3** | Judging whether a data breach is notifiable under POPIA s.22 | Compliance, legal |
| **R4** | Explaining what caused a change in the risk score | Executives, department heads |
| **R5** | Reading privileged-action sequences for insider risk | Compliance, internal audit |

**Three properties make this a low-risk first AI deployment:**

1. **All five are advisory.** None can alter a severity, a risk score, a bucket, an alert status
   or a block. Every one produces a recommendation for a named human to accept or reject.
2. **Two touch a regulator and cannot act.** R3 assembles a statutory notification and stops.
   The platform has no transmit capability and never will under this agreement.
3. **The deterministic foundation is already built.** 33 of 43 deterministic components are
   shipped and live. Adding AI is an additive change; a model failure degrades one capability,
   not the platform.

**The strongest single justification** is in R1 and it was verified against the live data model:
detection rules generated from an external source select on three fields that **do not exist in
this platform's schema** — zero of three match. A rule built by the engineering route and merged
in good faith is inert. It loads, validates as configuration, matches nothing, and no test in the
current suite detects the condition.

---

## 3. Background

### 3.1 What the platform does today

| Capability | Status |
|---|---|
| OEM ingestion (AppScan, Imperva DAM/WAF, API Security, compliance feed) | Operational, resilient |
| Cross-source normalisation to OWASP Top 10 2021 with CWE mapping | Operational, versioned |
| Fused risk score, 4 signals, tenant-scoped | Operational |
| Alert rules, dedup, severity-gated dispatch | Operational, 9 rules |
| Role-scoped dashboards across 14 roles | Operational |
| Auditor-General attestation, ECDSA P-256 signed | Operational |
| Multi-tenancy (province → department → branch) | Operational, scoped on every query |

### 3.2 What it does not do

| Gap | Consequence |
|---|---|
| No external threat intelligence of any kind | Findings are judged in isolation; an actively exploited vulnerability and a dormant one score identically |
| No attacker-technique framework (MITRE ATT&CK) | The estate cannot state which attack methods apply to it or which it would notice |
| No alerting-rule authoring | Coverage is fixed at 9 hand-written rules covering 11 techniques; no new weakness class is ever covered automatically |
| No breach-notification workflow | The platform can detect a compromise and cannot produce the statutory notification POPIA s.22 requires |
| No causal explanation of risk movement | The executive trend line moves with no stated cause |
| No insider-behaviour analytics | The signed, append-only audit trail is written and never read |

---

## 4. Requirements

Each requirement states the deliverable and the reason a model is required rather than an
engineering build. Reasons are classified:

- **V** — verified against the codebase, the schema or a live probe
- **S** — structural: a property of the problem class, not of this implementation
- **E** — economic: the engineering cost scales with something that grows

---

### R1 · Authoring alerting rules for received telemetry

**Scope.** This platform does not scan, does not host sensors and does not perform
vulnerability testing. It receives findings from four OEM sources and alerts on them. This
requirement produces rules in the platform's own `alert_rules.yaml` shape — a record match on
`severity`, `source` or `category`, or an aggregate over received rows.

**Requirement.** For an attacker technique present in received telemetry and lacking any alerting,
produce a rule that alerts on it, expressed in the platform's own vocabulary, with a severity, a
throttle and a dispatch channel, delivered as a reviewable change to the existing rule file.

**Why not the engineering route**

| | |
|---|---|
| **V** | Rules produced for a technique select on fields this platform does not have. Verified: a live technique probe returned predicates on three fields, and none of them exist in the block table. The gap is larger than a rename — a rule for this platform is written against a normalised, tenant-scoped finding record, not against log fields at all. |
| **S** | The hard problem is deciding which *received* signal evidences a technique: which OEM source, which normalised field, at what threshold, and in the shape the rule engine actually evaluates. That is judgement, repeated for every technique. |
| **V** | Coverage is fixed at nine hand-written rules covering eleven techniques. Every new weakness class arriving through a new CWE is a rule nobody has written, and nothing alerts on it. |
| **E** | The obligation scales with techniques and with new weakness classes, for as long as the platform runs. |

**Explicitly out of scope.** Sigma, Suricata, Wazuh and YARA rules are **not** requested. They run
against packet, host and file telemetry this platform never receives, and belong to the client's
own SIEM or IDS estate. Proposing them here would be a scope error.

---

### R2 · Attributing active threat campaigns to this estate

**Requirement.** For a vulnerability present in the estate, determine whether a named, currently
active campaign targets this sector and whether its technique set matches the estate's exposure.
Return the attribution with a confidence score.

**Why not the engineering route**

| | |
|---|---|
| **S** | A threat-feed signal count measures *global popularity*, not *relevance here*. A vulnerability with twelve sightings may be twelve phishing kits, none touching government; one with three may be in a campaign aimed squarely at this sector. No threshold separates them, because both arrive as a number. |
| **S** | The deliverable is extraction from unstructured threat reporting — advisories, prose, indicator dumps — into a technique set that is not published in queryable form. That is semantic extraction, not a lookup. |
| **V** | The platform holds **zero** external threat intelligence: no reputation feed, no vulnerability database, no campaign data. This is an absence, not a weak capability. The engineering route begins with building feed integration, rate limiting, caching and staleness handling before producing the figure that does not, on its own, answer the question. |
| **E** | Campaign intelligence has a shelf life measured in days and evolves as it adapts. A rule written against one month's reporting is wrong by the next. Re-reading current reporting is a recurring cost; re-writing rules is a treadmill with no completion date. |

**Constraint.** A signal count of zero must never be rendered as "no risk". It means "no record
in the feed". This distinction is a product requirement, not a caveat.

---

### R3 · Judging whether a breach is notifiable under POPIA s.22

**Requirement.** Given a detected compromise, assess whether the POPIA s.22 notification duty is
triggered; if so, assemble a complete, evidenced, signed notification packet for a named human to
review; provide the applicable regulatory guidance and precedent.

**Why not the engineering route**

| | |
|---|---|
| **S** | **Both error directions are expensive.** Failing to report a reportable breach is a regulatory finding. Notifying the Regulator unnecessarily is itself a compliance event with reputational consequence. No threshold is simultaneously correct in both directions, which is the definition of a judgement rather than a rule. |
| **S** | **Severity is the wrong axis.** The archetypal breach for a government identity platform is bulk unauthorised read access through legitimate credentials. That produces **no critical-severity event at all** — it surfaces as anomalous access volume, a statistical signal. A rule keyed to severity misses the most important case. |
| **S** | The statute turns on whether personal information was compromised, the nature and sensitivity of the data, and the circumstances. `severity ∈ {critical, high, medium, low}` is a vendor's opinion. Building a statutory test on a vendor's taxonomy inverts the authority. |
| **E** | "Adequate notification" is defined by case law, not by configuration, and no engineer can encode it from memory. The engineering route re-implements a legal review that must be performed regardless. |
| **S** | **Blast radius is zero by design.** The platform assembles and signs. A named human decides whether to send and does the sending. The capability has no transmit function, no write path and no authority — the lowest-risk possible deployment of a model in a regulated environment. |

---

### R4 · Explaining what caused a change in the risk score

**Requirement.** When the fused risk score moves, identify the dominant contributing signal —
which is already computed deterministically — and attribute the movement to named external threat
activity.

**Why not the engineering route**

| | |
|---|---|
| **S** | A decomposition is not an explanation. The deterministic layer already reports "the application-scanning signal moved by 5.9". It cannot say which vulnerability, how recently it arrived, or whether anyone is exploiting it. The question asked is not answered by restating it. |
| **V** | The causal evidence is outside the platform: publication date, known-exploited status, campaign membership. The chain runs from a number the platform computed to a cause it has never held. |
| **S** | The ambiguous cases are where judgement is required. When two signals move together, which is the driver and which is the downstream effect? Separating them needs reasoning across signals plus external corroboration. |
| **E** | It is the highest-frequency question in the product. The trend chart is the most-viewed panel on the executive dashboard and currently moves with no explanation attached. |

**Scope note.** The signal decomposition is already built, deterministic and live. Only the causal
attribution requires this requirement. **If the committee prefers the decomposition without the
narrative, R4 should be withdrawn and no AI is required for the decomposition.**

---

### R5 · Reading privileged-action sequences for insider risk

**Requirement.** Read the signed privileged-action trail and identify behavioural patterns that
individually-authorised actions only reveal in combination; produce an explanation suitable for
an auditor or investigator.

**Why not the engineering route**

| | |
|---|---|
| **S** | Thresholds are defeated by adaptation, which is the reason detection capability exists. An actor who learns a "more than 500 rows" rule exports 499, once a week. Every volume-only detection has this property; a model reading the whole sequence does not depend on any single threshold being crossed. |
| **S** | The signal is in the order, not the events. Acknowledge → switch tenant → export → acknowledge → resolve in ninety seconds is defensible step by step and damning in sequence. A per-action rule cannot represent it. |
| **V** | The substrate is already excellent and entirely unused: append-only, ECDSA signed, recording every privileged action with actor, role, scope hash and request context. **Verified: no code outside the export path reads it.** Three single-row checks ship against it; nothing reads across rows. |
| **S** | The output is an explanation an auditor can rely on, not a score. "This account exported 4,000 rows forty seconds after switching tenant" is an artefact. "This account's behaviour is unusual" is not. |

**Governance constraint.** No administrator at any tier may hold this capability. A model that
summarises privileged actions is the most dangerous thing to place in an administrator's hands;
the route excludes them by design, and review requires a second named person.

---

## 5. Scope

### 5.1 In scope

| | |
|---|---|
| Provider | AIMI, enterprise tier, five capabilities |
| Model hosting | Provider-hosted, contractually bound to South African or sovereign jurisdiction |
| Data crossing the boundary | Public identifiers only — vulnerability IDs, attacker technique IDs, authorised hostnames, regulatory queries. No warehouse row, no personal information, no aggregate count |
| Human gate | Mandatory on every output. Advisory only |
| Audit | Every AI call recorded with token, confidence, latency and prompt version |

### 5.2 Out of scope

| Excluded | Reason |
|---|---|
| Any autonomous change to severity, risk score, bucket or alert status | Defensible scores cannot be model-mutated |
| Autonomous blocking, or any platform state change | No authority is granted |
| Personal-information processing | Not required by any of the five |
| Vector retrieval or semantic search over warehouse text | The corpus does not justify it; the gate stays closed |
| Substituting model output for the deterministic pipeline | Reproducibility and signability are non-negotiable |
| Text-to-query of any kind | Governed separately and not requested here |

### 5.3 Explicitly not being funded as AI

Listed for completeness. **None of these requires a model.** Three are already in production.

| Capability | State |
|---|---|
| Compliance scoring from telemetry | **Built.** Replaces a hand-entered figure with a computed one |
| Cross-vendor contradiction detection | **Built.** Five of six checks live |
| Estate ownership and concentration graph | **Built** |
| Evidence packets, signed and offline-verifiable | **Built.** Reuses the attestation's existing signing |
| Risk-delta decomposition | **Built.** Deterministic half of R4 |
| Peer control-gap prescription | **Built** |
| ATT&CK coverage and hunt query construction | **Built.** Curated mapping, no generation |
| Vendor coverage and agreement attestation | **Built** |

---

## 6. Deliverables

| # | Deliverable | Verification |
|---|---|---|
| D1 | Alerting-rule authoring service, translated to the platform's own vocabulary, as a reviewable diff | Rules execute against this platform's columns in test |
| D2 | Campaign attribution with confidence and an explicit "no record" state | A zero signal count never renders as "no risk" |
| D3 | Breach-notification packet assembly, signing, and regulatory retrieval | Packet is assembled and signed; **no transmit path exists** |
| D4 | Risk-movement causal narrative beside the computed decomposition | Every cited figure is present in the fact pack |
| D5 | Behavioural sequence report over the signed audit trail | Reports generated by a human reviewer, not an administrator |
| D6 | Governance: outbound data register, audit trail, kill switch per capability | Any capability disableable without a deployment |
| D7 | Acceptance test suite across all five | Cross-tenant leakage rate zero; every output human-gated |

---

## 7. Constraints

| # | Constraint |
|---|---|
| C1 | The deterministic pipeline is unchanged and remains provable with every model disconnected |
| C2 | Existing role and permission structure is not modified; capabilities are additive |
| C3 | No AI component sits in the ingestion or dispatch path |
| C4 | No AI text enters the signed attestation body |
| C5 | Every AI output carries a confidence value and a mandatory human gate |
| C6 | A capability can be disabled without a release |
| C7 | Outbound data is limited to public identifiers and is registered and reviewable |

---

## 8. Commercial and contractual

| Item | Position required |
|---|---|
| Provider | AIMI, enterprise tier |
| Hosting jurisdiction | South Africa, or sovereign jurisdiction with a documented transfer basis |
| Service levels | Defined uptime and response; the blue-team surface must demonstrate responsiveness before commitment |
| Data processing | Written agreement covering the outbound identifier set; a signed data-transfer register before first call |
| Exit | Full export of derived artefacts and audit records; no dependency on provider-held state |
| Liability | Provider warrants no use of customer data for model training |

**Note on a verified risk.** During assessment, the provider's blue-team endpoints did not respond
across a two-minute window while other provider services responded normally in the same session.
**A documented availability check against the exact endpoints for R1 and R5 is a condition
precedent to signature.**

---

## 9. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| K1 | Model output treated as fact by an operator | High | Confidence on every output; mandatory human gate; audit of accept/reject |
| K2 | Cross-tenant leakage through a capability | Severe | Only public identifiers cross; deterministic scope enforced in code, not in prompts; leakage suite in CI |
| K3 | Provider unavailable at a live incident | Medium | Deterministic fallback; no capability is load-bearing; kill switch |
| K4 | Provider changes model behaviour without notice | High | Model and prompt version pinned by digest; recorded on every output |
| K5 | Regulator receives a notification drafted with model involvement | High | Human approval mandatory; platform cannot transmit; provenance retained |
| K6 | Key personnel dependency | Medium | Documentation and evaluation harness delivered to the client |

---

## 10. Prerequisites

None of the five is blocked on missing data. Three engineering items must land first:

| # | Item | Dependency |
|---|---|---|
| P1 | Persist the vulnerability identifier the platform already receives and discards | Half a day. Unblocks R2 |
| P2 | Curated attacker-technique mapping | **Complete and shipped** |
| P3 | Outbound data register entry and transfer basis | Compliance and legal, before first call |

---

## 11. Approval

| | Name | Decision | Date |
|---|---|---|---|
| Executive sponsor | | Approve / Decline / Defer | |
| Compliance | | Approve / Decline | |
| Technology | | Approve / Decline | |
| Finance | | Approve / Decline | |

**Recommendation.** Approve R1, R2, R3 and R5. **R4 is optional** — its deterministic half is
already in production and the incremental value is the causal narrative alone.

---

*AIR-R1 · Prepared 12 October 2026 against `sita-platform` commit `eca4852`. Claims marked **V**
were verified against the codebase, the database schema, or a live provider probe; **S** are
structural properties of the problem; **E** are cost-scaling arguments. No implementation work is
committed by this document.*