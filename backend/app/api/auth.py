from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.sql import and_, expression

from app.config import settings
from app.tenant import (
    BRANCHES,
    DEPARTMENT_ROLES,
    GRANTABLE_ROLES,
    NATIONWIDE_ROLES,
    provincial_departments_for_province,
    tier_for_role,
)

security = HTTPBearer(auto_error=False)

ROLES_HIERARCHY = {
    "exec": {"risks", "compliance", "alerts", "alerts_read", "alerts_write", "findings", "dashboard"},
    "soc": {"findings", "alerts_read", "alerts_write", "dashboard"},
    "appsec": {"risks", "findings"},
    "dbsec": {"risks", "findings", "alerts_read"},
    "compliance": {"compliance"},
    "sre": {"admin_read", "admin_write", "alerts_read", "dashboard"},
    "transversal-admin": {"admin_read", "admin_write"},
    "dept-admin": {"admin_read", "admin_write"},
    "branch-admin": {"admin_read", "admin_write"},
    "province-soc-lead": {"findings", "alerts_read", "alerts_write", "dashboard"},
    "province-dept-admin": {"admin_read", "admin_write"},
    "local-appsec": {"risks", "findings"},
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
    exp: int = 0

@lru_cache
def get_jwks():
    return {}

async def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> JWTClaims:
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
        return JWTClaims(**payload)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_roles(*required: str):
    async def checker(claims: JWTClaims = Depends(verify_token)):
        user_roles = set(claims.roles)
        allowed = any(
            user_role == "admin" or perm in ROLES_HIERARCHY.get(user_role, set())
            for user_role in user_roles
            for perm in required
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return claims
    return checker


def is_nationwide(claims: JWTClaims) -> bool:
    """True when the caller's roles grant whole-estate capability."""
    return any(role in NATIONWIDE_ROLES for role in claims.roles)


def is_department_scoped(claims: JWTClaims) -> bool:
    """True when the caller holds a department-scoped role."""
    return any(role in DEPARTMENT_ROLES for role in claims.roles)


def grantable_roles(claims: JWTClaims) -> set[str] | None:
    """Roles the caller may assign to other users. None = anything (system admin).

    Delegation is a strict one-way cascade down the tenancy tree. The
    managed-service creator (`operator`) may create the SITA superuser
    (`admin`) and peer `operator` accounts only. The SITA superuser (`admin`)
    may create department superusers (`dept-admin`, `province-dept-admin`,
    `branch-admin`) and provision national-level dashboard access
    (`exec`, `compliance`, `sre`) estate-wide — never a peer `admin`.
    Beneath it, delegation follows the existing tree: `transversal-admin`
    grants the operational department roles plus the admin tiers below it and
    the specialist national roles; `dept-admin` adds `branch-admin`;
    `branch-admin` and nationwide `sre` grant the operational department
    roles only. See GRANTABLE_ROLES.
    """
    granted: set[str] = set()
    for role in claims.roles:
        granted |= GRANTABLE_ROLES.get(role, set())
    return granted


def _caller_tier(claims: JWTClaims) -> int:
    """Highest admin tier held by the caller (0 = not an admin)."""
    return max((tier_for_role(r) for r in claims.roles), default=0)


def _tenant_consistent(department_ids: list[str], branch_ids: list[str]) -> bool:
    """True when every branch belongs to one of the given departments.

    A scope is only valid within the tenancy tree: branches must be children
    of the departments they are attached to. Guards against scopes like
    depts=[treasury] + branches=[dha-ict].
    """
    depts = set(department_ids or [])
    for branch in branch_ids or []:
        parent = BRANCHES.get(branch, (None, None))[1]
        if parent is None or parent not in depts:
            return False
    return True


def scope_covers(claims: JWTClaims, department_ids: list[str], branch_ids: list[str], province_ids: list[str] | None = None) -> bool:
    """True when the caller's admin-set scope covers the target scope.

    The caller covers a target when its departments are a subset of the
    caller's departments and (if the caller is branch-narrowed) its branches
    are a subset of the caller's branches. Province scope expands a scope to
    the province's full department set on both sides, so a province-wide
    target (e.g. `province-soc-lead` scoped to Gauteng) is covered only by a
    caller whose province scope spans all of Gauteng. Scopes that are not
    internally tenancy-consistent (branch not under its department) never
    pass. A caller with no admin-set scope covers the estate only via a
    nationwide role; whole-estate (unscoped) targets are unreachable for
    scoped callers.
    """
    caller_depts = set(getattr(claims, "department_ids", None) or [])
    for province in getattr(claims, "province_ids", None) or []:
        caller_depts.update(provincial_departments_for_province(province))
    caller_branches = set(getattr(claims, "branch_ids", None) or [])
    target_depts = set(department_ids or [])
    for province in province_ids or []:
        target_depts.update(provincial_departments_for_province(province))
    target_branches = set(branch_ids or [])

    if target_branches and not _tenant_consistent(department_ids, branch_ids):
        return False

    if not caller_depts and not caller_branches:
        return is_nationwide(claims)
    if not target_depts and not target_branches:
        return False
    if caller_depts and not target_depts <= caller_depts:
        return False
    if caller_branches and not (target_branches and target_branches <= caller_branches):
        return False
    return True


def can_manage(claims: JWTClaims, roles: list[str], department_ids: list[str], branch_ids: list[str], province_ids: list[str] | None = None) -> bool:
    """True when the caller may create/update/delete a user with these roles/scope.

    Two gates, both enforced:

    - Roles: every target role must be grantable by the caller, and no target
      admin-tier role may sit at or above the caller's own tier (delegation is
      strictly one-way down the tenancy tree). Only the managed-service
      creator (`operator`) sits above the SITA superuser, so only `operator`
      can create/rotate a superuser (`admin`).
    - Scope: the target scope must be within the caller's admin-set scope.
    """
    granted = grantable_roles(claims)
    if granted is None:
        return True
    caller_tier = _caller_tier(claims)
    for role in roles:
        role_tier = tier_for_role(role)
        # Allow operator to manage peer operators (creator rotation).
        if role == "operator" and "operator" in claims.roles:
            continue
        # Allow transversal-admin to grant/manage peer transversal-admin accounts.
        if role == "transversal-admin" and "transversal-admin" in claims.roles:
            continue
        if role_tier and role_tier >= caller_tier:
            return False
    if not set(roles) <= granted:
        return False
    return scope_covers(claims, department_ids, branch_ids, province_ids)


def tenant_filter(claims: JWTClaims, model):
    """SQLAlchemy filter scoping a query to the caller's admin-set scope.

    Scope = department_ids (allowed departments) plus optional branch_ids
    (finer restriction within those departments). Province scope
    (province_ids) expands to that province's full department set, so a
    province-level persona (e.g. `province-soc-lead`) is scoped to every
    department inside its province without listing them all. The admin may
    narrow any role, including nationwide ones.

    - Departments set  -> department_id IN (assigned, province-expanded)
    - Branches set     -> branch_id IN (assigned)  (intersects department scope)
    - No scope set     -> nationwide roles see everything (None);
                          department roles fail closed (false()).
    """
    depts = set(getattr(claims, "department_ids", None) or [])
    branches = list(getattr(claims, "branch_ids", None) or [])
    for province in getattr(claims, "province_ids", None) or []:
        depts.update(provincial_departments_for_province(province))
    depts = list(depts)
    conds = []
    if depts:
        conds.append(model.department_id.in_(depts))
    if branches:
        conds.append(model.branch_id.in_(branches))
    if conds:
        return and_(*conds)
    # No scope: nationwide capability wins (admin/exec/compliance/sre see the
    # whole estate even when they also hold a department role); otherwise a
    # department role fails closed until admin assigns it a department.
    if is_nationwide(claims):
        return None
    if is_department_scoped(claims):
        return expression.false()
    return None
