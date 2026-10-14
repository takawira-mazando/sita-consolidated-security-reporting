"""Deterministic intelligence endpoints.

Serves the part of the value-proposition set that requires no model. Every route
here is a join, an aggregate, or arithmetic over columns the warehouse already
carries. None of them opens a network connection or calls a model, which is
what makes each one testable with every AI dependency switched off and safe to
sign.

Permissions are additive namespaces in the same style as the value
propositions, and ``ROLES_HIERARCHY`` is not modified. The capability manifest is
open to any authenticated caller because it describes the platform, not an
estate — it returns which propositions are deterministic, which are gated, and
what the blocked parts are blocked on. No estate data, no counts.

``/intel/privilege`` is deliberately estate-wide and deliberately held away from
administrators: it audits the platform's own privileged actions, so no admin tier
and no executive role may hold it. See the module docstring in
``app.processing.intel.privilege``.
"""
from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.processing.intel import (
    attack,
    author_rules,
    behaviour,
    campaign,
    capability,
    causal,
    controls,
    delta,
    estate,
    packet,
    peer,
    popia,
    privilege,
    vendor,
)

router = APIRouter(prefix="/intel", tags=["intel"])


@router.get("/capability")
async def get_capability():
    """Which propositions are deterministic and which are genuinely gated.

    Open to any authenticated caller: it describes the platform's own
    capability boundary and contains no tenant data.
    """
    return capability.manifest()


@router.get("/vendor/contradictions")
async def get_vendor_contradictions(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    """Cross-OEM contradictions (AVP-4). Deterministic."""
    return await vendor.contradictions(session, claims)


@router.get("/vendor/attestation")
async def get_vendor_attestation(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    """Coverage and agreement across sources (AVP-10). Deterministic.

    Returns ``denominator_known: false``. No asset inventory exists, so no
    coverage percentage is published — see the response's ``denominator_note``.
    """
    return await vendor.attestation(session, claims)


@router.get("/estate/ownership")
async def get_estate_ownership(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    """Ownership ambiguity and blast radius (AVP-6). Deterministic."""
    return await estate.estate_graph(session, claims)


@router.get("/risk/movers")
async def get_risk_movers(
    window_days: int = Query(14, ge=1, le=90),
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    """Applications whose fused score moved most (AVP-8 stage a). Deterministic."""
    return await delta.largest_movers(session, claims, window_days, limit)


@router.get("/risk/delta")
async def get_risk_delta(
    app_name: str = Query(..., min_length=1, max_length=255),
    window_days: int = Query(14, ge=2, le=90),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    """Decompose one application's score movement by signal (AVP-8 stage a).

    Stage (b), the external cause, is not available: it needs campaign
    enrichment and a ``findings.cve_id`` column that does not exist. The
    response says so explicitly under ``external_cause`` rather than omitting it.
    """
    return await delta.app_delta(session, claims, app_name, window_days)


@router.get("/controls/score")
async def get_control_score(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    """POPIA computed from telemetry (AVP-1). Deterministic.

    Calls ``compute_popia_score``, which existed in
    ``app.processing.compliance`` with zero callers. No model, no external
    service, no AIMI dependency.

    The score will be materially lower than the seeded figure it is compared
    against, because five of the eight POPIA conditions have no telemetry to
    bind to and score zero with the reason stated. That is the correct answer,
    not a defect in the computation.
    """
    return await controls.assurance(session, claims)


@router.get("/controls/iso")
async def get_iso_status(
    claims = Depends(require_roles("compliance")),
):
    """ISO 27001 readiness. Deliberately returns no score (AVP-1).

    Four Annex A themes now have an evidence binding and eight do not. A score
    from four of twelve themes would overstate coverage in the one direction an
    auditor cares about, so none is published — the bound and unbound themes are
    returned instead, which makes the remaining work legible.
    """
    return controls.iso_status()


@router.get("/peer/prescription")
async def get_peer_prescription(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    """Control gaps in the caller's own estate, ranked by live exposure (AVP-7).

    Deterministic set difference. **No peer department's findings, counts or
    request URIs are read** — the blinded ranking that prompts a department to
    open this endpoint stays exactly as ``benchmark`` already presents it.
    """
    return await peer.prescribe(session, claims)


@router.get("/attack/coverage")
async def get_attack_coverage(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    """Red against blue ATT&CK coverage (AVP-2, deterministic half).

    Red is techniques the estate is exposed to, from the CWE already classified
    onto every finding. Blue is techniques the platform's own alert rules can
    evidence, from a side table. The gap between them is the deliverable.

    Curated mapping data only. No model.
    """
    return await attack.coverage(session, claims)


@router.get("/hunts")
async def get_hunts(
    limit: int = Query(10, ge=1, le=25),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    """Coverage gaps turned into runnable hunt cards (AVP-9).

    Every field is computed: the gap from coverage, the query from curated
    column bindings, the expected hit shape from the caller's own rows.
    """
    return await attack.hunts(session, claims, limit)


@router.post("/packet")
async def post_packet(
    alert_id: str | None = Query(None, max_length=64),
    app_name: str | None = Query(None, max_length=255),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    """Assemble and sign a dispute-ready evidence packet (AVP-12).

    Reuses the AG attestation's ECDSA primitives, so it verifies by exactly the
    same published procedure. ``generated_at`` is excluded from the signed body,
    so two packets over the same facts are byte-identical.

    Requires an anchor. With neither ``alert_id`` nor ``app_name`` this would be
    the AG attestation, which already exists.
    """
    return await packet.build(session, claims, alert_id, app_name)


@router.post("/privilege/audit")
async def post_privilege_audit(
    window_days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    """Accountability checks over the signed audit trail (AVP-11). Deterministic.

    POST rather than GET: the trail it reads records the caller's own actions,
    and ``demoInterceptor`` rewrites any GET whose path matches a demo pattern.
    Holding this route excludes every admin tier — an administrator does not get
    the tool that audits administrators.
    """
    return await privilege.privilege_audit(session, window_days)


# ---------------------------------------------------------------------------
# AI-Residue endpoints  (advisory-only, require human review before any action)
# ---------------------------------------------------------------------------

@router.post("/attack/author-rule", tags=["intel", "ai-residue"])
async def post_author_rule(
    technique_id: str = Query(..., min_length=3, max_length=16,
                               description="MITRE ATT&CK technique ID, e.g. T1190"),
    technique_name: str | None = Query(None, max_length=255),
    severity: str | None = Query(None, pattern="^(critical|high|medium|low)$"),
    target_source: str | None = Query(None, max_length=64),
    claims=Depends(require_roles("findings")),
):
    """Author a reviewable alert-rule proposal for a technique (AVP-2 AI residue).

    Advisory only: the rule is NEVER automatically merged. The response contains
    a git diff that a platform operator must review and approve before the rule
    is added to ``alert_rules.yaml``.
    """
    return author_rules.author_rule_for_technique(
        technique_id=technique_id,
        technique_name=technique_name,
        custom_severity=severity,
        target_source=target_source,
    )


@router.post("/threat/attribute", tags=["intel", "ai-residue"])
async def post_attribute_campaign(
    report_text: str = Body(..., media_type="text/plain",
                             description="Raw text of a threat report (OSINT, CTI feed, MITRE ATT&CK advisory)."),
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("findings")),
):
    """Attribute a threat report to this estate (AVP-3 AI residue).

    Deterministically extracts ATT&CK techniques, CVEs, and adjacent-sector
    keywords from the supplied report text, then cross-references them against
    the estate's own exposure. Returns a structured attribution dossier for
    analyst review. Advisory only — no alert rules are created.
    """
    # Fetch estate exposure for cross-reference
    try:
        coverage_data = await attack.coverage(session, claims)
        exposed = [t["technique_id"] for t in coverage_data.get("exposed", [])]
        covered = [t["technique_id"] for t in coverage_data.get("covered", [])]
    except Exception:
        exposed, covered = [], []

    result = campaign.attribute_campaign(
        report_text=report_text,
        estate_exposed_techniques=exposed,
        estate_covered_techniques=covered,
    )
    return result.__dict__


@router.post("/popia/dossier", tags=["intel", "ai-residue"])
async def post_popia_dossier(
    alert_id: str | None = Query(None, max_length=64),
    app_name: str | None = Query(None, max_length=255),
    window_days: int = Query(30, ge=1, le=180),
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("compliance")),
):
    """Assemble a POPIA s.22 breach-notification evidence dossier (AVP-5 AI residue).

    Gathers platform-held evidence (findings, alerts) and returns a structured
    dossier anchored to a specific alert or application. The statutory threshold
    judgement (s.22(1)) and the notification narrative are **deliberately withheld**
    and flagged for human legal review.
    """
    return await popia.assemble_breach_dossier(
        session=session,
        claims=claims,
        alert_id=alert_id,
        app_name=app_name,
        window_days=window_days,
    )


@router.post("/risk/causal", tags=["intel", "ai-residue"])
async def post_risk_causal(
    app_name: str = Query(..., min_length=1, max_length=255),
    window_days: int = Query(14, ge=2, le=90),
    threat_report: str | None = Body(None, media_type="text/plain",
                                     description="Optional raw threat-report text to cross-reference against the delta."),
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("risks")),
):
    """Explain a risk-delta movement with external-cause context (AVP-8 AI residue).

    Stage (a) decomposition is already available via ``GET /intel/risk/delta``.
    This endpoint adds the external-cause hypothesis: maps the dominant signal
    to an ATT&CK technique and, if a threat report is supplied, checks whether
    that technique appears in the report. Advisory only — analyst review required.
    """
    delta_payload = await delta.app_delta(session, claims, app_name, window_days)
    return causal.enrich_delta_with_context(
        delta_payload=delta_payload,
        threat_report_text=threat_report,
    )


@router.post("/audit/explain", tags=["intel", "ai-residue"])
async def post_explain_behaviour(
    window_days: int = Query(30, ge=1, le=365),
    actor_id: str | None = Query(None, max_length=255,
                                  description="Scope to a single actor. Omit to analyse all actors."),
    min_confidence: int = Query(2, ge=1, le=10,
                                description="Minimum corroborating-signal count to flag a cluster."),
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("compliance")),
):
    """Explain multi-step behavioural patterns in the signed audit trail (AVP-11 AI residue).

    Groups audit events into temporal clusters and labels patterns that no
    single per-row rule would flag (self-approve chains, escalating exports,
    cross-scope pivots, rapid authority sweeps). Returns a structured report
    for analyst review. Advisory only — no disciplinary actions are created.
    """
    result = await behaviour.explain_behaviour(
        session=session,
        window_days=window_days,
        actor_id=actor_id,
        min_confidence=min_confidence,
    )
    # Convert dataclasses to dicts for JSON serialisation
    import dataclasses
    return dataclasses.asdict(result)