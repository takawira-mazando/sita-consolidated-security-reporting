"""Aggregated risk comparisons across tenant-configured hierarchy tiers."""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.db import get_session
from app.models.risk_score import RiskScore

router = APIRouter(tags=["benchmark"])


def build_tier_benchmark(records: list[dict]) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in records:
        key = record.get("scope_level_key")
        if key:
            grouped[str(key)].append(float(record["fused_score"]))

    return {
        "items": [
            {
                "scope_level_key": key,
                "average_risk": round(sum(scores) / len(scores), 1),
                "maximum_risk": round(max(scores), 1),
                "records": len(scores),
            }
            for key, scores in sorted(grouped.items())
        ]
    }


@router.get("/benchmark/tiers")
async def tier_benchmark(
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("dashboard")),
):
    query = select(
        RiskScore.tenant_scope_level_key,
        func.avg(RiskScore.fused_score).label("average_risk"),
        func.max(RiskScore.fused_score).label("maximum_risk"),
        func.count().label("records"),
    ).group_by(RiskScore.tenant_scope_level_key)
    scope = tenant_filter(claims, RiskScore)
    if scope is not None:
        query = query.where(scope)
    rows = (await session.execute(query)).all()
    return {
        "items": [
            {
                "scope_level_key": row.tenant_scope_level_key,
                "average_risk": round(float(row.average_risk), 1),
                "maximum_risk": round(float(row.maximum_risk), 1),
                "records": int(row.records),
            }
            for row in rows
            if row.tenant_scope_level_key
        ]
    }
