
---

# Blue-Team AI Capability Assessment

**Extracted from `AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md`.** This is an
assessment of a proposed seven-area blue-team capability list against the
platform's verified gap register. It is not about the value propositions and
is therefore not carried in that document.

**Headline:** of the seven proposed areas, two are genuine provider wins, three
are real gaps the provider is the wrong tool for, and two are weak or negative.
---

# PART II — Assessment of the Proposed Blue-Team AI Capability Set

**Added 12 October 2026.** Assesses the seven proposed areas — log analysis, threat detection
and anomaly identification, event correlation, intelligent alert analysis and prioritisation,
incident investigation support, security reporting and analytics, and threat intelligence
support — against SITA's verified gap register, and critiques the AI value add of each.

**Headline verdict: of the seven, two are genuine AIMI wins, three are real gaps that AIMI is
the wrong tool for, and two are weak or negative.** The list reads as a generic blue-team
capability matrix rather than a response to anything SITA cannot already do.

---

## 11. Architectural verdict on AIMI's blue-team tool surface

This had to be established before any area could be assessed, because the tool signatures
determine what is portable.

**AIMI's blue-team suite is written for a single host defending itself.** Seven of twelve tools
take a filesystem path or no parameters at all:

| Tool | Signature | Ports to a multi-tenant warehouse? |
|---|---|---|
| `blue_malware_scan` | `path="/home"`, `recursive=true` | **No** — SITA's data plane has no file ingress; it consumes OEM API JSON |
| `blue_analyze_logs` | `log_path="/var/log"`, `lookback_hours=24` | **No** — SITA ingests no syslog or journald stream |
| `blue_check_ftp` | none | **No** — SITA has no host layer to check |
| `blue_hardening_check` | none | **No** — SITA has no host layer |
| `ids_suricata_alerts` | `eve_json_path="/var/log/suricata/eve.json"` | Only via a file export |
| `ids_snort_alerts` | `alert_path="/var/log/snort/alert"` | Only via a file export |
| `ids_status` | none | **No** — reports the local engine |
| `ids_rule_synthesize` | **`findings_json`** | **Yes — the one portable contract** |
| `iron_dome_health` / `status` / `report` / `threat_hunt` / `alerts` | none or hours+severity | **No** — local daemon and local database |
| `iron_dome_block_ip` / `unblock_ip` | `ip`, `duration_minutes`, `reason` | **No** — autonomous iptables mutation on AIMI's host |
| `blue_update_clamav` | none | **No** — signature refresh, irrelevant without file ingress |

**Zero of the twelve accept a database connection, a tenant identifier, or a stream name.**
There is no `tenant_id` parameter anywhere in the blue-team surface. There is no
`scope_hash`. The suite has no concept of multi-tenancy because it does not need one — it
defends one container.

### 11.1 Three consequences

**a) The only portable contract is `ids_rule_synthesize(findings_json)`.** It takes findings as
JSON and returns detection content. That is structurally identical to AVP-2's rule-diff
proposition, and it is the single piece of AIMI's blue-team surface worth calling as a service.

**b) A file-export bridge is technically possible and strategically wrong.** SITA could export a
tenant-scoped, redacted snapshot to a file; AIMI would analyse it; SITA would re-attribute. It
works. It also creates a written artefact on AIMI's disk that is no longer protected by
`tenant_filter()`, no longer covered by the AVP Data Boundary (§5), and no longer auditable
per-request. It also forces row-level data across a boundary that was specifically designed to
carry only public identifiers. **If this route is ever taken, restrict it to aggregates only.**
It is strictly worse than the token model and should be a last resort.

**c) `iron_dome_block_ip` is a governance regression.** It performs an autonomous iptables
mutation with no human in the loop. SITA's entire alert lifecycle routes through
`acknowledge` → `resolve`, `alert_rules.yaml` declares channels and throttles for every rule,
and `access_audit.py` signs every privileged action. Wiring autonomous blocking into that
would be a **downgrade** in control posture, not an upgrade in capability. **Explicitly excluded
from every wave.**

### 11.2 Availability signal — must be verified before commitment

The blue-team surface could not be probed on 12 October 2026:

- Two `tool_iron_dome_*` calls returned *"unavailable tool"* from the server on first attempt
  (operator error on my part — wrong tool name).
- The MCP session then dropped — *"Could not find session"*, a documented and normally
  recoverable failure mode.
- **Six subsequent attempts over roughly two minutes all timed out**, including
  `tool_aimi_get_started`, which had succeeded twice earlier in the same session, and including
  zero-argument calls such as `ids_status` and `iron_dome_health`.

I cannot distinguish "the AIMI blue-team service is down" from "my session is wedged and did not
recover". Either way: **the exact surface being proposed for integration demonstrated no
responsiveness during a two-minute window, while the fraud, graph and purple-team tools
responded normally earlier in the same session.** Before Wave 3 commitments are made, run a
documented availability check against the blue-team endpoints. This is a procurement question,
not an engineering one.

---

## 12. The human-validation clause — critique

> *"AI-generated findings and recommendations will need to be validated by the relevant security
> personnel."*

This clause is correct and load-bearing, and **currently has nothing to attach to.**

| Requirement | State in SITA |
|---|---|
| A system of record for who validated what | **Does not exist.** No case entity, no analyst note field, no review table |
| When they validated it | **Does not exist.** No triage table — that is Phase D, not built |
| On what evidence | **Does not exist.** No evidence attachment mechanism |
| A durable audit trail linking AI output to a named decider | **Partially.** `audit.action_audit` and `access_audit.py` exist and are ECDSA-signed, but nothing writes an AI-decision row, because no AI ships |

Phase D's `warehouse.finding_triage` with accept/reject logging is the intended home for this, and
it is 15 weeks out. **Until it lands, the validation clause is a policy statement with no
mechanism**, and policy statements with no mechanism are what an Auditor-General finding is
written about.

AIMI models the right shape. The `typology_match` probe returned:

```json
"qa": {
  "layer_1": {"type": "deterministic_validation", "confidence": 1.0, "null_fields": []},
  "layer_2": {"type": "cross_source_verification", "verified": false,
              "notes": ["No cross-source verification available"]},
  "layer_3": {"type": "hermes_review_gate", "triggered": true,
              "recommendation": "Human review recommended before acting on these findings."},
  "overall_confidence": 0.6,
  "hallucination_risk": "medium"
}
```

**Adopt this envelope as the platform standard for all AI output**, including SITA's own Phase B
narratives, rather than inventing a second QA convention. The `hermes_review_gate.triggered`
flag is the natural trigger for the validation workflow — it becomes the work item.

Two requirements the clause must add to be defensible:

1. **A named decider, not a role.** "Validated by the SOC" is not evidence. "Validated by
   A. Mbeki, appsec, 2026-10-14, against evidence E-4471" is.
2. **The validation event must be signed.** `sign_canonical_payload()` already exists in
   `app/security_pki.py`. The validation row joins the `action_audit` chain, so the audit trail
   is non-repudiable.

---

## 13. Area-by-area critique

### Area 1 — Security Log Analysis · **Weak. Do not integrate.**

SITA ingests OEM telemetry and normalises it deterministically: `normaliser.py` flattens
vendor field paths via `field_mapper.yaml`, normalises severity per source, maps six vendor
vocabularies to OWASP Top 10 2021, coerces timestamps, dedups. That is a stronger log-analysis
capability than heuristic pattern-matching on raw syslog, because it is deterministic and
auditable.

AIMI's `blue_analyze_logs(log_path, lookback_hours)` reads files from a path on its own host.
SITA has **no syslog or journald stream** — it consumes AppScan, Imperva DAM, Imperva WAF, API
Security and a compliance feed, all via API.

**Critique.** This is not "AIMI beats SITA". It is "AIMI analyses a data class SITA does not
have, using a method SITA does not need, over a data class SITA already handles better". The
proposal conflates *log analysis* with *syslog analysis*. Either drop the area, or restate it
honestly as "on-host file and process integrity monitoring", which is a **host-security product
decision, not a telemetry-platform decision** — and one SITA has no host layer to apply it to.

---

### Area 2 — Threat Detection and Anomaly Identification · **Real gap. But it is a data-science gap wearing an AI label.**

SITA's anomaly detection is genuinely thin. Verified inventory:

- **One** statistical rule exists in the entire platform: a 3-sigma z-score on Imperva volume
  against a 7-day baseline (`alert_rules.yaml:103-113`).
- **One** more quasi-statistical rule: a 5-point day-over-day compliance delta (`:90-101`).
- The other seven rules are signature matches — severity equality, source equality.
- **No** clustering, **no** forecasting, **no** time-series modelling, **no** changepoint
  detection, **no** per-entity baseline, **no** correlation, **no** regression.
- `scipy`, `statsmodels` and `sklearn` are not installed.

**Critique.** The genuine opportunity here is that SITA has **15,283 `risk_scores` rows** with
four signal columns each, plus 2,244 findings and 3,569 WAF blocks — enough history for
per-application baselines, seasonal decomposition, changepoint detection and peer-group anomaly
scoring. **None of that needs an LLM.** It needs a data scientist and numpy.

AIMI's answer to this area is `blue_malware_scan` (ClamAV on files) and `iron_dome_threat_hunt` —
host-based and local. That is a **different capability class** from statistical anomaly detection
over tenant telemetry.

**Recommendation.** Take this area, but re-label it. Scope it as a platform capability with AIMI
as, at most, a source of detection *ideas*. Do not present it as an AI integration.

---

### Area 3 — Security Event Correlation · **Strong need. AIMI is the wrong tool for the core job — and the right tool for the outer edge.**

SITA has **zero** correlation capability. Verified: no graph model, no entity resolution, no
cross-source join beyond `dedup_key` (which is suppression, not correlation). Every fact is an
isolated row. The questions SITA cannot answer at all:

- Which WAF blocks relate to which findings on which asset?
- Which assets share an owner, a dependency, a technology, or an attacker?
- What is the shortest path from a compromised application to a database holding PII?
- Which departments are exposed to the same technique?

AIMI's graph tooling is real. The `link_analyze` probe on four ATT&CK IDs returned typed nodes
with tactic assignment and a `SHARES_TACTIC` edge between T1190 and T1199 — correct, structured,
usable output.

**Critique.** But AIMI's graph is **external and global**. The correlation SITA needs first is
**internal and tenant-scoped**: joining SITA's own warehouse to itself. That is a self-join over
`findings` × `alerts` × `api_endpoints` × `risk_scores`, all of which are already
tenant-denormalised. **It requires no AI at all**, and it must be built in-cluster regardless —
because it is the join that makes `tenant_filter()` meaningful across tables.

Only the **outer edge** is AIMI's: resolve a shadow API's upstream host, enrich a CVE, attribute
a technique to a campaign. That is AVP-2 and AVP-6.

**Recommendation.** Split the area. Internal correlation graph — build it, SITA's own work, no
AI, highest value per hour in this entire assessment. External enrichment — AVP-2, AVP-6.

---

### Area 4 — Intelligent Alert Analysis and Prioritisation · **Real gap, cheap fix, mostly not an AIMI job.**

SITA's prioritisation is this (`alert_enricher.py:17`):

```python
SEVERITY_PRIORITY = {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5}
```

**`priority` is severity, reordered.** There is no context: no asset criticality, no threat
intelligence, no peer comparison, no history, no confidence, no business impact. Meanwhile
`app_catalog.yaml` already carries a `tier` field that is not used for prioritisation at all.

A SOC with 551 alerts and a rank column that is a relabelled severity column has no triage tool.

**Critique.** This is the weakest justification on the list for calling it AI, and the strongest
case for just fixing it. A defensible ranking needs, in order of value per hour:

1. **Asset tier** — already in `app_catalog.yaml`, currently unused for this.
2. **Threat context** — AVP-3's signal. This is where AIMI genuinely contributes.
3. **Peer deviation** — is this department worse than the other 172? AVP-7's data.
4. **Confidence** — AIMI's QA envelope, applied to SITA's own detections.
5. **Recency and churn** — deterministic, from data already stored.

AIMI's `risk_score` and `fraud_classify` are built for customers, entities and transactions — not
security alerts. Using them here is a **category mismatch** dressed as integration.

**Recommendation.** Take the area, drop the AI framing. Build the deterministic ranking first.
Wire AVP-3 in second, as one input among five.

---

### Area 5 — Incident Investigation Support · **Real gap, currently blocked on a substrate that does not exist.**

SITA's investigation capability is:

- `AlertStatus` declares five states. **Two of them are unreachable.** `INVESTIGATING` and
  `DISMISSED` are defined in `models/alert.py:8-13` and never written by any code path. The API
  exposes only `acknowledge` and `resolve`.
- **No case entity.** No investigation workspace, no evidence attachment, no analyst notes, no
  assignment, no SLA, no escalation chain beyond severity→channel, no timeline of analyst actions.
- `Alert.enriched_data` (JSONB) is the only free-form slot, and it holds enrichment, not notes.
- The audit trail is genuinely good — ECDSA-signed, records who knew and when — and it is the only
  investigation-grade artefact that exists.

**Critique.** The blocker is not AI. **The blocker is that there is nothing for an AI to
support.** You cannot give an AI an investigation workspace that has not been built. This area
requires, in strict order: a case entity → evidence attachment → analyst notes → timeline →
*then* AI triage support on top.

AIMI can supply the orchestration shape. `investigate` with `poll_progress` returning typed phase
events (`{"phase": 1, "status": "complete", "name": "Domain Intelligence"}`) is a sound model
for an investigation state machine, and `case_package` handles compilation. But it cannot supply
the workspace, and it cannot see tenant-scoped evidence under the Data Boundary.

**Recommendation.** Take the area. Sequence it **last among the blue-team items**, behind a case
management build that is SITA's own work and is not currently scheduled in any phase.

---

### Area 6 — Security Reporting and Analytics · **Negative value add. Exclude.**

SITA is **ahead of AIMI** here, and adding AIMI would be a regression.

| | SITA | AIMI |
|---|---|---|
| Tenant-scoped role dashboards | 6, across 14 roles | 0 |
| Scoping primitive | `tenant_filter()`, province expansion, fail-closed | **None in the blue-team surface** |
| Cryptographic attestation | ECDSA P-256, reproducible body, offline verification | None |
| Compliance framework registry | 6 instruments with stored applicability determinations | `grc_posture` on 4 framework ids, no ISO |
| Peer benchmarking | Tenant-safe with peer blinding | None |
| Narrative | Deterministic, anti-drift-tested against literal re-statement | None relevant |

AIMI's report tools — `report_pentest`, `report_executive_brief`, `report_fraud`,
`purple_report` — generate reports from **AIMI's own engagement and investigation data**. That
is a different job entirely. They have no tenant concept and cannot produce a department-scoped
artefact.

**Critique.** This is the clearest signal that the seven-area list was not written from SITA's gap
register. Area 6 describes the platform's single strongest capability. Including it in an
AI-integration scope signals that the scope was assembled from a generic capability matrix rather
than from what the platform cannot do.

Phase B of `AI_INTEGRATION_PLAN_MASTER.md` already owns reporting and analytics, deterministically
and with a verifier. **Keep it there. Exclude AIMI from this area entirely.**

---

### Area 7 — Threat Intelligence Support · **Strongest win in the set. Build this first.**

SITA has **nothing**. Verified: no VT, no OTX, no HIBP, no reputation feed, no IOC store, no
domain intelligence. Every finding is judged in isolation.

AIMI brings four feeds and automatic OTX enrichment:

- `domain_investigate` — VT, AA419, HIBP, OTX, plus TLS, headers, WHOIS, DNS, fraud heuristics
- `ioc_correlate` — with per-indicator `enrichment_status.otx` of `fired` / `no_key` / `error`
- `breach_exposure` — HIBP domain and email exposure
- `username_search` — Sherlock-style handle discovery

**Critique.** The OTX result separation is the detail that makes this integration trustworthy and
that should be built into the UI from day one: `pulse_count: 0` means **"no OTX record"**, never
"safe". The guide is explicit about this. A pulse count of 0 rendered as a clean bill of health
would be a serious and entirely silent error.

This is the one area where every condition is simultaneously favourable:

- **Genuine zero** in SITA — nothing is displaced
- **Token-only egress** — CVE, domain, hash. No row, no name, no count
- **Tenancy risk near zero** — the output describes a public indicator, not an estate
- **Directly feeds AVP-3**, which in turn feeds Area 4's prioritisation
- **AO-agnostic** — public threat intelligence is not personal information

**Recommendation.** This is Area 7 alone, promoted to Wave 2 alongside AVP-2 and AVP-6, and it
should be the headline of any AIMI proposal.

---

## 14. Scorecard

| # | Proposed area | SITA's verified state | AIMI fit | Verdict |
|---|---|---|---|---|
| 1 | Security Log Analysis | Strong deterministic normalisation; no syslog | Wrong data class | **Weak — drop or restate** |
| 2 | Threat Detection / Anomaly | **1** statistical rule in the whole platform | Right class, wrong implementation | **Real gap — data science, not AI** |
| 3 | Security Event Correlation | **Zero** | Right class, external not internal | **Strong need — build internal, AIMI for edge** |
| 4 | Alert Analysis / Prioritisation | `priority` = severity reordered | Category mismatch | **Real gap — cheap deterministic fix** |
| 5 | Incident Investigation | **Zero**; 2 of 5 alert states unreachable | Blocked on missing substrate | **Real gap — blocked, build case entity** |
| 6 | Security Reporting / Analytics | **Ahead of AIMI** | Regression risk | **Negative — exclude** |
| 7 | Threat Intelligence | **Zero** | Direct, token-only fit | **Strong win — do first** |

**Net: 2 of 7 are genuine AIMI wins. 3 are real gaps AIMI is the wrong tool for. 2 are weak or
negative.**

---

## 15. Revised capability set

What should actually go into the proposal, rewritten against SITA's gap register rather than
against a generic blue-team matrix:

| # | Capability | Why it survives | Owner |
|---|---|---|---|
| **1** | **Threat intelligence enrichment** — CVE, domain, IOC and OTX context on ingested findings (Area 7, AVP-3) | SOTA zero. Token-only egress. Near-zero tenancy risk | AIMI + platform |
| **2** | **Internal entity-correlation graph** — in-cluster self-join of findings × alerts × endpoints × risks, tenant-scoped, with external enrichment at the edge (Area 3, AVP-6) | SOTA zero. No AI required for the internal graph. Tenancy-safe by construction | Platform |
| **3** | **Context-aware alert ranking** — asset tier, threat context, peer deviation, confidence, churn (Area 4) | `priority` is currently severity reordered. Deterministic first | Platform |
| **4** | **Detection content generation** — validated Sigma/Suricata/Wazuh/YARA as a reviewable diff against `alert_rules.yaml` (Area 2 partly, AVP-2) | SITA zero on MITRE. Only portable AIMI blue-team contract | AIMI + platform |
| **5** | **Per-application anomaly baselines** — changepoint, seasonal, peer-group deviation over 15,283 stored score rows (Area 2) | One 3-sigma rule today. Data science, honestly labelled | Data science |
| **6** | **Case management and investigation workspace** — the substrate Area 5 requires, including the validation workflow §12 needs (Area 5) | SOTA zero. Not AI. Blocks Area 5 and the validation clause | Platform |
| **7** | **Hunt proposals from coverage gaps** (Area 5, AVP-9) | Consumes 2 and 4. Needs 6 to exist | Platform |

**Dropped:** Area 1 (wrong data class), Area 6 (SITA is ahead).

**Two of the seven survive as AI integration.** Four are platform engineering that should not be
sold as AI. One is data science. That ratio is the honest answer, and it is a better one than
seven-for-seven: a proposal that claims an LLM improves alert ranking and log analysis will not
survive contact with the engineering team that has to build it.

---

## 16. What to add to the proposal text

The original framing has one further defect: *"enhance the solution's ability to analyze and
interpret security data across the various integrated systems"* implies SITA cannot currently do
that. **It can, and it does, deterministically** — `processing/normaliser.py` reconciles six
vendor vocabularies across five OEM sources into one canonical schema with a versioned OWASP
taxonomy, and re-derives the classification at write time (`lake/writer.py:70-76`) so a bypassed
normaliser still cannot write an unrecognised category.

Suggested replacement:

> **Security telemetry from five OEM sources is already normalised, correlated to a versioned
> OWASP taxonomy, fused into a tenant-scoped risk score, and delivered through six role-scoped
> dashboards with a cryptographically signed compliance attestation.** That pipeline is
> deterministic and auditable, and it is the foundation these capabilities build on.
>
> The proposed AI integration adds what a deterministic pipeline structurally cannot: **external
> threat context** the platform does not hold, **independent verification** of what its vendors
> assert, and **generated detection and control content** for the gaps those capabilities expose.
> It does not replace the normalisation, the risk model or the reporting — those remain
> deterministic, and remain provable with every model switched off.
>
> AI-generated findings and recommendations are advisory. Each carries a confidence score and a
> review gate flag. Validation is recorded against a named decider and signed into the existing
> ECDSA audit chain. No AI output modifies a severity, a risk bucket or an alert status.

That version is defensible, it does not overclaim, and it is consistent with everything
`AI_INTEGRATION_PLAN_MASTER.md` §4.1 already commits to.

---

*Part II added 12 October 2026. Blue-team tool surface assessed from MCP tool signatures; the
surface was unresponsive for approximately two minutes during assessment and that is recorded as
an open procurement item in §11.2, not as a verified outage. Areas 3 and 4 in the scorecard were
scored from code read; areas 1, 2, 6 and 7 were scored against AIMI's documented and probed
capability. No code was written and no customer commitment is implied.*

---

*AIMI Intelligence Value Propositions. Prepared 12 October 2026 against `sita-platform`
commit `eca4852` and AIMI `enterprise` tier. SOTA: proposal, no code committed, no
customer commitment implied. Findings marked "probed live" were verified by direct MCP call
on 12 October 2026; AIMI responses are cached for 24 hours and reflect the state of that day.*
