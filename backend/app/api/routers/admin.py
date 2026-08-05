from math import ceil

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.ingestion.dlq import DLQManager
from app.models.connector_status import ConnectorHealth
from app.models.dlq import RejectedRecord

router = APIRouter(tags=["admin"])


@router.get("/connectors")
async def get_connectors(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    rows = (await session.execute(
        select(ConnectorHealth).order_by(ConnectorHealth.name)
    )).scalars().all()
    return {"items": [
        {
            "name": r.name,
            "source": r.source,
            "status": r.status,
            "last_poll_at": r.last_poll_at,
            "last_success_at": r.last_success_at,
            "latency_ms": r.latency_ms,
            "events_per_hour": r.events_per_hour,
            "error_count": r.error_count,
            "circuit_state": r.circuit_state,
        }
        for r in rows
    ]}


@router.get("/dead-letter")
async def get_dead_letter(
    source: str | None = None,
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    filters = []
    if source:
        filters.append(RejectedRecord.source == source)
    q = select(RejectedRecord).where(*filters).order_by(RejectedRecord.rejected_at.desc())
    q = q.offset((page - 1) * size).limit(size)
    rows = (await session.execute(q)).scalars().all()
    total = (await session.execute(
        select(func.count()).select_from(RejectedRecord).where(*filters)
    )).scalar_one()
    return {
        "items": [
            {
                "id": r.id,
                "batch_id": r.batch_id,
                "source": r.source,
                "rejection_reason": r.rejection_reason,
                "rejection_code": r.rejection_code,
                "rejected_at": r.rejected_at,
                "reprocessed": r.reprocessed,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


@router.post("/connectors/{name}/reset")
async def reset_connector(
    name: str,
    claims = Depends(require_roles("admin_write")),
):
    return {"status": "ok", "connector": name, "circuit_state": "closed"}


@router.post("/dead-letter/reprocess/{record_id}")
async def reprocess_dlq(
    record_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    mgr = DLQManager(session)
    raw = await mgr.reprocess(record_id)
    return {"status": "queued", "record_id": record_id, "payload": raw}
