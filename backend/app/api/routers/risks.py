import logging
from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.risk import RiskScore, RiskTrend
from app.db import get_session
from app.models.risk_score import RiskBucket
from app.models.risk_score import RiskScore as RiskScoreModel

logger = logging.getLogger(__name__)

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
    scope_level_key: str | None = Query(None, max_length=64, pattern=r"^[a-z0-9_-]+$", description="Filter by a configured tenant hierarchy tier"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    try:
        filters = []
        scope = tenant_filter(claims, RiskScoreModel)
        if scope is not None:
            filters.append(scope)
        if scope_level_key:
            filters.append(RiskScoreModel.tenant_scope_level_key == scope_level_key)
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
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("Database error in get_risks: %s", e)
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.exception("Unexpected error in get_risks: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/risks/{app_name}/trend", response_model=RiskTrend)
async def get_risk_trend(
    app_name: str,
    days: int = Query(30, ge=7, le=90),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("risks")),
):
    try:
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
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("Database error in get_risk_trend: %s", e)
        raise HTTPException(status_code=500, detail="Database query failed")
    except Exception as e:
        logger.exception("Unexpected error in get_risk_trend: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
