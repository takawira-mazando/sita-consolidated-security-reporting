"""Metrics endpoints serving the derived dashboard panels.

Provides the data behind the AppSec (WAF / API exposure / fix-rate), SOC
(MTTD / MTTR / backlog age), SRE (system health / agent inventory), DBSec
(database inventory / coverage) and Compliance (trend / regulatory calendar)
panels. Data is produced by app/entrypoints/seed_simulated.py (or live
connectors) and stored via app/lake/writer.py.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.models.alert import Alert, AlertStatus
from app.models.compliance import ComplianceGap, ComplianceSnapshot
from app.models.finding import Finding
from app.models.metrics import (
    Agent,
    ApiEndpoint,
    DatabaseInventory,
    SloMetric,
    SystemMetric,
    WafBlock,
)

router = APIRouter(tags=["metrics"])


def _dt(value):
    if value is None:
        return None
    return value.isoformat()


# ------------------------------------------------------------------ AppSec
@router.get("/metrics/appsec/waf")
async def get_waf_blocks(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    window = datetime.now(timezone.utc) - timedelta(days=30)
    total = (
        await session.execute(
            select(func.count()).select_from(WafBlock).where(WafBlock.block_time >= window)
        )
    ).scalar_one()

    by_type_rows = (
        await session.execute(
            select(WafBlock.attack_type, func.count())
            .where(WafBlock.block_time >= window)
            .group_by(WafBlock.attack_type)
            .order_by(func.count().desc())
        )
    ).all()
    by_type = [{"type": t or "unknown", "count": c} for t, c in by_type_rows]

    latest_rows = (
        await session.execute(
            select(WafBlock)
            .where(WafBlock.block_time >= window)
            .order_by(WafBlock.block_time.desc())
            .limit(50)
        )
    ).scalars().all()
    items = [
        {
            "id": r.id,
            "app_name": r.app_name,
            "attack_type": r.attack_type,
            "request_uri": r.request_uri,
            "action": r.action,
            "src_ip": r.src_ip,
            "block_time": _dt(r.block_time),
        }
        for r in latest_rows
    ]
    return {"total": total, "window_days": 30, "by_type": by_type, "items": items}


@router.get("/metrics/appsec/api-exposure")
async def get_api_exposure(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    rows = (await session.execute(select(ApiEndpoint).order_by(ApiEndpoint.exposure_score.desc()))).scalars().all()
    items = [
        {
            "id": r.id,
            "app_name": r.app_name,
            "endpoint": r.endpoint,
            "method": r.method,
            "is_shadow": bool(r.is_shadow),
            "exposure_score": float(r.exposure_score),
            "discovered_at": _dt(r.discovered_at),
            "last_seen": _dt(r.last_seen),
        }
        for r in rows
    ]
    return {
        "total": len(items),
        "shadow_total": sum(1 for i in items if i["is_shadow"]),
        "items": items,
    }


@router.get("/metrics/appsec/fix-rate")
async def get_fix_rate(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    window = datetime.now(timezone.utc) - timedelta(days=30)
    total = (
        await session.execute(
            select(func.count()).select_from(Finding).where(Finding.last_seen >= window)
        )
    ).scalar_one()
    fixed = (
        await session.execute(
            select(func.count()).select_from(Finding).where(
                Finding.last_seen >= window,
                Finding.status.in_(["fixed", "closed", "resolved", "remediated"]),
            )
        )
    ).scalar_one()
    return {
        "window_days": 30,
        "total": total,
        "fixed": fixed,
        "fix_rate": round((fixed / total) * 100, 1) if total else 0.0,
    }


# --------------------------------------------------------------------- SOC
@router.get("/metrics/soc/slo")
async def get_slo_metrics(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("alerts_read")),
):
    rows = (await session.execute(select(SloMetric).order_by(SloMetric.week_start))).scalars().all()
    mttd = [
        {"week": r.week_start.isoformat(), "value_hours": r.value_hours}
        for r in rows if r.metric == "mttd"
    ]
    mttr = [
        {"week": r.week_start.isoformat(), "value_hours": r.value_hours}
        for r in rows if r.metric == "mttr"
    ]

    open_statuses = [AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING]
    backlog_rows = (
        await session.execute(
            select(Alert.first_triggered).where(Alert.status.in_(open_statuses))
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    buckets = {"0-6h": 0, "6-24h": 0, "1-3d": 0, "3d+": 0}
    oldest_hours = 0
    for first in backlog_rows:
        if first is None:
            continue
        age = (now - first).total_seconds() / 3600
        if age < 6:
            buckets["0-6h"] += 1
        elif age < 24:
            buckets["6-24h"] += 1
        elif age < 72:
            buckets["1-3d"] += 1
        else:
            buckets["3d+"] += 1
        oldest_hours = max(oldest_hours, int(age))
    return {
        "mttd": mttd,
        "mttr": mttr,
        "backlog": {
            "total": len(backlog_rows),
            "oldest_hours": oldest_hours,
            "buckets": [{"bucket": k, "count": v} for k, v in buckets.items()],
        },
    }


# --------------------------------------------------------------------- SRE
@router.get("/metrics/sre/system")
async def get_system_metrics(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("dashboard")),
):
    rows = (await session.execute(select(SystemMetric).order_by(SystemMetric.recorded_at.desc()))).scalars().all()
    items = [
        {
            "metric": r.metric,
            "value": float(r.value),
            "unit": r.unit,
            "recorded_at": _dt(r.recorded_at),
        }
        for r in rows
    ]
    uptime_row = next((i for i in items if i["metric"] == "uptime"), None)
    return {
        "items": items,
        "uptime": uptime_row["value"] if uptime_row else None,
    }


@router.get("/metrics/sre/agents")
async def get_agents(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("dashboard")),
):
    rows = (await session.execute(select(Agent).order_by(Agent.name))).scalars().all()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "role": r.role,
            "version": r.version,
            "status": r.status,
            "host": r.host,
            "last_seen": _dt(r.last_seen),
        }
        for r in rows
    ]
    by_role: dict[str, int] = {}
    versions: dict[str, int] = {}
    for r in rows:
        by_role[r.role] = by_role.get(r.role, 0) + 1
        versions[r.version] = versions.get(r.version, 0) + 1
    return {
        "total": len(rows),
        "online": sum(1 for r in rows if r.status == "online"),
        "degraded": sum(1 for r in rows if r.status == "degraded"),
        "items": items,
        "by_role": [{"role": k, "count": v} for k, v in sorted(by_role.items())],
        "versions": [{"version": k, "count": v} for k, v in sorted(versions.items(), key=lambda x: -x[1])],
    }


# ------------------------------------------------------------------- DBSec
@router.get("/metrics/dbsec/inventory")
async def get_database_inventory(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    rows = (await session.execute(select(DatabaseInventory).order_by(DatabaseInventory.name))).scalars().all()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "engine": r.engine,
            "monitored": bool(r.monitored),
            "agent_version": r.agent_version,
            "last_heartbeat": _dt(r.last_heartbeat),
        }
        for r in rows
    ]
    monitored = sum(1 for i in items if i["monitored"])
    total = len(items)
    return {
        "total": total,
        "monitored": monitored,
        "unmonitored": total - monitored,
        "coverage_pct": round((monitored / total) * 100, 1) if total else 0.0,
        "items": items,
    }


# ---------------------------------------------------------------- Compliance
@router.get("/metrics/compliance/trend")
async def get_compliance_trend(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    rows = (
        await session.execute(
            select(ComplianceSnapshot).order_by(ComplianceSnapshot.snapshot_date)
        )
    ).scalars().all()
    items = [
        {
            "framework": r.framework,
            "snapshot_date": r.snapshot_date.isoformat(),
            "overall_score": float(r.overall_score),
            "total_controls": r.total_controls,
            "passed_controls": r.passed_controls,
        }
        for r in rows
    ]
    return {"items": items}


@router.get("/metrics/compliance/calendar")
async def get_regulatory_calendar(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("compliance")),
):
    rows = (
        await session.execute(
            select(ComplianceGap)
            .where(ComplianceGap.status.notin_(["closed", "remediated"]))
            .order_by(ComplianceGap.due_date.asc())
            .limit(12)
        )
    ).scalars().all()
    items = [
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
    ]
    return {"items": items}
