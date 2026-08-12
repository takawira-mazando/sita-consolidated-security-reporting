from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.db import get_session
from app.models.alert import Alert, AlertStatus
from app.models.risk_score import RiskBucket, RiskScore

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("dashboard")),
):
    def _bucket(b):
        return b.value if hasattr(b, "value") else b

    risk_scope = tenant_filter(claims, RiskScore)
    alert_scope = tenant_filter(claims, Alert)

    risk_q = select(RiskScore)
    if risk_scope is not None:
        risk_q = risk_q.where(risk_scope)
    rows = (await session.execute(risk_q)).scalars().all()
    buckets = [_bucket(r.bucket) for r in rows]
    critical = sum(1 for b in buckets if b == RiskBucket.CRITICAL.value)
    monitored = sum(1 for b in buckets if b == RiskBucket.MONITORED.value)
    safe = sum(1 for b in buckets if b == RiskBucket.SAFE.value)
    avg = round(sum(float(r.fused_score) for r in rows) / len(rows), 1) if rows else 0.0

    active_q = select(func.count()).select_from(Alert).where(
        Alert.status.in_([AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING])
    )
    if alert_scope is not None:
        active_q = active_q.where(alert_scope)
    active = (await session.execute(active_q)).scalar_one()

    unread_q = select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.NEW)
    if alert_scope is not None:
        unread_q = unread_q.where(alert_scope)
    unread = (await session.execute(unread_q)).scalar_one()

    return {
        "current_risk_score": avg,
        "monitored_apps": monitored,
        "critical_apps": critical,
        "monitored_apps_count": monitored,
        "safe_apps": safe,
        "active_alerts": active,
        "unread_alerts": unread,
    }
