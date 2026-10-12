"""Regulatory framework registry with an explicit applicability determination.

Closes the registry half of the §3 and §7/P2 findings in
``docs/B5_ICASA_ECT_Gap_Analysis.md``.

The compliance API previously validated ``framework`` against
``pattern="^(popia|iso_27001)$"`` — a closed set that made it impossible to ask
the platform about the Electronic Communications and Transactions Act, RICA, or
the National Cybersecurity Act, and just as impossible to record a considered
determination that they do not apply.

Applicability is a first-class attribute rather than an omission. A framework
that does not bind this platform is registered as ``not_applicable`` with the
reason, so the answer to "did you consider the ECT Act?" is a stored, reviewable
position instead of silence.

Determinations are technical assessments for engineering prioritisation. They
are **not legal advice** and must be confirmed by counsel — see B5 §2 and §8.
"""
from __future__ import annotations

from dataclasses import dataclass

APPLIES = "applies"
CONDITIONAL = "conditional"
NOT_APPLICABLE = "not_applicable"
PARTIAL = "partial"


@dataclass(frozen=True)
class Framework:
    id: str
    name: str
    instrument: str
    applicability: str
    rationale: str
    #: Where the platform currently stands against this instrument.
    coverage: str
    gaps: tuple[str, ...] = ()
    regulator: str = ""

    @property
    def applicable(self) -> bool:
        return self.applicability in (APPLIES, CONDITIONAL, PARTIAL)


FRAMEWORKS: dict[str, Framework] = {
    "popia": Framework(
        id="popia",
        name="Protection of Personal Information Act",
        instrument="Act 4 of 2013",
        applicability=APPLIES,
        regulator="Information Regulator (not ICASA)",
        rationale=(
            "The platform is a responsible party for HR-sourced person records "
            "and an operator for department tenants."
        ),
        coverage=(
            "Weighted domain scoring exists but is seeded, not computed; "
            "output-path masking is now centralised in app.pii."
        ),
        gaps=(
            "s.57(1)(a) prior authorisation for unique-identifier linking not held",
            "No encryption at rest for identity.persons.id_number",
            "No consent, DSAR or erasure workflow",
            "No data-subject access request handling",
            "Cross-border transfer agreements not on file",
            "Read-access auditing only recently added (app.monitoring.access_audit)",
        ),
    ),
    "iso_27001": Framework(
        id="iso_27001",
        name="ISO/IEC 27001 Information Security Management",
        instrument="ISO/IEC 27001:2013 Annex A (code implements 2013 numbering)",
        applicability=APPLIES,
        regulator="Certification body (voluntary)",
        rationale="Baseline information security management control set.",
        coverage=(
            "Twelve Annex A themes weighted for scoring; seeded snapshots "
            "rather than computed scores."
        ),
        gaps=(
            "Documentation claims 27001:2022 while the code uses 2013 controls",
            "Scoring functions have no callers",
        ),
    ),
    "ect_act": Framework(
        id="ect_act",
        name="Electronic Communications and Transactions Act",
        instrument="Act 25 of 2002",
        applicability=PARTIAL,
        regulator=(
            "Minister / Department of Communications and Digital Technologies; "
            "ICASA may make recommendations under ICASA Act s.4(o)"
        ),
        rationale=(
            "Applies to e-services provided by public bodies and to the "
            "declaration of critical information infrastructure. SITA is a "
            "public body operating an e-service platform."
        ),
        coverage=(
            "Platform serves authenticated users and issues machine-readable "
            "responses with integrity headers."
        ),
        gaps=(
            "No record of critical information infrastructure status under s.53",
            "No cyber-inspector or legal-hold procedure (ECT Ch. XII, s.80-84)",
            "No documented hosting-provider determination under s.75-77",
            "s.78 no-obligation-to-monitor position not recorded",
        ),
    ),
    "rica": Framework(
        id="rica",
        name="Regulation of Interception of Communications and Provision of "
             "Communication-related Information Act",
        instrument="Act 70 of 2002",
        applicability=NOT_APPLICABLE,
        regulator="Minister of Justice and Constitutional Development",
        rationale=(
            "RICA binds telecommunication service providers. SITA holds no "
            "ICAMS licence, provides no electronic communications service or "
            "network service, and operates no interception capability. With no "
            "interception capability there is no s.28/s.30 duty and no "
            "communication-related information to store."
        ),
        coverage=(
            "Conformant by absence of capability: the platform neither "
            "intercepts communications nor holds subscriber records."
        ),
        gaps=(
            "Conditional: re-examine if SITA ever assumes a TSP function, "
            "co-hosts with an operator, or is designated to assist registered agencies",
        ),
    ),
    "ncia": Framework(
        id="ncia",
        name="National Cybersecurity Act / critical information infrastructure",
        instrument="Act 33 of 2021",
        applicability=CONDITIONAL,
        regulator="Minister of ICT; Centre for Cybersecurity South Africa",
        rationale=(
            "Engages if the platform or its data estate is declared critical "
            "information infrastructure. That designation is not currently "
            "recorded either way."
        ),
        coverage="No designation status tracked; CSIRT notification is roadmap only.",
        gaps=(
            "Determine and record CII designation status",
            "No CSIRT notification channel (docs/SITA_Executive_Presentation_Deck.md:184)",
        ),
    ),
    "icasa_eca": Framework(
        id="icasa_eca",
        name="Electronic Communications Act / ICASA licence conditions",
        instrument="Act 36 of 2005; ICASA Act 13 of 2000",
        applicability=NOT_APPLICABLE,
        regulator="Independent Communications Authority of South Africa",
        rationale=(
            "Regulates ECS and ECNS licensees. SITA is a Schedule 3A public "
            "entity holding no communications licence, operating no electronic "
            "communications network and supplying no type-approved equipment. "
            "ICASA's compliance model does not apply, and compliance must not "
            "be asserted against it."
        ),
        coverage=(
            "ICASA appears only as a customer tenant (app.tenant.DEPARTMENTS). "
            "Its own obligations reach the platform contractually as processor "
            "duties, enforced by the Information Regulator rather than ICASA."
        ),
        gaps=(
            "Applicability determination not yet issued as a signed opinion",
            "ICASA tenant data is processed without a documented DPA or transfer basis",
        ),
    ),
}


def get(framework_id: str) -> Framework:
    return FRAMEWORKS[framework_id]


def ids() -> list[str]:
    return list(FRAMEWORKS)


def applicable_ids() -> list[str]:
    return [f.id for f in FRAMEWORKS.values() if f.applicable]


def as_dicts() -> list[dict]:
    return [
        {
            "id": f.id,
            "name": f.name,
            "instrument": f.instrument,
            "applicability": f.applicability,
            "applicable": f.applicable,
            "regulator": f.regulator,
            "rationale": f.rationale,
            "coverage": f.coverage,
            "gaps": list(f.gaps),
        }
        for f in FRAMEWORKS.values()
    ]