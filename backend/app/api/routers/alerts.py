from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.alert import Alert
from app.db import get_session
from app.models.alert import Alert as AlertModel, AlertStatus
from typing import Optional
from math import ceil

router = APIRouter(tags=["alerts"])


def _severity(value):
    return value.value if hasattr(value, "value") else value


def _status(value):
    return value.value if hasattr(value, "value") else value


@router.get("/alerts", response_model=PaginatedResponse)
async def get_alerts(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_read")),
):
    filters = []
    if severity:
        filters.append(AlertModel.severity == severity)
    if status:
        filters.append(AlertModel.status == status)
    if source:
        filters.append(AlertModel.source == source)
    if since:
        filters.append(AlertModel.last_triggered >= since)

    q = select(AlertModel).where(*filters).order_by(AlertModel.last_triggered.desc())
    q = q.offset((page - 1) * size).limit(size)
    rows = (await session.execute(q)).scalars().all()

    items = [
        Alert(
            id=r.id,
            rule_id=r.rule_id,
            title=r.title,
            description=r.description,
            severity=_severity(r.severity),
            source=r.source,
            target_id=r.target_id,
            status=_status(r.status),
            acknowledged_by=r.acknowledged_by,
            acknowledged_at=r.acknowledged_at,
            first_triggered=r.first_triggered,
            last_triggered=r.last_triggered,
            created_at=r.created_at,
        )
        for r in rows
    ]
    total = len(items)
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_write")),
):
    from datetime import datetime, timezone
    row = (
        await session.execute(
            select(AlertModel).where(AlertModel.id == alert_id)
        )
    ).scalar_one_or_none()
    if row is None:
        return {"id": alert_id, "status": "not_found"}
    row.status = AlertStatus.ACKNOWLEDGED
    row.acknowledged_by = claims.email or claims.sub
    row.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    return {"id": alert_id, "status": "acknowledged"}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_write")),
):
    from datetime import datetime, timezone
    row = (
        await session.execute(
            select(AlertModel).where(AlertModel.id == alert_id)
        )
    ).scalar_one_or_none()
    if row is None:
        return {"id": alert_id, "status": "not_found"}
    row.status = AlertStatus.RESOLVED
    row.resolved_at = datetime.now(timezone.utc)
    await session.commit()
    return {"id": alert_id, "status": "resolved"}
