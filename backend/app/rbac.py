# RBAC helper utilities for the SITA platform
"""Utility functions to evaluate RBAC permissions for users.
The data‑plane exposes *security cockpits* that are scoped to a tenant
under a specific MSSP.  Permissions are stored in the ``Permission`` model
and referenced by ``Role.permissions`` (a list of permission IDs).
A role also carries an ``owner_type``/``owner_id`` that defines its scope:

- ``platform`` – global permissions for the whole system.
- ``mssp``      – permissions limited to a particular MSSP (owner_id = mssp.id).
- ``tenant``    – permissions limited to a specific tenant (owner_id = tenant.id).
- ``branch``    – permissions limited to a branch (not used for cockpit access).

The ``user_has_cockpit_access`` function aggregates a user's roles and
determines whether the user can *view* the cockpit for a given tenant
under an MSSP.
"""

import uuid
from typing import List

from fastapi import HTTPException, status

from app.db import SessionFactory
from app.models.user import User
from app.models.admin import Role, Permission
from app.models.admin import Tenant, MSSP

# ---------------------------------------------------------------------
# Helper to load a user and its role objects
# ---------------------------------------------------------------------

async def _load_user_roles(session, user_id: str) -> List[Role]:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # ``user.roles`` stores a list of role IDs (JSON column)
    role_ids: List[str] = user.roles or []
    if not role_ids:
        return []
    stmt = Role.__table__.select().where(Role.id.in_(role_ids))
    result = await session.execute(stmt)
    return result.scalars().all()

# ---------------------------------------------------------------------
# Core permission check for cockpit access
# ---------------------------------------------------------------------

async def user_has_cockpit_access(
    user_id: str,
    mssp_id: str,
    tenant_id: str,
) -> bool:
    """Return ``True`` if the user may view the security cockpit for the
    supplied ``tenant_id`` under the given ``mssp_id``.

    The check follows the hierarchy:
    1. Platform‑wide permission (owner_type='platform').
    2. MSSP‑level permission where ``owner_type='mssp'`` and ``owner_id``
       matches ``mssp_id``.
    3. Tenant‑level permission where ``owner_type='tenant'`` and
       ``owner_id`` matches ``tenant_id``.

    The required permission has:
        resource = 'cockpit'
        action   = 'view'
        scope    = one of 'platform', 'mssp', 'tenant'
    """
    async with SessionFactory() as session:
        # Verify MSSP and Tenant relationship for safety
        mssp = await session.get(MSSP, mssp_id)
        if not mssp:
            raise HTTPException(status_code=404, detail="MSSP not found")
        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if tenant.mssp_id != mssp_id:
            # Tenant does not belong to the supplied MSSP – deny
            return False

        roles = await _load_user_roles(session, user_id)
        if not roles:
            return False

        # Gather permission IDs from all roles
        permission_ids: List[str] = []
        for role in roles:
            permission_ids.extend(role.permissions or [])
        if not permission_ids:
            return False

        # Load Permission objects that match the collected IDs
        stmt = Permission.__table__.select().where(Permission.id.in_(permission_ids))
        perms_result = await session.execute(stmt)
        perms: List[Permission] = perms_result.scalars().all()

        # Evaluate the hierarchy rules
        for perm in perms:
            if perm.resource != "cockpit" or perm.action != "view":
                continue
            if perm.scope == "platform":
                return True
            if perm.scope == "mssp" and perm.owner_id == mssp_id:
                return True
            if perm.scope == "tenant" and perm.owner_id == tenant_id:
                return True
        return False

# ---------------------------------------------------------------------
# Convenience wrapper for FastAPI dependencies (optional) – can be used
# as ``Depends`` in route definitions.
# ---------------------------------------------------------------------

async def require_cockpit_access(user_id: str, mssp_id: str, tenant_id: str):
    allowed = await user_has_cockpit_access(user_id, mssp_id, tenant_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view cockpit",
        )
    return True
