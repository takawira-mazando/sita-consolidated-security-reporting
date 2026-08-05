from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.models.compliance import ComplianceGap, ComplianceSnapshot

router = APIRouter(tags=["compliance"])


@router.get("/compliance")
async def get_compliance(
    framework: str | None = Query(None, regex="^(popia|iso_27001)$"),
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
    horizon = date.today() + timedelta(days=30)
    expiring = sum(
        1 for r in rows
        if r.due_date and r.status not in ("closed", "remediated") and r.due_date <= horizon
    )

    return {
        "available": available,
        "missing": missing,
        "expiring": expiring,
        "total": total,
    }
