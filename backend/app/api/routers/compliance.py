from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.models.compliance import ComplianceGap, ComplianceSnapshot
from app.monitoring.egress import open_findings
from app.processing.frameworks import FRAMEWORKS, as_dicts

router = APIRouter(tags=["compliance"])

#: Built from the registry so the accepted values can never drift from the
#: frameworks the platform has actually assessed. Previously hardcoded as a
#: regex, which made an unassessed framework indistinguishable from a forgotten
#: one.
FRAMEWORK_IDS = "|".join(FRAMEWORKS)


@router.get("/compliance")
async def get_compliance(
    framework: str | None = Query(None, pattern=f"^({FRAMEWORK_IDS})$"),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    q = select(ComplianceSnapshot)
    if framework:
        q = q.where(ComplianceSnapshot.framework == framework)
    q = q.order_by(ComplianceSnapshot.snapshot_date.desc())
    rows = (await session.execute(q)).scalars().all()
    if not rows:
        return {"framework": framework or "all", "overall_score": 0, "snapshot_date": "", "total_controls": 0, "passed_controls": 0}
    latest = rows[0]
    return {
        "framework": framework or latest.framework,
        "overall_score": float(latest.overall_score),
        "snapshot_date": latest.snapshot_date.isoformat(),
        "total_controls": latest.total_controls,
        "passed_controls": latest.passed_controls,
    }


@router.get("/compliance/gaps")
async def get_compliance_gaps(
    framework: str | None = Query(None),
    status: str | None = Query(None),
    sort_by: str = Query("due_date"),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    q = select(ComplianceGap)
    if framework:
        q = q.where(ComplianceGap.framework == framework)
    if status:
        q = q.where(ComplianceGap.status == status)
    order_col = ComplianceGap.due_date if sort_by == "due_date" else ComplianceGap.severity
    q = q.order_by(order_col)
    rows = (await session.execute(q)).scalars().all()
    return {"items": [
        {
            "id": r.id,
            "framework": r.framework,
            "control_id": r.control_id,
            "domain": r.domain,
            "description": r.description,
            "owner": r.owner,
            "severity": r.severity,
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "status": r.status,
        }
        for r in rows
    ]}


EVIDENCE_EXPIRY_DAYS = 30


@router.get("/compliance/evidence")
async def get_evidence(
    gap_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    q = select(ComplianceGap)
    if gap_id:
        q = q.where(ComplianceGap.id == gap_id)
    rows = (await session.execute(q)).scalars().all()

    total = len(rows)
    available = sum(1 for r in rows if (r.evidence_count or 0) > 0)
    missing = total - available
    horizon = date.today() + timedelta(days=EVIDENCE_EXPIRY_DAYS)
    expiring = sum(
        1 for r in rows
        if r.due_date and r.status not in ("closed", "remediated") and r.due_date <= horizon
    )

    return {
        "available": available,
        "missing": missing,
        "expiring": expiring,
        "total": total,
        "expiry_horizon_days": EVIDENCE_EXPIRY_DAYS,
    }


@router.get("/compliance/frameworks")
async def list_frameworks(
    claims = Depends(require_roles("compliance")),
):
    """Every regulatory framework assessed, with its applicability determination.

    Frameworks that do not bind the platform are returned with
    ``applicability: not_applicable`` and a stated rationale, so a considered
    determination is visible rather than implied by omission.
    """
    return {
        "frameworks": as_dicts(),
        "note": (
            "Applicability determinations are technical assessments for "
            "engineering prioritisation, not legal advice. See "
            "docs/B5_ICASA_ECT_Gap_Analysis.md sections 2 and 8."
        ),
    }


@router.get("/compliance/transfers")
async def list_transfers(
    claims = Depends(require_roles("compliance")),
):
    """Cross-border data transfer register: destinations without a mechanism on file.

    The working list for closing gap G-07. Every entry here is an external
    system the platform exchanges South African government data with where no
    data transfer agreement or prior authorisation has been recorded.
    """
    return {
        "open_transfers": open_findings(),
        "note": (
            "Register maintained in app.monitoring.egress. An entry appears "
            "here until a transfer mechanism is recorded against it."
        ),
    }
