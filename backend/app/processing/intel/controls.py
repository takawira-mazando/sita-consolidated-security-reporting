"""Compliance controls computed from telemetry. No model, no external call.

Backs AVP-1. The scoring engine already exists and has never been called:
``app.processing.compliance`` holds ``POPIA_WEIGHTS`` (eight POPIA conditions),
``ISO_WEIGHTS`` (twelve Annex A themes) and ``compute_framework_score`` — a plain
weighted sum with **zero callers**, which is why ``compliance_snapshots`` carries
seeded fixture numbers and why the platform's own narrative admits it.

This module wires that dead engine to evidence and calls it. Nothing here
interprets, judges or ranks. It is a join per domain and a weighted sum over the
result.

What it does not pretend
------------------------
**Five of the eight POPIA conditions have no telemetry to bind to.** Consent,
purpose limitation, data-subject rights and breach response are absent from the
platform — ``docs/B5_ICASA_ECT_Gap_Analysis.md`` records the data-subject layer
as ``Absent`` with zero code for consent, erasure or DSAR. So those domains score
zero, with ``evidence_available: false`` and the reason stated.

That is the point. The seeded score claims 78%. The computed score will be
materially lower because the platform can only evidence three conditions and a
half. **A low number that is true is worth more than a high number that was
typed**, and the gap between the two is the finding the client needs to see.

Every figure carries ``evidence_available`` and ``denominator``. No percentage is
emitted whose denominator is not disclosed in the same object.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceSnapshot
from app.models.finding import Finding
from app.models.metrics import Agent, ApiEndpoint, DatabaseInventory, WafBlock
from app.processing.compliance import (
    ISO_WEIGHTS,
    POPIA_WEIGHTS,
    compute_popia_score,
)

#: Version stamped onto every computed score so an artefact can be traced to the
#: catalogue and weights that produced it.
ENGINE_VERSION = "controls-v1"

#: An agent heartbeat older than this is not evidence of monitoring.
AGENT_FRESHNESS_DAYS = 7

#: A WAF block newer than this is evidence the edge is still reporting.
WAF_ACTIVITY_DAYS = 30


@dataclass(frozen=True)
class Control:
    """One framework condition, and what would prove it.

    ``evidence`` names the observable that stands in for the control. Where there
    is none the control still exists in the catalogue — a law applies whether or
    not the platform can measure it — but it cannot score above zero and says so.
    """

    control_id: str
    framework: str
    domain: str
    title: str
    weight: float
    #: Key of the evidence function in ``EVIDENCE``, or None when none exists.
    evidence: str | None
    #: Why there is no evidence, when there is none.
    no_evidence_reason: str = ""


CATALOGUE: tuple[Control, ...] = (
    Control("popia-accountability", "popia", "data_inventory",
            "Accountability — personal information is inventoried",
            POPIA_WEIGHTS["data_inventory"], "inventory_coverage"),
    Control("popia-consent", "popia", "consent",
            "Processing is based on the data subject's consent",  # s.12
            POPIA_WEIGHTS["consent"], None,
            "No consent register, no DSAR workflow and no erasure path exist. "
            "B5 G-12 records the data-subject layer as Absent with zero code."),
    Control("popia-purpose", "popia", "purpose_limitation",
            "Collection is limited to a stated purpose",  # s.13
            POPIA_WEIGHTS["purpose_limitation"], None,
            "No purpose register exists. Findings carry an OEM category and an "
            "OWASP id, neither of which records why personal information was "
            "collected."),
    Control("popia-quality", "popia", "data_quality",
            "Personal information is complete, accurate and not excessive",
            POPIA_WEIGHTS["data_quality"], "classification_coverage"),
    Control("popia-safeguards", "popia", "security_safeguards",
            "Security safeguards appropriate to the information",  # s.19
            POPIA_WEIGHTS["security_safeguards"], "safeguards"),
    Control("popia-breach", "popia", "breach_response",
            "Security compromises are reported to the Regulator",  # s.22
            POPIA_WEIGHTS["breach_response"], None,
            "Detection exists — the DAM feed is breach detection — but there is "
            "no notification workflow or packet assembly. See AVP-5."),
    Control("popia-rights", "popia", "data_subject_rights",
            "Data subjects can access and correct their information",  # s.23-25
            POPIA_WEIGHTS["data_subject_rights"], None,
            "No access, correction or objection workflow exists."),
    Control("popia-cross-border", "popia", "cross_border",
            "Transfers to a foreign jurisdiction are lawful",  # s.44, s.57
            POPIA_WEIGHTS["cross_border"], "cross_border"),
)


@dataclass
class DomainResult:
    control_id: str
    domain: str
    title: str
    weight: float
    #: 0-100, or None when no evidence exists.
    pct: float | None
    evidence_available: bool
    detail: dict = field(default_factory=dict)
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "domain": self.domain,
            "title": self.title,
            "weight": self.weight,
            "pct": self.pct,
            "evidence_available": self.evidence_available,
            "evidence": self.detail,
            "no_evidence_reason": self.reason,
        }


# ---------------------------------------------------------------- evidence
async def _inventory_coverage(session: AsyncSession, claims) -> dict:
    """How much of the estate is actually catalogued.

    Denominator is the union of what the platform claims to hold, not a number
    invented here: databases recorded and API endpoints discovered.
    """
    from app.api.auth import tenant_filter

    dbs = tenant_filter(claims, DatabaseInventory)
    apis = tenant_filter(claims, ApiEndpoint)

    db_total = (
        await session.execute(select(func.count()).select_from(DatabaseInventory)
                             .where(*[dbs] if dbs is not None else []))
    ).scalar() or 0
    db_mon = (
        await session.execute(select(func.count()).select_from(DatabaseInventory)
                             .where(*([dbs] if dbs is not None else []),
                                    DatabaseInventory.monitored.is_(True)))
    ).scalar() or 0
    api_total = (
        await session.execute(select(func.count()).select_from(ApiEndpoint)
                             .where(*[apis] if apis is not None else []))
    ).scalar() or 0

    return {
        "databases_recorded": db_total,
        "databases_monitored": db_mon,
        "api_endpoints_discovered": api_total,
        "denominator": db_total + api_total,
        "note": (
            "Coverage of what the platform knows about. It is NOT coverage of the "
            "estate: there is no asset inventory, so an application absent from "
            "both tables is invisible and cannot be counted against it."
        ),
    }


async def _classification_coverage(session: AsyncSession, claims) -> dict:
    """Share of findings carrying a resolved taxonomy.

    ``findings.owasp_status`` is the classifier's own four-state outcome, which
    makes this the one data-quality measure the platform genuinely holds.
    """
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Finding)
    base = select(Finding.owasp_status, func.count()).group_by(Finding.owasp_status)
    if scope is not None:
        base = base.where(scope)
    rows = (await session.execute(base)).all()

    by_status = {r[0]: r[1] for r in rows if r[0]}
    total = sum(by_status.values())
    classified = by_status.get("classified", 0)
    return {
        "by_status": dict(sorted(by_status.items())),
        "denominator": total,
        "classified": classified,
        "unmapped": by_status.get("unmapped", 0),
    }


async def _safeguards(session: AsyncSession, claims) -> dict:
    """Security safeguards: monitoring coverage and operational freshness."""
    from datetime import datetime, timedelta, timezone

    from app.api.auth import tenant_filter

    dbs = tenant_filter(claims, DatabaseInventory)
    waf = tenant_filter(claims, WafBlock)

    db_total = (
        await session.execute(select(func.count()).select_from(DatabaseInventory)
                             .where(*[dbs] if dbs is not None else []))
    ).scalar() or 0
    db_mon = (
        await session.execute(select(func.count()).select_from(DatabaseInventory)
                             .where(*([dbs] if dbs is not None else []),
                                    DatabaseInventory.monitored.is_(True)))
    ).scalar() or 0

    # Agents carry no tenancy columns, so this is an estate-wide operational
    # signal and is labelled as such rather than silently blended with scoped
    # figures.
    cutoff = datetime.now(timezone.utc) - timedelta(days=AGENT_FRESHNESS_DAYS)
    agent_total = (
        await session.execute(select(func.count()).select_from(Agent))
    ).scalar() or 0
    agent_fresh = (
        await session.execute(
            select(func.count()).select_from(Agent).where(Agent.last_seen >= cutoff)
        )
    ).scalar() or 0

    waf_cutoff = datetime.now(timezone.utc) - timedelta(days=WAF_ACTIVITY_DAYS)
    waf_stmt = select(func.count()).select_from(WafBlock).where(WafBlock.block_time >= waf_cutoff)
    if waf is not None:
        waf_stmt = waf_stmt.where(waf)
    waf_recent = (await session.execute(waf_stmt)).scalar() or 0

    return {
        "databases_recorded": db_total,
        "databases_monitored": db_mon,
        "database_coverage_pct": round(db_mon / db_total * 100, 1) if db_total else 0.0,
        "agents_total_estate_wide": agent_total,
        "agents_reporting_within_7d_estate_wide": agent_fresh,
        "waf_blocks_last_30d": waf_recent,
        "denominator": "database_inventory rows for coverage; agent count is estate-wide",
    }


async def _cross_border() -> dict:
    """Transfer register: destinations with a mechanism on file.

    Pure function over the code-resident register in ``app.monitoring.egress``.
    No database, no network, and adding a destination is a code-review event —
    which is the control point.
    """
    from app.monitoring.egress import TRANSFER_REGISTER

    destinations = list(TRANSFER_REGISTER.values())
    authorised = [d for d in destinations if d.authorised]
    cross = [d for d in destinations if d.cross_border]
    return {
        "destinations_total": len(destinations),
        "destinations_authorised": len(authorised),
        "destinations_cross_border": len(cross),
        "destinations_cross_border_authorised": len([d for d in cross if d.authorised]),
        "unauthorised": sorted(d.id for d in destinations if not d.authorised),
        "denominator": len(destinations),
        "note": (
            "A low score here is correct and should not be read as a defect in "
            "the register. It is an accurate statement that the transfer "
            "agreements are not yet on file."
        ),
    }


async def _acknowledge_without_authority(session: AsyncSession, claims) -> dict:
    """Whether privileged alert actions were permission-checked when they happened.

    Thin wrapper over the AVP-11 check so ISO A.9 and the accountability
    proposition cannot drift apart: both read the same signed audit rows.
    """
    from app.processing.intel.privilege import acknowledge_without_authority

    rows = await acknowledge_without_authority(session, window_days=90)
    violations = len(rows)
    return {
        "privileged_alert_actions_checked": True,
        "actions_without_authority": violations,
        "examples": rows[:5],
        "denominator": "audit.action_audit rows for alert.acknowledge / alert.resolve, 90d",
        "note": (
            "Absence of violations is evidence of the check running, not proof it "
            "always did. This is the strongest signal available without an "
            "evidence store."
        ),
    }


async def _egress_transfer_mechanism() -> dict:
    """Declared transfer mechanisms, read from the code-resident register."""
    from app.monitoring.egress import TRANSFER_REGISTER

    destinations = list(TRANSFER_REGISTER.values())
    return {
        "destinations_declared": len(destinations),
        "destinations_authorised": len([d for d in destinations if d.authorised]),
        "denominator": len(destinations),
    }


EVIDENCE = {
    "inventory_coverage": _inventory_coverage,
    "classification_coverage": _classification_coverage,
    "safeguards": _safeguards,
    "cross_border": _cross_border,
    "acknowledge_without_authority": _acknowledge_without_authority,
    "egress_transfer_mechanism": _egress_transfer_mechanism,
}


def _pct_from(detail: dict, key_num: str, key_den: str) -> float:
    """Ratio as a percentage. Zero when the denominator is absent, never a crash."""
    num = detail.get(key_num) or 0
    den = detail.get(key_den) or 0
    return round(num / den * 100, 1) if den else 0.0


def _score_safeguards(detail: dict) -> float:
    """Two observable sub-indicators, averaged; each disclosed separately."""
    parts = []
    if detail.get("databases_recorded"):
        parts.append(detail["database_coverage_pct"])
    if detail.get("agents_total_estate_wide"):
        parts.append(round(
            detail["agents_reporting_within_7d_estate_wide"]
            / detail["agents_total_estate_wide"] * 100, 1
        ))
    return round(sum(parts) / len(parts), 1) if parts else 0.0


def _score_permission_checked(detail: dict) -> float:
    """100 when no privileged action breached the permission model."""
    checked = detail.get("privileged_alert_actions_checked")
    violations = detail.get("actions_without_authority") or 0
    if not checked:
        return 0.0
    return 100.0 if violations == 0 else 0.0


SCORERS = {
    "inventory_coverage": lambda d: _pct_from(d, "databases_monitored", "databases_recorded"),
    "classification_coverage": lambda d: _pct_from(d, "classified", "denominator"),
    "safeguards": _score_safeguards,
    "cross_border": lambda d: _pct_from(d, "destinations_authorised", "destinations_total"),
    "acknowledge_without_authority": _score_permission_checked,
    "egress_transfer_mechanism": lambda d: _pct_from(
        d, "destinations_authorised", "destinations_declared"
    ),
}


async def assess(session: AsyncSession, claims) -> dict:
    """Compute POPIA from telemetry by calling the existing, uncalled engine."""
    results: list[DomainResult] = []
    for control in CATALOGUE:
        if control.evidence is None:
            results.append(DomainResult(
                control_id=control.control_id, domain=control.domain,
                title=control.title, weight=control.weight, pct=None,
                evidence_available=False,
                reason=control.no_evidence_reason or "no evidence binding defined",
            ))
            continue
        fn = EVIDENCE[control.evidence]
        detail = await (fn(session, claims) if fn.__code__.co_argcount > 1 else fn())
        results.append(DomainResult(
            control_id=control.control_id, domain=control.domain,
            title=control.title, weight=control.weight,
            pct=SCORERS[control.evidence](detail),
            evidence_available=True, detail=detail,
        ))

    domain_scores = {r.domain: (r.pct or 0.0) for r in results}
    score = compute_popia_score(domain_scores)

    evidenced = [r for r in results if r.evidence_available]
    return {
        "avp": "AVP-1",
        "framework": "popia",
        "engine_version": ENGINE_VERSION,
        "computed": True,
        "computed_from": "telemetry",
        "requires_model": False,
        "score": score,
        "score_basis": "compute_popia_score over POPIA_WEIGHTS",
        "weights_source": "app.processing.compliance.POPIA_WEIGHTS",
        "conditions_total": len(results),
        "conditions_evidenced": len(evidenced),
        "conditions_without_evidence": len(results) - len(evidenced),
        "controls": [r.as_dict() for r in results],
        "domain_scores": domain_scores,
    }


async def compare_to_seeded(session: AsyncSession) -> dict:
    """The seeded figure beside the computed one — never blended.

    ``compliance_snapshots`` is unscopable, so this is an estate-wide comparison
    and is labelled as such. It exists so the size of the credibility gap is a
    number rather than a footnote.
    """
    rows = (
        await session.execute(
            select(ComplianceSnapshot)
            .where(ComplianceSnapshot.framework == "popia")
            .order_by(ComplianceSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).all()
    if not rows:
        return {"seeded_available": False}
    seeded = rows[0]
    return {
        "seeded_available": True,
        "seeded_scope": "estate_wide",
        "seeded_score": float(seeded.overall_score),
        "seeded_snapshot_date": seeded.snapshot_date.isoformat(),
        "seeded_note": (
            "Fixture data. compute_framework_score had no callers, so no code "
            "produced this number. Kept visible beside the computed score and "
            "never blended with it."
        ),
    }


async def assurance(session: AsyncSession, claims) -> dict:
    computed = await assess(session, claims)
    seeded = await compare_to_seeded(session)
    delta = None
    if seeded.get("seeded_available"):
        delta = round(seeded["seeded_score"] - computed["score"], 1)
    return {
        **computed,
        "scope_class": "tenant_scoped",
        "seeded_comparison": seeded,
        "seeded_minus_computed": delta,
        "caveat": (
            "The computed score is low because the platform can evidence three of "
            "eight POPIA conditions from telemetry. The remaining five are absent "
            "from the product, not badly implemented, and each carries its own "
            "reason. Closing them is the work this number is for."
        ),
    }


def iso_status() -> dict:
    """Honest statement of ISO readiness.

    ``ISO_WEIGHTS`` exists and ``compute_iso_score`` is callable. As of this
    revision four Annex A themes have an evidence binding and the rest do not,
    so — unlike POPIA, where every weighted domain is covered — **no ISO score is
    published**. Publishing a number from four of twelve themes would be the same
    defect this module exists to remove, wearing a smaller hat.

    The bindings that exist are listed so the remaining work is legible: the
    theme name is the thing that needs an evidence class, not new code.
    """
    bound = sorted(
        t for t, spec in ISO_BINDINGS.items() if spec[0] is not None
    )
    unbound = sorted(t for t in ISO_WEIGHTS if t not in bound)
    return {
        "avp": "AVP-1",
        "framework": "iso_27001",
        "computed": False,
        "score": None,
        "engine_version": ENGINE_VERSION,
        "weights_available": True,
        "themes_total": len(ISO_WEIGHTS),
        "themes_with_evidence_binding": len(bound),
        "themes_bound": bound,
        "themes_unbound": unbound,
        "reason": (
            f"compute_iso_score is implemented and callable, but only {len(bound)} of "
            f"{len(ISO_WEIGHTS)} Annex A themes have an evidence binding. A score "
            "from a partial control set overstates coverage in the one direction "
            "that matters for an auditor, so none is published."
        ),
        "requires_model": False,
    }


#: Annex A themes that can be evidenced from telemetry the platform already
#: holds. ``(evidence_key, why_absent)``. Themes outside this table have no
#: binding and score nothing.
ISO_BINDINGS: dict[str, tuple[str | None, str]] = {
    "A.5_ISMS": (None, "A policy system is a document set, not telemetry."),
    "A.6_organisation": (None, "Roles exist but organisational responsibility is not "
                               "evidenced by anything the platform observes."),
    "A.7_HR": (None, "Requires the employment records the platform deliberately does "
                     "not retain, and identity.users.person_id is NULL throughout."),
    "A.8_assets": ("inventory_coverage",
                   "Partial: this measures what is catalogued, not asset management."),
    "A.9_access": ("acknowledge_without_authority",
                   "Partial: evidences that alert actions were permission-checked, "
                   "not the full access control theme."),
    "A.10_crypto": ("egress_transfer_mechanism",
                    "Partial: evidences declared transfer mechanisms, not the use of "
                    "cryptography."),
    "A.11_physical": (None, "Physical security is wholly outside a software platform."),
    "A.12_operations": ("safeguards",
                        "Partial: monitoring coverage and freshness only."),
    "A.13_communications": (None, "Network segmentation is not observable from this "
                                  "platform's position."),
    "A.14_acquisition": ("classification_coverage",
                         "Partial: supplier security is not observable; this evidences "
                         "data classification only."),
    "A.15_supplier": (None, "No supplier register exists."),
    "A.16_incident": (None, "No incident-management workflow exists yet. AVP-5 builds "
                            "part of one."),
}