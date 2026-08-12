from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.risk import RiskScore, RiskTrend
from app.db import get_session
from app.models.risk_score import RiskBucket
from app.models.risk_score import RiskScore as RiskScoreModel
from app.tenant import CLUSTERS, MINISTRIES, MINISTRY_TO_CLUSTER

router = APIRouter(tags=["risks"])


def _bucket_value(bucket):
    if isinstance(bucket, RiskBucket):
        return bucket.value
    return bucket


@router.get("/risks", response_model=PaginatedResponse)
async def get_risks(
    app: str | None = Query(None),
    bucket: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    filters = []
    scope = tenant_filter(claims, RiskScoreModel)
    if scope is not None:
        filters.append(scope)
    if app:
        filters.append(RiskScoreModel.app_name == app)
    if bucket:
        filters.append(RiskScoreModel.bucket == bucket)
    if date_from:
        filters.append(RiskScoreModel.score_date >= date_from)
    if date_to:
        filters.append(RiskScoreModel.score_date <= date_to)

    q = select(RiskScoreModel).where(*filters).order_by(
        RiskScoreModel.score_date.desc(), RiskScoreModel.app_name
    )
    q = q.offset((page - 1) * size).limit(size)
    rows = (await session.execute(q)).scalars().all()

    items = [
        RiskScore(
            app_name=r.app_name,
            score_date=r.score_date,
            fused_score=float(r.fused_score),
            signal_appscan=float(r.signal_appscan) if r.signal_appscan is not None else None,
            signal_imperva=float(r.signal_imperva) if r.signal_imperva is not None else None,
            signal_api_exposure=float(r.signal_api_exposure) if r.signal_api_exposure is not None else None,
            signal_compliance_penalty=float(r.signal_compliance_penalty) if r.signal_compliance_penalty is not None else None,
            bucket=_bucket_value(r.bucket),
            computed_at=r.computed_at,
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


@router.get("/risks/by-cluster")
async def get_risks_by_cluster(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    """Rank Treasury clusters by average fused risk (most vulnerable first).

    cluster_id/ministry_id are nullable reporting metadata derived from each
    row's department_id; they never widen the tenant scope (tenant_filter still
    keys on department_id).
    """
    filters = []
    scope = tenant_filter(claims, RiskScoreModel)
    if scope is not None:
        filters.append(scope)
    if date_from:
        filters.append(RiskScoreModel.score_date >= date_from)
    if date_to:
        filters.append(RiskScoreModel.score_date <= date_to)

    rows = (
        await session.execute(
            select(
                RiskScoreModel.cluster_id,
                func.avg(RiskScoreModel.fused_score).label("avg_risk"),
                func.max(RiskScoreModel.fused_score).label("max_risk"),
                func.count(func.distinct(RiskScoreModel.department_id)).label("departments"),
                func.count().label("rows"),
            )
            .where(*filters)
            .group_by(RiskScoreModel.cluster_id)
            .order_by(func.avg(RiskScoreModel.fused_score).desc())
        )
    ).all()
    return {
        "items": [
            {
                "cluster_id": r.cluster_id,
                "cluster_name": CLUSTERS.get(r.cluster_id) if r.cluster_id else None,
                "avg_risk": round(float(r.avg_risk), 1) if r.avg_risk is not None else None,
                "max_risk": round(float(r.max_risk), 1) if r.max_risk is not None else None,
                "departments": int(r.departments),
                "rows": int(r.rows),
            }
            for r in rows
        ]
    }


@router.get("/risks/by-ministry")
async def get_risks_by_ministry(
    cluster_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    """Rank ministries by average fused risk (most vulnerable first)."""
    filters = []
    scope = tenant_filter(claims, RiskScoreModel)
    if scope is not None:
        filters.append(scope)
    if cluster_id:
        filters.append(RiskScoreModel.cluster_id == cluster_id)
    if date_from:
        filters.append(RiskScoreModel.score_date >= date_from)
    if date_to:
        filters.append(RiskScoreModel.score_date <= date_to)

    rows = (
        await session.execute(
            select(
                RiskScoreModel.ministry_id,
                func.avg(RiskScoreModel.fused_score).label("avg_risk"),
                func.max(RiskScoreModel.fused_score).label("max_risk"),
                func.count(func.distinct(RiskScoreModel.department_id)).label("departments"),
                func.count().label("rows"),
            )
            .where(*filters)
            .group_by(RiskScoreModel.ministry_id)
            .order_by(func.avg(RiskScoreModel.fused_score).desc())
        )
    ).all()
    return {
        "items": [
            {
                "ministry_id": r.ministry_id,
                "ministry_name": MINISTRIES.get(r.ministry_id) if r.ministry_id else None,
                "cluster_id": MINISTRY_TO_CLUSTER.get(r.ministry_id) if r.ministry_id else None,
                "avg_risk": round(float(r.avg_risk), 1) if r.avg_risk is not None else None,
                "max_risk": round(float(r.max_risk), 1) if r.max_risk is not None else None,
                "departments": int(r.departments),
                "rows": int(r.rows),
            }
            for r in rows
        ]
    }


@router.get("/risks/{app_name}/trend", response_model=RiskTrend)
async def get_risk_trend(
    app_name: str,
    days: int = Query(30, ge=7, le=90),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)
    q = select(RiskScoreModel).where(
        RiskScoreModel.app_name == app_name, RiskScoreModel.score_date >= cutoff
    )
    scope = tenant_filter(claims, RiskScoreModel)
    if scope is not None:
        q = q.where(scope)
    rows = (
        await session.execute(q.order_by(RiskScoreModel.score_date))
    ).scalars().all()
    trend = [
        RiskScore(
            app_name=r.app_name,
            score_date=r.score_date,
            fused_score=float(r.fused_score),
            signal_appscan=float(r.signal_appscan) if r.signal_appscan is not None else None,
            signal_imperva=float(r.signal_imperva) if r.signal_imperva is not None else None,
            signal_api_exposure=float(r.signal_api_exposure) if r.signal_api_exposure is not None else None,
            signal_compliance_penalty=float(r.signal_compliance_penalty) if r.signal_compliance_penalty is not None else None,
            bucket=_bucket_value(r.bucket),
            computed_at=r.computed_at,
        )
        for r in rows
    ]
    return {"app_name": app_name, "trend": trend}
