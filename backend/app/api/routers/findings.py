from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.finding import Finding
from app.db import get_session
from app.models.finding import Finding as FindingModel, Severity
from typing import Optional
from math import ceil

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=PaginatedResponse)
async def get_findings(
    app: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    filters = []
    if app:
        filters.append(FindingModel.app_name == app)
    if severity:
        filters.append(FindingModel.severity == severity)
    if category:
        filters.append(FindingModel.category == category)
    if source:
        filters.append(FindingModel.source == source)
    if status:
        filters.append(FindingModel.status == status)
    if since:
        filters.append(FindingModel.last_seen >= since)

    count_q = select(func.count()).select_from(FindingModel)
    if filters:
        count_q = count_q.where(*filters)
    total = (await session.execute(count_q)).scalar_one()

    q = select(FindingModel).where(*filters).order_by(FindingModel.last_seen.desc())
    q = q.offset((page - 1) * size).limit(size)
    rows = (await session.execute(q)).scalars().all()

    items = [
        Finding(
            id=r.id,
            source=r.source,
            external_id=r.external_id,
            app_name=r.app_name,
            severity=r.severity.value if isinstance(r.severity, Severity) else r.severity,
            title=r.title,
            description=r.description,
            category=r.category,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
            status=r.status,
            version=r.version,
        )
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


@router.get("/findings/{finding_id}", response_model=Finding)
async def get_finding(
    finding_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    row = (
        await session.execute(
            select(FindingModel).where(
                or_(FindingModel.id == finding_id, FindingModel.external_id == finding_id)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"id": finding_id, "source": "", "external_id": "", "app_name": "", "severity": "info", "title": "", "first_seen": "", "last_seen": "", "status": "", "version": 1}
    return Finding(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        app_name=row.app_name,
        severity=row.severity.value if isinstance(row.severity, Severity) else row.severity,
        title=row.title,
        description=row.description,
        category=row.category,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
        status=row.status,
        version=row.version,
    )
