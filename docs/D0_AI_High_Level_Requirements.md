# SITA Platform — AI Integration Requirements
**Project:** AI Narrative Reporting
**Client:** State Information Technology Agency (SITA)
**Date:** 8 October 2026
**Status:** Proposed — Awaiting Client Sign-off

---

## Outcome 1 — Plain-language security reports, on demand

The client needs executives and compliance officers to receive written summaries of the platform's security and compliance posture — without manually interpreting dashboards.

| Req | Requirement |
|---|---|
| AI-01 | The system shall generate a written narrative report from live warehouse data on demand |
| AI-02 | The report shall be written in plain language suitable for an executive or compliance audience |
| AI-03 | Two report types shall be available at go-live: **Executive Briefing** and **Compliance Status** |
| AI-04 | Six additional report types shall be delivered by December 2026, bringing the total to eight |
| AI-05 | Reports shall be accessible through the existing platform dashboard — no new login, no new application |

---

## Outcome 2 — Every user sees only what they are authorised to see

The client needs assurance that a report generated for one department cannot expose another department's data, and that an unknown or unauthorised user receives nothing.

| Req | Requirement |
|---|---|
| AI-06 | The system shall generate each report scoped exactly to the requesting user's authorised data view |
| AI-07 | A user with no scope (e.g. a department administrator with no linked data) shall receive a report with zero findings |
| AI-08 | A user attempting to access data outside their scope shall receive an empty result — never escalated or estate-wide data |
| AI-09 | An unrecognised or unauthorised user shall be refused access with a clear error — never an empty report that could be mistaken for clean data |
| AI-10 | All 14 platform roles shall be tested against every report type to confirm correct access behaviour |

---

## Outcome 3 — Every number in a report is real and verifiable

The client needs confidence that figures in a generated report match the warehouse and can be traced back to their source — not hallucinated or illustrative.

| Req | Requirement |
|---|---|
| AI-11 | Every figure in a generated report shall exist in the source data. A figure that cannot be verified shall cause the report to be discarded and regenerated via template |
| AI-12 | Every report shall include a grounding reference so any figure can be traced to the exact source record it came from |
| AI-13 | Compliance data covering the whole estate (not a single department) shall be clearly labelled as estate-wide in the report — never presented as department-specific |
| AI-14 | Report examples and test data used during development shall be drawn from live data, not invented figures |

---

## Outcome 4 — Reports are available even when the AI model is not

The client needs the reporting capability to remain available during model outages — with no degradation to dashboard performance.

| Req | Requirement |
|---|---|
| AI-15 | If the AI model is unavailable, the system shall deliver a report using the same verified data via a pre-built template |
| AI-16 | The template report shall carry identical figures to what the model would have produced — the only difference is that the prose is fixed |
| AI-17 | The response shall indicate whether the report was model-generated or template-generated |
| AI-18 | A model failure shall not degrade any existing dashboard or data view |

---

## Outcome 5 — Every report can be audited and reproduced

The client needs to be able to look up any generated report after the fact — what it said, what data it used, which model produced it, and who requested it.

| Req | Requirement |
|---|---|
| AI-19 | Every generated report shall be logged with the model identity, prompt version, and timestamp |
| AI-20 | The data folder used to produce a report shall be retrievable for any report by its ID |
| AI-21 | Where a user submits a custom prompt, the submitted prompt (not the template) shall be stored in the audit log |
| AI-22 | Every AI recommendation that is acted on shall be traceable to the named person who accepted it |

---

## Outcome 6 — Users can request the specific narrative they need

The client needs users to be able to direct the report toward the facts most relevant to their audience — without this expanding what data they are allowed to see.

| Req | Requirement |
|---|---|
| AI-23 | A user shall be able to specify which aspects of their authorised data the report should focus on |
| AI-24 | Focusing on a subset of the data shall not grant access to data outside the user's scope |
| AI-25 | The eight report types shall be offered as editable starting points, not fixed templates |
| AI-26 | Editing a starting-point template shall not widen the user's data access |

---

## Outcome 7 — Reports can be saved and shared

The client needs generated reports to be exportable in standard formats for distribution and record-keeping.

| Req | Requirement |
|---|---|
| AI-27 | All eight report types shall be exportable to **CSV** |
| AI-28 | All eight report types shall be exportable to **PDF** |

---

## Quality targets

| Attribute | Target |
|---|---|
| Report delivery time — returning user | Under 8 seconds |
| Report delivery time — first request | Under 20 seconds |
| Data accuracy | 100% — every figure verified before delivery |
| Cross-department data exposure | Zero |
| Dashboard availability impact | Zero — a model failure does not affect any existing view |

---

## Sign-off

| Role | Name | Date |
|---|---|---|
| Client Representative | | |
| Business Analyst | Peter Rashaya | |
| Technical Lead | Takawira Mazando | |
| Compliance | | |
