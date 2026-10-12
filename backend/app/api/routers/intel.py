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
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.processing.intel import (
    attack,
    capability,
    controls,
    delta,
    estate,
    packet,
    peer,
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