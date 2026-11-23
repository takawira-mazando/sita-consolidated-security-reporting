from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.sql import and_, expression

from app.config import settings
from app.tenant import GRANTABLE_ROLES, PLATFORM_SCOPE_ROLES, SCOPED_COCKPIT_ROLES, tier_for_role

security = HTTPBearer(auto_error=False)

ROLES_HIERARCHY = {
    "exec": {"risks", "compliance", "alerts", "alerts_read", "alerts_write", "findings", "dashboard"},
    "soc": {"findings", "alerts_read", "alerts_write", "dashboard"},
    "appsec": {"risks", "findings", "dashboard"},
    "dbsec": {"risks", "findings", "alerts_read", "dashboard"},
    "compliance": {"compliance", "dashboard"},
    "sre": {"sre", "alerts_read", "dashboard"},
    "ai": {"dashboard"},
    "transversal-admin": {"admin_read", "admin_write", "dashboard"},
    "tenant-admin": set(),
    "admin": {"*"},
    "operator": {"*"},
}


class JWTClaims(BaseModel):
    sub: str = ""
    email: str = ""
    roles: list[str] = []
    department_id: str | None = None
    department_ids: list[str] = []
    branch_ids: list[str] = []
    province_ids: list[str] = []
    tenant_workspace_ids: list[str] = []
    tenant_scope_unit_ids: list[str] = []
    tenant_can_manage_members: bool = False
    tenant_workspace_access: list[dict[str, Any]] = []
    active_tenant_workspace_id: str | None = None
    active_tenant_scope_level_keys: list[str] = []
    exp: int = 0


@lru_cache
def get_jwks():
    return {}


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> JWTClaims:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        if settings.auth0_domain:
            payload = jwt.decode(
                credentials.credentials,
                settings.auth0_domain,
                algorithms=settings.auth0_algorithms,
                audience=settings.auth0_audience,
                options={"verify_aud": bool(settings.auth0_audience)},
            )
        else:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
                options={"verify_signature": True},
            )
        claims = JWTClaims(**payload)
        active_workspace_id = request.headers.get("X-Tenant-Workspace-ID")
        if active_workspace_id:
            if active_workspace_id not in claims.tenant_workspace_ids:
                raise HTTPException(
                    status_code=403,
                    detail="Tenant workspace is outside your assigned access",
                )
            claims = claims.model_copy(
                update={"active_tenant_workspace_id": active_workspace_id}
            )
        return claims
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_roles(*required: str):
    async def checker(claims: JWTClaims = Depends(verify_token)):
        user_roles = set(claims.roles)
        allowed = any(
            user_role in ("admin", "operator")
            or "*" in ROLES_HIERARCHY.get(user_role, set())
            or permission in ROLES_HIERARCHY.get(user_role, set())
            for user_role in user_roles
            for permission in required
        )
        active_scope_levels: set[str] = set()
        if claims.active_tenant_workspace_id:
            workspace_access = next(
                (
                    item
                    for item in claims.tenant_workspace_access
                    if item.get("workspace_id") == claims.active_tenant_workspace_id
                ),
                None,
            )
            cockpit_scopes = (
                workspace_access.get("cockpit_scopes", {})
                if workspace_access
                else {}
            )
            for cockpit_id, scope_levels in cockpit_scopes.items():
                permissions = ROLES_HIERARCHY.get(cockpit_id, set())
                if any(permission in permissions for permission in required):
                    allowed = True
                    active_scope_levels.update(scope_levels)
        if not allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return claims.model_copy(
            update={"active_tenant_scope_level_keys": sorted(active_scope_levels)}
        )
    return checker


def is_global_scope(claims: JWTClaims) -> bool:
    """Whether a role grants global access outside an active tenant workspace."""
    return bool(set(claims.roles) & PLATFORM_SCOPE_ROLES)


def is_scoped_role(claims: JWTClaims) -> bool:
    return bool(set(claims.roles) & SCOPED_COCKPIT_ROLES)


def grantable_roles(claims: JWTClaims) -> set[str]:
    return set().union(*(GRANTABLE_ROLES.get(role, set()) for role in claims.roles))


def _caller_scope_units(claims: JWTClaims) -> set[str]:
    return set(claims.tenant_scope_unit_ids or [])


def scope_covers(
    claims: JWTClaims,
    organization_unit_ids: list[str],
    legacy_unit_ids: list[str] | None = None,
    unused_scope_ids: list[str] | None = None,
) -> bool:
    """Check that requested unit identifiers fall within the caller's grant."""
    target_units = set(organization_unit_ids or [])
    target_units.update(legacy_unit_ids or [])
    target_units.update(unused_scope_ids or [])
    if not target_units:
        return is_global_scope(claims) or (
            claims.active_tenant_workspace_id is not None
            and "root" in claims.active_tenant_scope_level_keys
        )
    if is_global_scope(claims) and not claims.active_tenant_workspace_id:
        return True
    return target_units <= _caller_scope_units(claims)


def check_tenancy_access(
    claims: JWTClaims,
    organization_unit_id: str | None = None,
    legacy_unit_id: str | None = None,
) -> None:
    requested = {unit for unit in (organization_unit_id, legacy_unit_id) if unit}
    if not requested:
        return
    if not scope_covers(claims, list(requested)):
        raise HTTPException(
            status_code=403,
            detail="Requested organization scope is outside your assigned tenant access",
        )


def person_within_scope(claims: JWTClaims, person) -> bool:
    """Do not infer tenant scope from directory department or office labels."""
    if is_global_scope(claims) and not claims.active_tenant_workspace_id:
        return True
    person_scope = getattr(person, "tenant_scope_unit_id", None)
    if not person_scope:
        return False
    return scope_covers(claims, [str(person_scope)])


def can_manage(
    claims: JWTClaims,
    roles: list[str],
    organization_unit_ids: list[str],
    legacy_unit_ids: list[str] | None = None,
    unused_scope_ids: list[str] | None = None,
) -> bool:
    """Allow only permitted downward role grants within the caller's scope."""
    if not set(roles) <= grantable_roles(claims):
        return False
    caller_tier = max((tier_for_role(role) for role in claims.roles), default=0)
    for role in roles:
        role_tier = tier_for_role(role)
        if role_tier and role_tier >= caller_tier:
            if role != "operator" or "operator" not in claims.roles:
                return False
    return scope_covers(
        claims,
        organization_unit_ids,
        legacy_unit_ids,
        unused_scope_ids,
    )


def tenant_filter(claims: JWTClaims, model):
    """Build a fail-closed filter using the active workspace and configured tiers."""
    active_workspace_id = claims.active_tenant_workspace_id
    if active_workspace_id:
        if not hasattr(model, "tenant_workspace_id") or not hasattr(
            model, "tenant_scope_level_key"
        ):
            return expression.false()
        levels = claims.active_tenant_scope_level_keys or []
        if not levels:
            return expression.false()
        return and_(
            model.tenant_workspace_id == active_workspace_id,
            model.tenant_scope_level_key.in_(levels),
        )

    if claims.tenant_workspace_ids and hasattr(model, "tenant_workspace_id"):
        return model.tenant_workspace_id.is_(None)
    if is_global_scope(claims):
        return None
    if (
        is_scoped_role(claims)
        or claims.tenant_scope_unit_ids
        or claims.department_ids
        or claims.branch_ids
        or claims.province_ids
    ):
        return expression.false()
    return None
