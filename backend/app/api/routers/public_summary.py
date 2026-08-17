"""Public, aggregate-only estate summary powering the pre-login homepage.

Exposes high-level counts (open findings by severity, asset totals, connector
health, risk distribution) WITHOUT any per-resource detail, app owner, or PII
so it is safe to render on the public marketing page. Individual records still
require an authenticated, tenant-scoped call.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.connector_status import ConnectorHealth
from app.models.finding import Finding
from app.models.metrics import (
    Agent,
    ApiEndpoint,
    DatabaseInventory,
    WafBlock,
)
from app.models.risk_score import RiskScore
from app.tenant import (
    BRANCHES,
    DEPARTMENTS,
    PROVINCES,
    PROVINCIAL_DEPARTMENTS,
)

router = APIRouter(tags=["public"])


def _bucket(b):
    return b.value if hasattr(b, "value") else b


def _iso(value):
    if value is None:
        return None
    return value.isoformat()


@router.get("/public/summary")
async def public_summary(session: AsyncSession = Depends(get_session)):
    now = datetime.now(timezone.utc)

    total_findings = (
        await session.execute(select(func.count()).select_from(Finding))
    ).scalar_one() or 0
    open_findings = (
        await session.execute(
            select(func.count()).select_from(Finding).where(Finding.status == "open")
        )
    ).scalar_one() or 0
    severity_rows = (
        await session.execute(
            select(Finding.severity, func.count())
            .group_by(Finding.severity)
            .order_by(func.count().desc())
        )
    ).all()
    by_severity = {sev or "unknown": count for sev, count in severity_rows}

    app_count = float(
        (
            await session.execute(
                select(func.count(func.distinct(RiskScore.app_name)))
            )
        ).scalar_one()
        or 0
    ) or 0
    db_rows = (await session.execute(select(DatabaseInventory))).scalars().all()
    db_total = len(db_rows)
    db_monitored = sum(1 for d in db_rows if d.monitored)
    endpoints = (
        await session.execute(select(func.count()).select_from(ApiEndpoint))
    ).scalar_one() or 0
    agents = (await session.execute(select(func.count()).select_from(Agent))).scalar_one() or 0
    waf_blocks = (
        await session.execute(select(func.count()).select_from(WafBlock))
    ).scalar_one() or 0

    latest_ingest = (
        await session.execute(select(func.max(Finding.ingested_at)))
    ).scalar_one()
    latest_poll = (
        await session.execute(select(func.max(ConnectorHealth.last_success_at)))
    ).scalar_one()
    latest_ingest = latest_ingest or latest_poll

    latest_date = (
        await session.execute(select(func.max(RiskScore.score_date)))
    ).scalar_one()
    risk_distribution: dict[str, int] = {}
    latest_bucket_rows = []
    if latest_date is not None:
        latest_bucket_rows = (
            await session.execute(
                select(RiskScore.bucket, func.count())
                .where(RiskScore.score_date == latest_date)
                .group_by(RiskScore.bucket)
            )
        ).all()
    risk_distribution = {_bucket(b) or "unknown": count for b, count in latest_bucket_rows}

    trend_start = (now - timedelta(days=13)).date()
    trend_rows = (
        await session.execute(
            select(RiskScore.score_date, func.avg(RiskScore.fused_score))
            .where(RiskScore.score_date >= trend_start)
            .group_by(RiskScore.score_date)
            .order_by(RiskScore.score_date)
        )
    ).all()
    trend = [
        {"date": d.isoformat(), "avg_score": round(float(avg), 1)}
        for d, avg in trend_rows
    ]

    latest_sub = (
        select(RiskScore.app_name, func.max(RiskScore.score_date).label("md"))
        .group_by(RiskScore.app_name)
        .subquery()
    )
    top_rows = (
        await session.execute(
            select(RiskScore)
            .join(
                latest_sub,
                (RiskScore.app_name == latest_sub.c.app_name)
                & (RiskScore.score_date == latest_sub.c.md),
            )
            .order_by(RiskScore.fused_score.desc())
            .limit(10)
        )
    ).scalars().all()
    top_risky_apps = [
        {
            "app_name": r.app_name,
            "score": round(float(r.fused_score), 1),
            "bucket": _bucket(r.bucket),
        }
        for r in top_rows
    ]

    connector_rows = (
        await session.execute(
            select(ConnectorHealth.status, func.count()).group_by(ConnectorHealth.status)
        )
    ).all()
    connector_by_status = {status or "unknown": count for status, count in connector_rows}
    connector_total = sum(connector_by_status.values())

    return {
        "generated_at": _iso(now),
        "findings": {
            "total": total_findings,
            "open": open_findings,
            "by_severity": by_severity,
        },
        "assets": {
            "apps": int(app_count),
            "databases": db_total,
            "monitored_databases": db_monitored,
            "api_endpoints": endpoints,
            "agents": agents,
            "waf_blocks": waf_blocks,
        },
        "latest_ingest": _iso(latest_ingest),
        "risk": {
            "distribution": risk_distribution,
            "latest_score_date": latest_date.isoformat() if latest_date else None,
            "trend": trend,
        },
        "top_risky_apps": top_risky_apps,
        "connectors": {
            "total": connector_total,
            **{k: connector_by_status.get(k, 0) for k in ("healthy", "degraded", "down")},
        },
        "tenancy": {
            "departments": len(DEPARTMENTS),
            "branches": len(BRANCHES),
            "provinces": len(PROVINCES),
            "provincial_departments": len(PROVINCIAL_DEPARTMENTS),
        },
    }