from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.models.alert import Alert, AlertStatus
from app.models.risk_score import RiskScore, RiskBucket

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("dashboard")),
):
    def _bucket(b):
        return b.value if hasattr(b, "value") else b

    rows = (await session.execute(select(RiskScore))).scalars().all()
    buckets = [_bucket(r.bucket) for r in rows]
    critical = sum(1 for b in buckets if b == RiskBucket.CRITICAL.value)
    monitored = sum(1 for b in buckets if b == RiskBucket.MONITORED.value)
    safe = sum(1 for b in buckets if b == RiskBucket.SAFE.value)
    avg = round(sum(float(r.fused_score) for r in rows) / len(rows), 1) if rows else 0.0

    active = (
        await session.execute(
            select(func.count()).select_from(Alert).where(
                Alert.status.in_([AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING])
            )
        )
    ).scalar_one()

    unread = (
        await session.execute(
            select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.NEW)
        )
    ).scalar_one()

    return {
        "current_risk_score": avg,
        "monitored_apps": monitored,
        "critical_apps": critical,
        "monitored_apps_count": monitored,
        "safe_apps": safe,
        "active_alerts": active,
        "unread_alerts": unread,
    }
