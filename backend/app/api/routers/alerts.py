from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import check_tenancy_access, require_roles, tenant_filter
from app.api.schemas.alert import Alert
from app.api.schemas.common import PaginatedResponse
from app.db import get_session
from app.models.alert import Alert as AlertModel
from app.models.alert import AlertStatus, DispatchLog
from app.monitoring.access_audit import (
    record_access,
    request_context,
    scope_digest,
)

router = APIRouter(tags=["alerts"])


def _audit_alert_action(
    session: AsyncSession,
    request: Request | None,
    claims,
    action: str,
    alert_id: str,
    detail: dict,
) -> None:
    """Record a state change or outbound notification on an alert.

    Alert acknowledgement and dispatch are the actions a regulator or auditor
    asks about first in an incident review: who knew, when, and what left the
    platform as a result.
    """
    depts = list(getattr(claims, "department_ids", None) or [])
    branches = list(getattr(claims, "branch_ids", None) or [])
    provinces = list(getattr(claims, "province_ids", None) or [])
    roles = list(getattr(claims, "roles", None) or [])
    record_access(
        session,
        action=action,
        actor=getattr(claims, "email", None) or claims.sub,
        target=alert_id,
        tenant_scope={
            "department_ids": depts,
            "branch_ids": branches,
            "province_ids": provinces,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(depts, branches, provinces, roles),
        detail={**detail, **request_context(request)},
    )


def _severity(value):
    return value.value if hasattr(value, "value") else value


def _status(value):
    return value.value if hasattr(value, "value") else value


@router.get("/alerts", response_model=PaginatedResponse)
async def get_alerts(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    source: str | None = Query(None),
    since: str | None = Query(None),
    department_id: str | None = Query(None, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$", description="Filter by department within assigned scope"),
    branch_id: str | None = Query(None, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$", description="Filter by branch within assigned scope"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_read")),
):
    filters = []
    scope = tenant_filter(claims, AlertModel)
    if scope is not None:
        filters.append(scope)
    if department_id or branch_id:
        check_tenancy_access(claims, department_id, branch_id)
        if department_id:
            filters.append(AlertModel.department_id == department_id)
        if branch_id:
            filters.append(AlertModel.branch_id == branch_id)
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
            last_dispatched_at=r.last_dispatched_at,
            resolved_at=r.resolved_at,
            dedup_count=r.dedup_count,
            channels=r.channels,
            enriched_data=r.enriched_data,
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


@router.get("/alerts/{alert_id}/dispatch", response_model=list)
async def get_alert_dispatch(
    alert_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_read")),
):
    q = select(DispatchLog).where(DispatchLog.alert_id == alert_id)
    scope = tenant_filter(claims, DispatchLog)
    if scope is not None:
        q = q.where(scope)
    rows = (await session.execute(q.order_by(DispatchLog.attempted_at.desc()))).scalars().all()
    return [
        {
            "channel": r.channel,
            "status": r.status,
            "error": r.error,
            "attempted_at": r.attempted_at,
        }
        for r in rows
    ]


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_write")),
):
    from datetime import datetime, timezone
    q = select(AlertModel).where(AlertModel.id == alert_id)
    scope = tenant_filter(claims, AlertModel)
    if scope is not None:
        q = q.where(scope)
    row = (await session.execute(q)).scalar_one_or_none()
    if row is None:
        return {"id": alert_id, "status": "not_found"}
    previous = _status(row.status)
    row.status = AlertStatus.ACKNOWLEDGED
    row.acknowledged_by = claims.email or claims.sub
    row.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    _audit_alert_action(
        session,
        request,
        claims,
        "alert.acknowledge",
        alert_id,
        {"previous_status": previous, "severity": _severity(row.severity)},
    )
    return {"id": alert_id, "status": "acknowledged"}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_write")),
):
    from datetime import datetime, timezone
    q = select(AlertModel).where(AlertModel.id == alert_id)
    scope = tenant_filter(claims, AlertModel)
    if scope is not None:
        q = q.where(scope)
    row = (await session.execute(q)).scalar_one_or_none()
    if row is None:
        return {"id": alert_id, "status": "not_found"}
    previous = _status(row.status)
    row.status = AlertStatus.RESOLVED
    row.resolved_at = datetime.now(timezone.utc)
    await session.commit()
    _audit_alert_action(
        session,
        request,
        claims,
        "alert.resolve",
        alert_id,
        {"previous_status": previous, "severity": _severity(row.severity)},
    )
    return {"id": alert_id, "status": "resolved"}
