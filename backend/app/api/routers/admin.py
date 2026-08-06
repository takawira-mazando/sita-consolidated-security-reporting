from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import ROLES_HIERARCHY, require_roles
from app.db import get_session
from app.ingestion.dlq import DLQManager
from app.models.connector_status import ConnectorHealth
from app.models.dlq import RejectedRecord
from app.models.user import User
from app.security import hash_password

router = APIRouter(tags=["admin"])

VALID_ROLES = set(ROLES_HIERARCHY.keys())


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["soc"])


class UserUpdate(BaseModel):
    display_name: str | None = None
    roles: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    roles: list[str]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _to_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "roles": list(user.roles or []),
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _validate_roles(roles: list[str]) -> None:
    if not roles:
        raise HTTPException(status_code=400, detail="At least one role is required")
    invalid = set(roles) - VALID_ROLES
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role(s): {sorted(invalid)}. Valid roles: {sorted(VALID_ROLES)}",
        )


async def _get_user_or_404(session: AsyncSession, user_id: str) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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


@router.get("/users", response_model=dict)
async def list_users(
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    size = min(max(size, 1), 200)
    page = max(page, 1)
    q = select(User).order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await session.execute(q)).scalars().all()
    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    return {
        "items": [_to_out(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    _validate_roles(body.roles)
    email = body.email.lower().strip()
    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        roles=body.roles,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return _to_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    user = await _get_user_or_404(session, user_id)
    if body.roles is not None:
        _validate_roles(body.roles)
        if user.id == claims.sub and not body.roles:
            raise HTTPException(status_code=400, detail="You cannot remove all roles from your own account")
    if body.is_active is False and user.id == claims.sub:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.roles is not None:
        user.roles = body.roles
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)

    await session.commit()
    await session.refresh(user)
    return _to_out(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    user = await _get_user_or_404(session, user_id)
    if user.id == claims.sub:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    await session.delete(user)
    await session.commit()
    return {"status": "deleted", "id": user_id}
