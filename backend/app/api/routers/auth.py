from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, scope_covers, verify_token
from app.config import settings
from app.db import get_session
from app.models.user import User
from app.monitoring.access_audit import (
    record_access,
    request_context,
    scope_digest,
)
from app.security import create_access_token, hash_password, verify_password
from app.tenant import (
    BRANCHES,
    DEPARTMENTS,
    NATIONWIDE_ROLES,
    PROVINCE_DEPARTMENTS,
    PROVINCES,
    PROVINCIAL_DEPARTMENTS,
    province_for_department,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ALL_ROLES = ["exec", "soc", "appsec", "dbsec", "compliance", "sre"]

# Roles grant capabilities; scope (assigned departments/branches) is set per
# user by admin. National roles (exec, compliance, sre) and admin default to
# the whole estate (empty scope); department roles are scoped to their
# assigned departments (optionally narrowed to branches).
DEMO_ACCOUNTS = [
    # The seeded department/province scope below IS each account's tenancy
    # entitlement: /demo-login issues it by default and any scope override
    # must stay within it (scope_covers). Nationwide personas (exec,
    # compliance, sre, transversal-admin) hold an empty scope = whole estate.
    {"email": "exec@example.com", "password": "pass123", "roles": ["exec"], "label": "Executive", "role": "exec", "department_ids": []},  # nosec B105
    {"email": "soc@example.com", "password": "pass123", "roles": ["soc"], "label": "SOC Analyst", "role": "soc", "department_ids": ["home-affairs-digital"]},  # nosec B105
    {"email": "appsec@example.com", "password": "pass123", "roles": ["appsec"], "label": "AppSec", "role": "appsec", "department_ids": ["home-affairs-digital", "treasury"]},  # nosec B105
    {"email": "dbsec@example.com", "password": "pass123", "roles": ["dbsec"], "label": "DB Security", "role": "dbsec", "department_ids": ["home-affairs-digital", "dpsa-hr"]},  # nosec B105
    {"email": "compliance@example.com", "password": "pass123", "roles": ["compliance"], "label": "Compliance", "role": "compliance", "department_ids": []},  # nosec B105
    {"email": "sre@example.com", "password": "pass123", "roles": ["sre"], "label": "Service Ops", "role": "sre", "department_ids": []},  # nosec B105
    {"email": "deptadmin@example.com", "password": "pass123", "roles": ["dept-admin"], "label": "Dept Admin", "role": "dept-admin", "department_ids": ["treasury"]},  # nosec B105
    {"email": "branchadmin@example.com", "password": "pass123", "roles": ["branch-admin"], "label": "Branch Admin", "role": "branch-admin", "department_ids": ["treasury"]},  # nosec B105
    {"email": "transversal@example.com", "password": "pass123", "roles": ["transversal-admin"], "label": "Transversal Admin", "role": "transversal-admin", "department_ids": []},  # nosec B105
    {"email": "provincesoc@example.com", "password": "pass123", "roles": ["province-soc-lead"], "label": "Provincial SOC Lead", "role": "province-soc-lead", "department_ids": [], "province_ids": ["gp"]},  # nosec B105
    {"email": "provdeptadmin@example.com", "password": "pass123", "roles": ["province-dept-admin"], "label": "Provincial Dept Admin", "role": "provdeptadmin", "department_ids": [], "province_ids": ["gp"]},  # nosec B105
    {"email": "localappsec@example.com", "password": "pass123", "roles": ["local-appsec"], "label": "Local AppSec", "role": "localappsec", "department_ids": ["gp-health"], "province_ids": ["gp"]},  # nosec B105
    {"email": "admin@example.com", "password": "admin123", "roles": ["admin"] + ALL_ROLES, "label": "Admin", "role": "admin", "department_ids": []},  # nosec B105
    # Managed-service creator: the platform provider's own credential. Holds
    # no dashboard — its sole function is to create the SITA superuser
    # (`admin`) from the HR pool, plus peer operators for rotation.
    {"email": "operator@example.com", "password": "operator123", "roles": ["operator", "admin"] + ALL_ROLES, "label": "Platform Operator", "role": "operator", "department_ids": []},  # nosec B105

    # Home Affairs department-scoped demo accounts
    {"email": "soc-ha@example.com", "password": "pass123", "roles": ["soc"], "label": "SOC Analyst (Home Affairs)", "role": "soc-ha", "department_ids": ["home-affairs-digital"], "branch_ids": ["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"]},  # nosec B105
    {"email": "appsec-ha@example.com", "password": "pass123", "roles": ["appsec"], "label": "AppSec (Home Affairs)", "role": "appsec-ha", "department_ids": ["home-affairs-digital"], "branch_ids": ["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"]},  # nosec B105
    {"email": "dbsec-ha@example.com", "password": "pass123", "roles": ["dbsec"], "label": "DB Security (Home Affairs)", "role": "dbsec-ha", "department_ids": ["home-affairs-digital"], "branch_ids": ["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"]},  # nosec B105
    {"email": "deptadmin-ha@example.com", "password": "pass123", "roles": ["dept-admin"], "label": "Dept Admin (Home Affairs)", "role": "deptadmin-ha", "department_ids": ["home-affairs-digital"], "branch_ids": ["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"]},  # nosec B105
    {"email": "branchadmin-ha@example.com", "password": "pass123", "roles": ["branch-admin"], "label": "Branch Admin (Home Affairs)", "role": "branchadmin-ha", "department_ids": ["home-affairs-digital"], "branch_ids": ["dha-civic", "dha-digital", "dha-immigration", "dha-operations", "dha-hrmd", "dha-ccss", "dha-finance", "dha-planning"]},  # nosec B105
]

LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 10

_login_attempts: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


async def login_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = monotonic()
    attempts = _login_attempts[ip]
    while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")
    attempts.append(now)

DEMO_ROLE_MAP = {account["role"]: account for account in DEMO_ACCOUNTS}


from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str
    department_id: str | None = None
    branch_id: str | None = None
    province_id: str | None = None


class SwitchTenantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: str | None = None
    branch_id: str | None = None
    province_id: str | None = None


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    department_id: str | None = None
    branch_id: str | None = None
    province_id: str | None = None


class TenancyBranch(BaseModel):
    id: str
    name: str


class TenancyDepartment(BaseModel):
    id: str
    name: str
    branch_count: int
    branches: list[TenancyBranch]
    province_id: str | None = None


class TenancyProvince(BaseModel):
    id: str
    name: str
    department_count: int


class TenancyResponse(BaseModel):
    counts: dict[str, int]
    departments: list[TenancyDepartment]
    provinces: list[TenancyProvince] = []


class UserOut(BaseModel):
    sub: str
    email: str
    roles: list[str]
    name: str | None = None
    department_ids: list[str] = []
    branch_ids: list[str] = []
    province_ids: list[str] = []
    department_id: str | None = None
    department_name: str | None = None
    province_name: str | None = None
    branch_names: list[str] = []


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class DemoAccount(BaseModel):
    email: str
    label: str
    role: str
    department_ids: list[str] = []
    province_ids: list[str] = []
    department_name: str | None = None
    province_name: str | None = None
    is_nationwide: bool = False


async def seed_demo_users(session: AsyncSession) -> int:
    created = 0
    for account in DEMO_ACCOUNTS:
        existing = (
            await session.execute(select(User).where(User.email == account["email"]))
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                User(
                    email=account["email"],
                    password_hash=hash_password(account["password"]),
                    display_name=account["label"],
                    roles=account["roles"],
                    department_ids=account["department_ids"],
                    branch_ids=account.get("branch_ids", []),
                    province_ids=account.get("province_ids", []),
                    is_active=True,
                )
            )
            created += 1
        else:
            existing.roles = account["roles"]
            existing.department_ids = account["department_ids"]
            existing.branch_ids = account.get("branch_ids", [])
            existing.province_ids = account.get("province_ids", [])
            existing.is_active = True
    await session.commit()
    return created


async def bootstrap_superadmin(session: AsyncSession) -> bool:
    """Create the first superadmin (role `admin`) only when identity.users is empty."""
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    if count > 0:
        return False
    session.add(
        User(
            email=settings.bootstrap_admin_email.lower().strip(),
            password_hash=hash_password(settings.bootstrap_admin_password),
            display_name="Superadmin",
            roles=["admin"],
            is_active=True,
        )
    )
    await session.commit()
    return True


def _issue(
    user: User,
    department_ids: list[str] | None = None,
    branch_ids: list[str] | None = None,
    province_ids: list[str] | None = None,
    roles: list[str] | None = None,
) -> LoginResponse:
    depts = list(department_ids if department_ids is not None else (user.department_ids or []))
    branches = list(branch_ids if branch_ids is not None else (user.branch_ids or []))
    provinces = list(province_ids if province_ids is not None else (user.province_ids or []))
    issued_roles = list(roles if roles is not None else (user.roles or []))
    primary = depts[0] if depts else None
    return LoginResponse(
        token=create_access_token(
            sub=user.id,
            email=user.email,
            roles=issued_roles,
            department_ids=depts,
            branch_ids=branches,
            province_ids=provinces,
        ),
        user=UserOut(
            sub=user.id,
            email=user.email,
            roles=issued_roles,
            name=user.display_name,
            department_ids=depts,
            branch_ids=branches,
            province_ids=provinces,
            department_id=primary,
            department_name=DEPARTMENTS.get(primary) if primary else None,
            province_name=PROVINCES.get(provinces[0]) if provinces else None,
            branch_names=[BRANCHES[b][0] for b in branches if b in BRANCHES],
        ),
    )


def _resolve_scope(
    department_id: str | None,
    branch_id: str | None,
    province_id: str | None,
) -> tuple[list[str], list[str], list[str]]:
    """Resolve a requested tenancy scope into (department_ids, branch_ids, province_ids).

    A department scope may be narrowed to one of its branches; a province
    scope expands to the province's full department set and cannot be combined
    with a specific department. Nothing supplied means "account default" and
    is returned as three empty lists.
    """
    if department_id is not None and province_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Choose a department or a province, not both",
        )
    if branch_id is not None and department_id is None:
        raise HTTPException(
            status_code=400,
            detail="A branch scope requires a department",
        )
    if province_id is not None:
        if province_id not in PROVINCES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown province '{province_id}'",
            )
        return [], [], [province_id]
    if department_id is None:
        return [], [], []
    if department_id not in DEPARTMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown department '{department_id}'",
        )
    if branch_id is None:
        return [department_id], [], []
    if branch_id not in BRANCHES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown branch '{branch_id}'",
        )
    parent = BRANCHES[branch_id][1]
    if parent != department_id:
        raise HTTPException(
            status_code=400,
            detail=f"Branch '{branch_id}' belongs to '{parent}', not '{department_id}'",
        )
    return [department_id], [branch_id], []


def _scope_claims(user: User) -> JWTClaims:
    """JWTClaims mirroring a user's admin-set scope (their entitlement)."""
    return JWTClaims(
        sub=user.id,
        email=user.email,
        roles=list(user.roles or []),
        department_ids=list(user.department_ids or []),
        branch_ids=list(user.branch_ids or []),
        province_ids=list(user.province_ids or []),
    )


def _account_default_scope(user: User) -> tuple[list[str], list[str], list[str]]:
    """A demo/real account's own tenancy: the admin-set (seeded) scope.

    Nationwide personas hold an empty scope (whole estate); department- and
    province-scoped personas get exactly their tenant subtree.
    """
    return (
        list(user.department_ids or []),
        list(user.branch_ids or []),
        list(user.province_ids or []),
    )


def _audit_auth(
    session: AsyncSession,
    request: Request | None,
    action: str,
    actor: str,
    outcome: str,
    issued: LoginResponse | None = None,
    reason: str | None = None,
) -> None:
    """Append an authentication access record.

    Failed attempts are recorded too: a spike of ``auth.login_failed`` against
    one address is the signal a SOC needs, and it is only visible if the
    failure path writes a record rather than only the success path.
    """
    user = issued.user if issued else None
    depts = list(user.department_ids or []) if user else []
    branches = list(user.branch_ids or []) if user else []
    provinces = list(user.province_ids or []) if user else []
    roles = list(user.roles or []) if user else []

    detail = {"outcome": outcome, **request_context(request)}
    if reason:
        detail["reason"] = reason

    record_access(
        session,
        action=action,
        actor=actor,
        target=actor,
        tenant_scope={
            "department_ids": depts,
            "branch_ids": branches,
            "province_ids": provinces,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(depts, branches, provinces, roles),
        detail=detail,
    )


def _audit_auth_denied(
    session: AsyncSession,
    request: Request | None,
    action: str,
    actor: str,
    status_code: int,
    reason: str,
) -> None:
    _audit_auth(
        session,
        request,
        action,
        actor,
        outcome="denied",
        reason=f"{status_code}:{reason}",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    _: None = Depends(login_rate_limit),
    session: AsyncSession = Depends(get_session),
):
    attempted = body.email.lower().strip()
    user = (
        await session.execute(select(User).where(User.email == attempted))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        _audit_auth_denied(
            session, request, "auth.login_failed", attempted, 401, "invalid_credentials"
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        _audit_auth_denied(
            session, request, "auth.login_failed", attempted, 403, "account_disabled"
        )
        raise HTTPException(status_code=403, detail="Account is disabled")
    if body.department_id or body.branch_id or body.province_id:
        depts, branches, provinces = _resolve_scope(
            body.department_id, body.branch_id, body.province_id
        )
        if not scope_covers(_scope_claims(user), depts, branches, provinces):
            _audit_auth_denied(
                session, request, "auth.login_failed", attempted, 403, "scope_escalation"
            )
            raise HTTPException(
                status_code=403,
                detail="Requested tenancy scope is outside your assigned scope",
            )
        issued = _issue(user, depts, branches, provinces)
        _audit_auth(session, request, "auth.login", attempted, "success", issued)
        return issued
    issued = _issue(user)
    _audit_auth(session, request, "auth.login", attempted, "success", issued)
    return issued


@router.post("/demo-login", response_model=LoginResponse)
async def demo_login(
    body: DemoLoginRequest,
    request: Request,
    _: None = Depends(login_rate_limit),
    session: AsyncSession = Depends(get_session),
):
    if not settings.seed_demo_users_enabled:
        raise HTTPException(status_code=404, detail="Demo login disabled")
    # In production/demo mode, require password verification
    if settings.environment.lower() not in ("dev", "development", "test", "testing"):
        raise HTTPException(status_code=404, detail="Demo login not available in production")
    account = DEMO_ROLE_MAP.get(body.role)
    if account is None:
        raise HTTPException(status_code=404, detail="Unknown demo role")
    user = (
        await session.execute(select(User).where(User.email == account["email"]))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        _audit_auth_denied(
            session, request, "auth.login_failed", account["email"], 401, "demo_unavailable"
        )
        raise HTTPException(status_code=401, detail="Demo account not available")
    if body.department_id or body.branch_id or body.province_id:
        depts, branches, provinces = _resolve_scope(
            body.department_id, body.branch_id, body.province_id
        )
        if not scope_covers(_scope_claims(user), depts, branches, provinces):
            _audit_auth_denied(
                session, request, "auth.login_failed", account["email"], 403, "scope_escalation"
            )
            raise HTTPException(
                status_code=403,
                detail="Requested tenancy scope is outside this demo account's scope",
            )
        issued = _issue(user, depts, branches, provinces)
        _audit_auth(session, request, "auth.demo_login", account["email"], "success", issued)
        return issued
    # No override: demo accounts sign in as their admin-set (seeded) tenancy —
    # nationwide personas get the whole estate, department-scoped and
    # provincial personas get exactly their tenant subtree.
    depts, branches, provinces = _account_default_scope(user)
    issued = _issue(user, depts, branches, provinces)
    _audit_auth(session, request, "auth.demo_login", account["email"], "success", issued)
    return issued


@router.get("/demo-accounts", response_model=list[DemoAccount])
async def demo_accounts(
    session: AsyncSession = Depends(get_session),
):
    if not settings.seed_demo_users_enabled:
        return []
    emails = [a["email"] for a in DEMO_ACCOUNTS]
    rows = (await session.execute(select(User).where(User.email.in_(emails)))).scalars().all()
    by_email = {u.email: u for u in rows}
    accounts = []
    for account in DEMO_ACCOUNTS:
        user = by_email.get(account["email"])
        if user is None or not user.is_active:
            continue
        primary_dept = (user.department_ids or [None])[0]
        primary_province = (user.province_ids or [None])[0]
        accounts.append(
            DemoAccount(
                email=account["email"],
                label=user.display_name or account["label"],
                role=account["role"],
                department_ids=list(user.department_ids or []),
                province_ids=list(user.province_ids or []),
                department_name=DEPARTMENTS.get(primary_dept) if primary_dept else None,
                province_name=PROVINCES.get(primary_province) if primary_province else None,
                is_nationwide=bool(set(user.roles or []) & NATIONWIDE_ROLES),
            )
        )
    return accounts



@router.get("/tenancy", response_model=TenancyResponse)
async def tenancy_hierarchy():
    """National + provincial hierarchy for the login page.

    Department/branch/province names are public government information; this
    endpoint exists so authenticated users can pick the tenancy context to
    sign into. Access control still happens on the data itself via tenant_filter.
    """
    departments = []
    for dept_id, dept_name in DEPARTMENTS.items():
        branches = [
            TenancyBranch(id=branch_id, name=name)
            for branch_id, (name, parent) in BRANCHES.items()
            if parent == dept_id
        ]
        departments.append(
            TenancyDepartment(
                id=dept_id,
                name=dept_name,
                branch_count=len(branches),
                branches=branches,
                province_id=province_for_department(dept_id),
            )
        )
    provinces = []
    for province_id, province_name in PROVINCES.items():
        provinces.append(
            TenancyProvince(
                id=province_id,
                name=province_name,
                department_count=len(PROVINCE_DEPARTMENTS[province_id]),
            )
        )
    return TenancyResponse(
        counts={
            "departments": len(DEPARTMENTS),
            "branches": len(BRANCHES),
            "provinces": len(PROVINCES),
            "provincial_departments": len(PROVINCIAL_DEPARTMENTS),
        },
        departments=departments,
        provinces=provinces,
    )


@router.get("/me", response_model=UserOut)
async def me(claims: JWTClaims = Depends(verify_token)):
    depts = list(claims.department_ids or [])
    branches = list(claims.branch_ids or [])
    provinces = list(claims.province_ids or [])
    primary = depts[0] if depts else None
    return UserOut(
        sub=claims.sub,
        email=claims.email,
        roles=claims.roles,
        department_ids=depts,
        branch_ids=branches,
        province_ids=provinces,
        department_id=primary,
        department_name=DEPARTMENTS.get(primary) if primary else None,
        province_name=PROVINCES.get(provinces[0]) if provinces else None,
        branch_names=[BRANCHES[b][0] for b in branches if b in BRANCHES],
    )


@router.post("/switch-tenant", response_model=LoginResponse)
async def switch_tenant(
    body: SwitchTenantRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    """Re-issue a token for a new tenancy scope without re-authenticating.

    The target must sit within the user's admin-set entitlement; an empty body
    resets to the account's default (stored) scope.

    Only admin and transversal-admin roles can switch tenants.

    Every switch is audited: it re-scopes a live session across tenant
    boundaries without re-authenticating, so it is the single highest-value
    event to have a signed, attributable record of.
    """
    # Restrict tenant switching to admin/transversal-admin roles only
    if not any(r in claims.roles for r in ["admin", "transversal-admin", "operator"]):
        _audit_auth_denied(
            session,
            request,
            "auth.switch_tenant",
            claims.email or claims.sub,
            403,
            "role_not_permitted",
        )
        raise HTTPException(
            status_code=403,
            detail="Tenant switching restricted to admin and transversal-admin roles"
        )
    user = (
        await session.execute(select(User).where(User.id == claims.sub))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        _audit_auth_denied(
            session,
            request,
            "auth.switch_tenant",
            claims.email or claims.sub,
            401,
            "account_not_available",
        )
        raise HTTPException(status_code=401, detail="Account is not available")
    if body.department_id or body.branch_id or body.province_id:
        depts, branches, provinces = _resolve_scope(
            body.department_id, body.branch_id, body.province_id
        )
        if not scope_covers(_scope_claims(user), depts, branches, provinces):
            _audit_auth_denied(
                session,
                request,
                "auth.switch_tenant",
                claims.email or claims.sub,
                403,
                "scope_escalation",
            )
            raise HTTPException(
                status_code=403,
                detail="Target tenant is outside your assigned scope",
            )
        issued = _issue(user, depts, branches, provinces)
    else:
        depts, branches, provinces = _account_default_scope(user)
        issued = _issue(user, depts, branches, provinces)

    _audit_auth(
        session,
        request,
        "auth.switch_tenant",
        claims.email or claims.sub,
        "success",
        issued,
    )
    return issued
    depts, branches, provinces = _account_default_scope(user)
    return _issue(user, depts, branches, provinces)
