# SITA Consolidated Security Reporting Platform
# Deliverable B5: ICASA & ECT Act Applicability Determination and Gap Analysis (v1.0)

**Managing Authority:** State Information Technology Agency (SITA)
**Primary Instrument:** Electronic Communications and Transactions Act (ECT Act No. 25 of 2002)
**Regulator of Reference:** Independent Communications Authority of South Africa (ICASA Act No. 13 of 2000; Electronic Communications Act No. 36 of 2005)
**Cross-Reference Documents:** `B3_POPIA_Compliance_Assessment.md`, `B4_POPIA_Remediation_Plan.md`, `RISK_REGISTER.md`
**Assessment Date:** 2026-10-09
**Method:** Full-text code audit of `backend/app`, `infrastructure/` and `docs/`, reconciled against primary legislation.

---

## 1. Executive Summary

A naive gap analysis against ICASA would produce roughly sixty findings and be almost entirely wrong, because ICASA's statutory machinery regulates **electronic communications service (ECS) and network service (ECNS) licensees**. SITA is a Schedule 3A public entity. It holds no ICAMS licence, operates no electronic communications network, and supplies no licensed equipment.

The instruments that genuinely bind this platform are:

1. **ECT Act 25 of 2002** — e-services by public bodies, critical information infrastructure, hosting and take-down notification, cyber inspectors.
2. **POPIA 4 of 2013** — enforced by the **Information Regulator**, not ICASA, but binding on SITA and flowing down contractually.
3. **RICA 70 of 2002** — **conditionally** applicable only if SITA assumes a telecommunication service provider function.

The decisive commercial finding: **ICASA is a tenant of this platform.** `backend/app/tenant.py:315` registers it as customer department "Independent Communications Authority of South Africa" with five branches (`tenant.py:644-648`). ICASA's own information-security obligations therefore reach this platform as **processor** obligations under the tenant contract, while regulatory enforcement sits with the Information Regulator, not ICASA.

**Coverage scorecard against the applicable ICASA/ECT considerations: 0 of 12 covered. 1 conformant by absence of capability. 3 critical gaps.**

The two structural findings that matter more than any individual control gap are recorded in Section 6.

---

## 2. Applicability Determination

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│              ICASA STATUTORY INSTRUMENT — APPLICABILITY MATRIX                     │
├──────────────────────────────────────┬────────────┬───────────────────────────────┤
│ Instrument                            │ Applies?   │ Basis                         │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ ECA licence conditions / ECS-ECNS     │            │ Not an ECS/ECNS licensee;     │
│ Code of Conduct                       │   NO       │ no ICAMS licence held;        │
│                                      │            │ outside ACR scope (65 lic.)   │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ Type approval / Equipment              │            │ Supplies no EC network        │
│ Authorisation (GN 43047, 2020)         │   NO       │ equipment                     │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ Numbering Plan / Call Termination /   │            │ No electronic communications │
│ Interconnection / Facilities Leasing   │   NO       │ network operated              │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ Universal Service & Access Obligations │   NO       │ Not designated licensee       │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ RICA 70 of 2002                       │            │ Binds telecommunication       │
│ (interception, CRI retention,          │CONDITIONAL │ service providers (s.12, 28,  │
│  listed equipment)                    │            │ 30, 39-41). Engages only if   │
│                                      │            │ SITA assumes TSP function     │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ ECT Act 25 of 2002                    │            │ Public-body e-services;      │
│                                      │   YES      │ critical data (s.53); hosting │
│                                      │            │ (s.75-77); cyber inspectors   │
│                                      │            │ (Ch. XII, s.80-84)            │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ POPIA 4 of 2013                       │            │ Information Regulator is     │
│                                      │   YES      │ enforcer; ICASA is tenant and │
│                                      │            │ inherits processor duties    │
├──────────────────────────────────────┼────────────┼───────────────────────────────┤
│ ICASA Act s.4(o) — recommendations     │  INDIRECT  │ Makes ICASA a stakeholder in  │
│ to Minister on ECT Act matters        │            │ ECT matters, not a supervisor │
└──────────────────────────────────────┴────────────┴───────────────────────────────┘
```

**Determination.** The ICASA licence-condition compliance model does not apply to this platform and must not be represented as the target regulatory model. The correct target model is **ECT Act + POPIA**, with RICA held as a conditional item.

This determination should be issued as a signed applicability opinion before any further assurance work. It is the single cheapest item in this analysis: it eliminates an entire class of spurious findings and prevents the platform asserting compliance against a regime it is not subject to.

---

## 3. Coverage Audit — What the Code Actually Implements

| Search term | Hits | Nature |
|---|---|---|
| ICASA | 7 | Tenant rows only — `tenant.py:251, 315, 644-648`. Zero regulatory logic. |
| ECT / Electronic Communications and Transactions Act | 0 | Absent |
| Communications Act | 0 | Absent |
| RICA / lawful interception | 0 | Absent |
| Type approval / equipment authorisation | 0 | Absent |
| National Cybercrimes Act | 0 | Absent |
| NCSA Act | 1 | Persona title in demo data only — `docs/C3_CISO_Four_Tier_Role_Mapping.md` |
| National CSIRT | 5 | Roadmap prose only — `docs/SITA_Executive_Presentation_Deck.md:184` |
| POPIA | 67 files | The only privacy regime implemented |

**Framework catalogue is hard-closed to two values.** `backend/app/api/routers/compliance.py:16` validates `framework` against `pattern="^(popia|iso_27001)$"`. An ICASA, ECT or RICA framework cannot even be requested through the API. `backend/app/synthetic/generator.py:66` mirrors the same two-value list.

**The compliance engine has no callers.** `backend/app/processing/compliance.py` is 38 lines: two weight dictionaries and three functions. Verified — `compute_framework_score`, `compute_popia_score` and `compute_iso_score` have **zero call sites** outside the module itself. Snapshots in the database originate from seed fixtures and the CSV compliance connector.

---

## 4. Gap Analysis

| # | Consideration | Status | Evidence |
|---|---|---|---|
| G-01 | ECT Act e-services compliance for public bodies (s.27) | **Absent** | No ECT reference repo-wide; no e-service recordkeeping policy |
| G-02 | Critical information infrastructure declaration (ECT s.53) | **Absent** | `critical_data` / `critical_database` concepts absent. No CII designation status tracked. CSIRT notification is roadmap-only |
| G-03 | Cyber-inspector readiness (ECT s.80-84) | **Absent** | No inspection-request runbook, no legal-hold trigger, no break-glass procedure. The audit role split `infrastructure/scripts/audit-role-split.sql` is **untracked in git** and may be unapplied on any target host |
| G-04 | Hosting-provider take-down notification (ECT s.75-77) | **Absent** | Platform is not a public host, so presumptively N/A — but no determination is recorded anywhere |
| G-05 | No general obligation to monitor (ECT s.78) | **Conformant** | No interception capability exists at all, so no RICA s.28-style duty arises. Record as a positive finding |
| G-06 | POPIA unique-identifier handling (s.13(c), s.57) | **Partial** | `identity.persons` holds 2,451 HR-sourced rows. **Identity numbers are present on only 22 of them** (2,429 NULL) — the platform does not absorb ID numbers as a matter of course, and no account originates from a person record (`identity.users` has 0 rows with a `person_id`). `work_phone`, `email` and `clearance_level` are populated on all 2,451 and were previously emitted unmasked; output masking is now centralised in `app/pii.py`. **See the corrections in §5.1** |
| G-07 | Cross-border transfer controls (POPIA s.44) | **Absent — CRITICAL** | PagerDuty hardcoded to `events.pagerduty.com` (`dispatch/pagerduty_adapter.py:28`); Microsoft Teams webhook; AppScan Cloud. No transfer register, DPA, sub-processor list or egress allowlist |
| G-08 | Encryption at rest | **Absent** | No `pgcrypto`, TDE or KMS. ID numbers and full OEM payloads in `warehouse.findings.raw_data` plaintext |
| G-09 | Retention discipline on personal data | **Partial** | pg_cron in `infrastructure/scripts/maintenance.sql` covers staging raw records, risk scores, alerts and compliance snapshots. `identity.persons`, `hr.employees`, `waf_blocks.src_ip` and `waf_blocks.request_uri` have **no purge job and no TTL** |
| G-10 | Read-access audit for personal data | **Absent — CRITICAL** | `ActionAudit` rows are written in exactly one place — the AG export (`api/routers/exports_ag.py:255-276`). No audit record for logins, failed logins, tenant switches, `/admin/users` reads, CSV exports or dispatch actions |
| G-11 | Subscriber complaint handling (EUSSC Regulations) | **N/A — document exclusion** | No subscriber relationship, no direct-to-consumer messaging. Should be recorded as a scoped-out item, not silently omitted |
| G-12 | Data-subject layer (consent, DSAR, erasure, minimisation) | **Absent** | Zero code for consent, erasure or DSAR. `docs/B3:60` claims the normaliser strips raw personal payloads; `processing/normaliser.py:204-218` performs no PII filtering |

### Coverage: 0 / 12 implemented · 1 conformant · 1 N/A · 10 absent

---

## 5. Verified Absences — Highest Regulatory Exposure

**G-10 is the most consequential.** For any Information Regulator inspection or internal audit, the platform cannot answer *"who accessed what personal data, and when."* Login events are rate-limited using an in-memory `defaultdict(deque)` keyed on IP (`api/routers/auth.py:66`) which is neither durable nor logged. Tenant switches, role grants and bulk exports leave no trace. POPIA security safeguards and ECT accountability both presuppose this record exists.

**G-07 is already self-identified.** `docs/B4:107` and the seed fixtures record "Cross-border data transfer not documented" as a **critical open gap**. The `cross_border: 0.05` entry in `compliance.py:9` is a score weight, not a control — it has no supporting artefact and its computation path is uncalled.

**G-06 is structural.** `identity.persons.id_number` is stored in plaintext in the same table and rows as ordinary employment data, and is masked only on two response paths. Database exports, CSV outputs and logs remain unmasked.

### 5.1 Corrections: scale, and the classification of identity numbers

Two errors in the first draft of this document are corrected here.

**Correction 1 — scale.** The first draft described the platform as holding
"an unencrypted national identity number for ~2,400 employees". That is wrong
and was inferred from the schema and the sync code without checking the data.
Measured against the live database on 2026-10-09:

| Measure | Count |
|---|---|
| `identity.persons` rows | 2,451 |
| rows with a non-null `id_number` | **22** |
| `identity.users` with a `person_id` | **0** |
| rows with `work_phone`, `email`, `clearance_level` | 2,451 |

The platform **does not absorb employee identity numbers** as a matter of
course. Employee and role records originate in the government HR systems; SITA
is the command centre and the platform is a consumer of that feed, not an
authoritative source. No platform account is provisioned from a person record
in the current dataset.

The genuine exposure is therefore **not** identity numbers. It is the
contact and employment attributes carried on all 2,451 rows — `work_phone`,
`email` and `clearance_level` — which were emitted unmasked on both admin
output paths. That is what `app/pii.py` now masks, and it is the more
material fix of the two.

The 22 populated `id_number` values are retained as a **forward-looking
control**: the HR sync path copies `id_number` whenever the upstream feed
supplies one (`api/routers/admin.py`, HR sync column list), so the field can
become populated without any change to this platform. Masking it is cheap
insurance, not a description of current state.

**Correction 2 — classification.** The first draft classified SA national ID
numbers as **special personal information** under POPIA s.26-33. That is
incorrect.

POPIA s.26 defines special personal information exhaustively as personal
information concerning **religious or philosophical beliefs, race or ethnic
origin, trade union membership, political persuasion, health or sex life,
biometric information, or criminal behaviour**. An identity number is not in
that list. The platform stores none of the listed categories, so the s.26
prohibition and the s.27-33 authorisations are **not engaged** by the current
data model.

The correct characterisation is narrower but not less serious:

- **s.13(c)** — an identity number is expressly "any identifying number",
  therefore personal information. The same applies to `work_phone` and `email`.
- **"Unique identifier"** — the Information Regulator's guidance note on prior
  authorisation lists **identity number**, **employee number** and **telephone
  number** explicitly among examples of unique identifiers.
- **s.57(1)(a)** — prior authorisation from the Information Regulator is
  required before using unique identifiers for a purpose other than the one
  intended at collection, or for linking the responsible party's information
  with that of other responsible parties. The platform links HR-sourced person
  records across **60 department tenants** plus a provincial dimension, which is
  squarely within s.57(1)(a). **No prior authorisation is on file.**

`clearance_level` is ordinary personal information, not a unique identifier; it
is masked because it makes an individual a target, not because of its category.

The remediation is therefore reframed: the obligation is **s.57 prior
authorisation plus s.19 security safeguards and minimisation** — not a
special-personal-information authorisation.

---

## 6. Structural Findings

### 6.1 The compliance score is fixture data, not a control

The headline figure of **82.9% / 97-of-117 POPIA controls** originates from seed fixtures (`infrastructure/scripts/init-db.sql:276`), not from computation. `compute_popia_score` and `compute_iso_score` have no callers. `GET /api/v1/compliance/evidence` does not return evidence: it counts gaps where a seeded integer `evidence_count` is greater than zero and buckets anything due within 30 days. There is **no evidence table, no upload path and no artefact store**.

A regulator asking *"show me the control and its evidence"* currently receives a weighted-sum function and a seeded integer. This must be corrected before any compliance figure is presented externally.

### 6.2 Documentation-to-code drift is systematic

Any gap analysis built on the existing documentation rather than the code will materially **overstate** coverage. Verified contradictions:

| Claim in documentation | Actual implementation |
|---|---|
| `docs/C2:55`, `SITA_GoLive:85` — "Bcrypt password hashing" | PBKDF2-HMAC-SHA256, 260,000 iterations (`app/security.py:13-31`) |
| `docs/B3:35`, `generate_excel_spreadsheets.py:234` — "SHA-256 masking" | Asterisk masking (`admin.py:137-142`) |
| `docs/C2:5, 15` — ISO/IEC 27001:**2022** | ISO 27001:**2013** Annex A themes, A.5-A.16 (`compliance.py:12-25`) |
| `docs/B3:38-40` — `audit_logs` records all auth, role changes and tenant switches with IPs | No such table and no such writes; the table is `audit.action_audit` and is written only by the AG export |
| `docs/B3:60` — "Telemetry normaliser strips raw personal payloads" | No PII filtering in `processing/normaliser.py`; full OEM payload retained in `staging.raw_records.raw_payload` and `warehouse.findings.raw_data` |
| `docs/C2:62` — "Prometheus metrics and SLOs" | `setup_metrics()` is `def setup_metrics(): pass`; no `/metrics` endpoint mounted |
| `docs/B3:65` — 12-month telemetry retention, 5-year audit retention | `maintenance.sql` implements 7d / 400d / 90d / 730d |
| `docs/B3:93-96` — Condition 8 satisfied via `/admin/users` | Administrative user provisioning, not a data-subject access request process |

**`docs/F1_Platform_Security_Hardening_Guide.md:55` contains a literal example password in a tracked file.** This must be rotated and purged from history.

`docs/B3` and `docs/F1` should be treated as unreliable sources until reconciled against code. `docs/SITA_GoLive_Readiness_and_RID_Resolution_Report.md:37` marks POPIA statutory compliance **CLOSED/SOLVED**; that marking is the single assertion most in need of review.

### 6.3 The transferable asset

The append-only, cryptographically verifiable audit trail is genuinely well engineered and is the correct foundation for closing G-10. `infrastructure/scripts/init-db.sql` enforces immutability in four layers: a PL/pgSQL guard function rejecting DELETE and rejecting UPDATE of 14 evidentiary columns; a BEFORE UPDATE OR DELETE row trigger; a separate BEFORE TRUNCATE statement trigger (TRUNCATE bypasses row triggers); and a BEFORE INSERT trigger that fails loudly if the guard has been disabled. `REVOKE UPDATE, DELETE, TRUNCATE` is applied to PUBLIC.

`infrastructure/scripts/audit-role-split.sql` closes the ownership hole by moving table and guard-function ownership to a `NOLOGIN` break-glass role and granting the runtime role INSERT and SELECT only — preventing the application from replacing the guard with a no-op body.

`backend/tests/test_audit_immutability.py` extracts the DDL verbatim from `init-db.sql` into a throwaway schema so it cannot pass against incorrect DDL, parametrizes nine blocking mutations, and verifies forged appended rows fail signature validation. **Caveat:** the database-backed tests skip when no PostgreSQL is reachable (`test_audit_immutability.py:87-106`) and have likely never executed in CI.

The gap is that this trail covers **AG exports only**. Extending it to read-access events is the highest-leverage single remediation available.

---

## 7. Recommended Remediation Sequence

| Pri | Item | Addresses | Owner | Target | Verification |
|---|---|---|---|---|---|
| P1 | Issue signed ICASA/ECT applicability opinion | G-04, G-11, §2 | Legal & Compliance | Immediate | Signed opinion on file; §2 matrix approved |
| P1 | Obtain POPIA s.57(1) prior authorisation for unique-identifier linking, or stop linking | G-06 | Legal & Compliance | Immediate | Authorisation on file from the Information Regulator, or linking removed |
| P1 | Central PII field classification with one masking policy applied on every output path | G-06 | Platform Engineering | Sprint 1 | `backend/app/pii.py` is the only masking implementation; no ad-hoc masking in routers; test asserts no output path returns a raw ID number |
| P1 | Extend audit trail to read-access events | G-10 | Platform Engineering | Sprint 1 | Auth, tenant-switch, `/admin/users` and export events present in `audit.action_audit`; new tests in `test_audit_immutability.py` |
| P1 | Apply and commit `audit-role-split.sql` | G-03 | DBA | Sprint 1 | File tracked in git; runtime role confirmed unable to disable guards |
| P1 | Classify `id_number` as special personal information; encrypt at rest | G-06, G-08 | Platform Engineering | Sprint 1-2 | `pgcrypto` or KMS applied; no plaintext ID in any dump; classification recorded in control catalogue |
| P1 | Build cross-border transfer register | G-07 | Legal & Platform | Sprint 1-2 | Register covering PagerDuty, Teams, AppScan; DPA or onshore replacement per entry; egress allowlist enforced |
| P2 | Extend framework enum beyond `popia\|iso_27001` | §3 | Platform Engineering | Sprint 2 | ECT and RICA frameworks queryable; scope tags distinguish "applies" from "not applicable" |
| P2 | Replace seeded scores with a real control catalogue and evidence store | §6.1 | Platform Engineering | Sprint 2-3 | Control table, evidence artefact table, upload path; scores computed not seeded |
| P2 | Add retention jobs for `identity.persons`, `waf_blocks` | G-09 | DBA | Sprint 2 | pg_cron entries; documented retention schedule per personal-data class |
| P2 | Establish ECT s.53 CII designation status | G-02 | Legal | Sprint 2 | Written determination whether platform data is declared critical |
| P3 | Build cyber-inspector and legal-hold runbook | G-03 | Legal & Platform | Sprint 3 | Documented procedure; drill executed; break-glass path tested |
| P3 | Implement data-subject layer: consent, DSAR, erasure, minimisation | G-12 | Platform Engineering | Sprint 3-4 | DSAR workflow with SLA timer; erasure path; normaliser PII filtering with tests |
| P3 | Reconcile all documentation against code | §6.2 | Documentation Owner | Sprint 1 | Every row of §6.2 table resolved; `docs/F1:55` secret rotated and purged |

**Immediate housekeeping (corrected on review):** `docs/F1_Platform_Security_Hardening_Guide.md` contained literal `JWT_SECRET` and `BOOTSTRAP_ADMIN_PASSWORD` values in a **tracked** file, presented as a copy-and-paste production template. Both have been replaced with generation commands, because a secret committed to a tracked file must be treated as compromised. Note that `backend/.env` also holds live AppScan Cloud credentials, but it is **gitignored** (`.gitignore:23`) and untracked, so it cannot reach a commit — it remains a local-workstation exposure only, and should still be rotated if the workstation is shared.

---

## 7A. Data Flow Correction and Employment Identifier Remediation

### The data-flow boundary, stated correctly

An earlier draft of this document blurred the platform's data boundary. Corrected:

| Record class | Where it originates | Where it lives here |
|---|---|---|
| Employee / person attributes | Government HR systems (PERSAL, SCIM); SITA is the command centre | `identity.persons` — a **mirror**, not the source of truth |
| **Role, account and tenancy scope** | **Created in this platform** | `identity.users` — 54 accounts, 28 distinct roles, 17 estate-wide |

No platform account originates from a person record in the current dataset
(`identity.users.person_id` is NULL on all 54). Authority assignment is the
platform's own function, which makes `admin.user.create` / `update` / `delete`
the principal privilege-escalation surface — and the reason the access-audit
work in G-10 matters most.

### Identifier remediation (implemented 2026-10-09)

The single ambiguous `identity.persons.employee_number` string has been replaced
with a scheme-qualified identifier layer.

| Scheme | Form | Authority | Identifies |
|---|---|---|---|
| `persal` | exactly 8 digits | National Treasury via PERSAL | the **employment** |
| `sap_personnel` | 4-20 alphanumeric | SITA SAP HCM / IFMS HR module | the **employment** |
| `internal_hr` | 3-64 chars | originating feed | the **employment** |

The SA identity number (13 digits, Home Affairs) identifies the **person**, not
the employment, and is deliberately excluded. Keying an account on it would
collide across reappointment and import the estate's most sensitive POPIA s.57
unique identifier into account resolution.

Delivered:

- `identity.employment_identifier` table — `(person_id, scheme, value,
  source_system)` with `UNIQUE (scheme, value)`, so two people can never share
  a PERSAL number. Applied to the live database; 2,451 identifiers backfilled
  across 2,451 persons, zero orphans.
- `app/employment.py` — scheme registry, per-scheme validation, and
  `classify()` which returns `None` on an ambiguous shape rather than guessing.
- **SA identity-number guard.** A 13-digit ID structurally satisfies both the
  `internal_hr` and `sap_personnel` patterns. `looks_like_sa_id_number()`
  validates the `YYMMDD` prefix and the Luhn check digit, and every scheme
  rejects such a value with a message pointing to `app.pii`. A test caught this
  hole after the first implementation; closing it prevents a Home Affairs
  identity number being ingested as an employment identifier.
- `identity.users.person_id` remains an internal UUID. Government identifiers
  are attributes of an account, never its primary key, so a corrected or
  reissued PERSAL number does not require re-keying.
- HR sync records both `persal_number` (validated) and the feed's own
  `employee_number` (classified), rejecting malformed values with a log rather
  than failing the sync.
- `GET /admin/persons/by-identifier?scheme=&value=` and
  `GET /admin/employment/schemes`.

PERSAL number length is attested in PERSAL Instruction Note No. 3 of 2024-2025
(para 43) and the PERSAL User Management Policy. Neither DPSA nor National
Treasury publishes the format on public pages, so validate against the live feed
before enforcing in production. DPSA also operates a Public Servant Verification
service (13-digit ID → employed yes/no + department) usable for reconciliation,
but it **explicitly excludes the State Security Agency**.

---

## 8. Limitations of This Assessment

1. Assertions about absence were established by full-text search across `backend/`, `infrastructure/`, `docs/`, `docs/` and `frontend/`, with targeted reads of the compliance, audit, dispatch, models, security, tenancy, connector and infrastructure-DDL modules. Absence of a search hit is strong evidence but is not proof of absence in compiled artefacts or third-party components.
2. The `.docx` and `.xlsx` files in the repository root were not parsed for regulatory content; the generator scripts that produce them were inspected and contain no statutory framework content.
3. The statutory analysis is a technical applicability determination for engineering prioritisation. It is **not legal advice** and must be confirmed by counsel before being relied upon externally, particularly the RICA conditional determination and the ECT s.53 CII status.
4. Database-backed test results could not be confirmed as having been executed in CI, as the suite skips without a reachable PostgreSQL instance.