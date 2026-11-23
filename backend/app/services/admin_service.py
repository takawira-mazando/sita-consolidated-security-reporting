# Admin service layer for multi‑tenant administration
"""Provides async CRUD helpers used by the admin FastAPI router.
Only a subset is implemented now – enough for creating MSSPs, Tenants,
Roles and assigning roles to users. Each function opens a new session
via ``SessionFactory`` and commits on success. Errors raise ``HTTPException``
with a 403/404 where appropriate.
"""

import uuid
from typing import List, Optional

from fastapi import HTTPException, status

from app.db import SessionFactory
from app.models.admin import MSSP, Tenant, Role, Permission
from app.models.user import User

# -------------------- Helper utilities --------------------

async def _get_mssp(session, mssp_id: str) -> MSSP:
    mssp = await session.get(MSSP, mssp_id)
    if not mssp:
        raise HTTPException(status_code=404, detail="MSSP not found")
    return mssp

async def _get_tenant(session, tenant_id: str) -> Tenant:
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# -------------------- MSSP CRUD --------------------

async def create_mssp(name: str, code: str, admin_user_id: Optional[str] = None) -> MSSP:
    async with SessionFactory() as session:
        mssp = MSSP(id=str(uuid.uuid4()), name=name, code=code, admin_user_id=admin_user_id)
        session.add(mssp)
        await session.commit()
        await session.refresh(mssp)
        return mssp

async def list_mssps() -> List[MSSP]:
    async with SessionFactory() as session:
        result = await session.execute(MSSP.__table__.select())
        return result.scalars().all()

# -------------------- Tenant CRUD --------------------

async def create_tenant(
    mssp_id: str,
    name: str,
    identifier: str,
    type_: Optional[str] = None,
    superuser_id: Optional[str] = None,
) -> Tenant:
    async with SessionFactory() as session:
        # ensure MSSP exists
        await _get_mssp(session, mssp_id)
        tenant = Tenant(
            id=str(uuid.uuid4()),
            mssp_id=mssp_id,
            name=name,
            identifier=identifier,
            type=type_,
            superuser_id=superuser_id,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return tenant

async def list_tenants(mssp_id: Optional[str] = None) -> List[Tenant]:
    async with SessionFactory() as session:
        stmt = Tenant.__table__.select()
        if mssp_id:
            stmt = stmt.where(Tenant.mssp_id == mssp_id)
        result = await session.execute(stmt)
        return result.scalars().all()

async def update_tenant(
    tenant_id: str,
    name: Optional[str] = None,
    identifier: Optional[str] = None,
    type_: Optional[str] = None,
    status: Optional[str] = None,
) -> Tenant:
    async with SessionFactory() as session:
        tenant = await _get_tenant(session, tenant_id)
        if name is not None:
            tenant.name = name
        if identifier is not None:
            tenant.identifier = identifier
        if type_ is not None:
            tenant.type = type_
        if status is not None:
            tenant.status = status
        await session.commit()
        await session.refresh(tenant)
        return tenant

# -------------------- Role & Permission --------------------

async def create_role(
    owner_type: str,
    owner_id: Optional[str],
    name: str,
    description: Optional[str] = None,
    permissions: Optional[List[str]] = None,
) -> Role:
    async with SessionFactory() as session:
        role = Role(
            id=str(uuid.uuid4()),
            owner_type=owner_type,
            owner_id=owner_id,
            name=name,
            description=description,
            permissions=permissions or [],
        )
        session.add(role)
        await session.commit()
        await session.refresh(role)
        return role

async def list_roles(owner_type: Optional[str] = None, owner_id: Optional[str] = None) -> List[Role]:
    async with SessionFactory() as session:
        stmt = Role.__table__.select()
        if owner_type:
            stmt = stmt.where(Role.owner_type == owner_type)
        if owner_id:
            stmt = stmt.where(Role.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalars().all()

async def assign_role_to_user(user_id: str, role_id: str) -> User:
    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # fetch role to ensure it exists
        role = await session.get(Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        # roles are stored as a list of role ids on the user model
        if role_id not in user.roles:
            user.roles.append(role_id)
            await session.commit()
            await session.refresh(user)
        return user

# -------------------- Simple audit helper --------------------

async def audit(event: str, details: dict):
    """Insert a row into ``audit.event_log`` – the table is created by the
    migration script. The schema is ``identity``; we only need ``event`` and
    ``payload`` columns (both JSONB). If the table is unavailable the function
    fails silently – audit is best‑effort.
    """
    try:
        async with SessionFactory() as session:
            stmt = (
                "INSERT INTO audit.event_log (event, payload) VALUES (:event, :payload)"
            )
            await session.execute(
                stmt,
                {"event": event, "payload": details},
            )
            await session.commit()
    except Exception:
        # do not interrupt main flow on audit failure
        pass
