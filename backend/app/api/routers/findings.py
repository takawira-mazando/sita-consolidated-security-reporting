from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.api.schemas.common import PaginatedResponse
from app.api.schemas.finding import Finding
from app.db import get_session
from app.models.finding import Finding as FindingModel
from app.models.finding import Severity
from app.processing import owasp

router = APIRouter(tags=["findings"])


def _project(row) -> Finding:
    return Finding(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        app_name=row.app_name,
        severity=row.severity.value if isinstance(row.severity, Severity) else row.severity,
        title=row.title,
        description=row.description,
        category=row.category,
        owasp_id=row.owasp_id,
        owasp_name=(owasp.categories().get(row.owasp_id).name if row.owasp_id in owasp.categories() else None),
        cwe_id=row.cwe_id,
        owasp_status=row.owasp_status,
        taxonomy_version=row.taxonomy_version,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
        status=row.status,
        version=row.version,
    )


@router.get("/findings", response_model=PaginatedResponse)
async def get_findings(
    app: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    owasp_id: str | None = Query(None, description="OWASP Top 10 category id, e.g. A03"),
    cwe_id: str | None = Query(None, description="Precise CWE identifier, e.g. CWE-89"),
    source: str | None = Query(None),
    status: str | None = Query(None),
    since: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    try:
        filters = []
        scope = tenant_filter(claims, FindingModel)
        if scope is not None:
            filters.append(scope)
        if app:
            filters.append(FindingModel.app_name == app)
        if severity:
            filters.append(FindingModel.severity == severity)
        if category:
            filters.append(FindingModel.category == category)
        if owasp_id:
            # Accept a bare id, a year-stamped id, or a slug, so a dashboard
            # link and a hand-typed filter land on the same rows.
            filters.append(FindingModel.owasp_id == owasp_id.upper().split(":")[0].split("-")[0])
        if cwe_id:
            filters.append(FindingModel.cwe_id == cwe_id.upper())
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

        return {
            "items": [_project(r) for r in rows],
            "total": total,
            "page": page,
            "size": size,
            "pages": ceil(total / size) if size else 0,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/findings/{finding_id}", response_model=Finding)
async def get_finding(
    finding_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("findings")),
):
    try:
        scope = tenant_filter(claims, FindingModel)
        base = select(FindingModel)
        if scope is not None:
            base = base.where(scope)
        row = (
            await session.execute(base.where(FindingModel.id == finding_id))
        ).scalar_one_or_none()
        if row is None:
            row = (
                await session.execute(base.where(FindingModel.external_id == finding_id))
            ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Finding not found")
        return _project(row)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
