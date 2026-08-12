from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, verify_token
from app.config import settings
from app.db import get_session
from app.models.user import User
from app.security import create_access_token, hash_password, verify_password
from app.tenant import (
    BRANCHES,
    DEPARTMENTS,
    NATIONWIDE_ROLES,
    PROVINCE_DEPARTMENTS,
    PROVINCES,
    PROVINCIAL_DEPARTMENTS,
    PROVINCIAL_ROLES,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ALL_ROLES = ["exec", "soc", "appsec", "dbsec", "compliance", "sre"]

# Roles grant capabilities; scope (assigned departments/branches) is set per
# user by admin. National roles (exec, compliance, sre) and admin default to
# the whole estate (empty scope); department roles are scoped to their
# assigned departments (optionally narrowed to branches).
DEMO_ACCOUNTS = [
    # Demo accounts still carry the seeded department scope used by the
    # regular email/password login; /demo-login ignores it and widens the
    # issued token to the whole estate unless a scope override is supplied.
    {"email": "exec@example.com", "password": "pass123", "roles": ["exec"], "label": "Executive", "role": "exec", "department_ids": []},
    {"email": "soc@example.com", "password": "pass123", "roles": ["soc"], "label": "SOC Analyst", "role": "soc", "department_ids": ["home-affairs-digital"]},
    {"email": "appsec@example.com", "password": "pass123", "roles": ["appsec"], "label": "AppSec", "role": "appsec", "department_ids": ["treasury"]},
    {"email": "dbsec@example.com", "password": "pass123", "roles": ["dbsec"], "label": "DB Security", "role": "dbsec", "department_ids": ["dpsa-hr"]},
    {"email": "compliance@example.com", "password": "pass123", "roles": ["compliance"], "label": "Compliance", "role": "compliance", "department_ids": []},
    {"email": "sre@example.com", "password": "pass123", "roles": ["sre"], "label": "Service Ops", "role": "sre", "department_ids": []},
    {"email": "deptadmin@example.com", "password": "pass123", "roles": ["dept-admin"], "label": "Dept Admin", "role": "dept-admin", "department_ids": ["treasury"]},
    {"email": "branchadmin@example.com", "password": "pass123", "roles": ["branch-admin"], "label": "Branch Admin", "role": "branch-admin", "department_ids": ["treasury"]},
    {"email": "transversal@example.com", "password": "pass123", "roles": ["transversal-admin"], "label": "Transversal Admin", "role": "transversal-admin", "department_ids": []},
    {"email": "provincesoc@example.com", "password": "pass123", "roles": ["province-soc-lead"], "label": "Provincial SOC Lead", "role": "province-soc-lead", "department_ids": [], "province_ids": ["gp"]},
    {"email": "admin@example.com", "password": "admin123", "roles": ALL_ROLES, "label": "Admin", "role": "admin", "department_ids": []},
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


class LoginRequest(BaseModel):
    email: str
    password: str


class DemoLoginRequest(BaseModel):
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
                    branch_ids=[],
                    province_ids=account.get("province_ids", []),
                    is_active=True,
                )
            )
            created += 1
        elif existing.department_ids in (None, []) and account["department_ids"]:
            existing.department_ids = account["department_ids"]
    if created or True:
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


def _demo_scope(department_id: str | None, branch_id: str | None) -> tuple[list[str], list[str]]:
    """Resolve an optional demo-login scope against the national hierarchy.

    Returns (department_ids, branch_ids). No department means no override
    (the account's admin-set scope applies). A branch must belong to the
    chosen department.
    """
    if department_id is None:
        return [], []
    if department_id not in DEPARTMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown department '{department_id}'",
        )
    if branch_id is None:
        return [department_id], []
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
    return [department_id], [branch_id]


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    _: None = Depends(login_rate_limit),
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(select(User).where(User.email == body.email.lower().strip()))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return _issue(user)


def _demo_nationwide_roles(user: User) -> list[str]:
    """Roles issued for a demo login with no scope override.

    Demo accounts default to the whole estate: an empty scope plus a nationwide
    role. tenant_filter treats an empty scope as whole-estate for nationwide
    roles and fails closed for department roles, so a nationwide role must be
    granted or a department-scoped demo account would see nothing. Provincial
    personas are the exception: they keep their province scope (see
    `_demo_province_scope`) so tenant isolation is demonstrable.
    """
    roles = list(user.roles or [])
    if not set(roles) & NATIONWIDE_ROLES and not set(roles) & PROVINCIAL_ROLES:
        roles.append("exec")
    return roles


def _demo_province_scope(user: User) -> list[str]:
    """Province scope issued for a provincial-persona demo login.

    Provincial personas are seeded with a province so their JWT carries it
    end-to-end and tenant_filter scopes reads to that province's departments.
    Non-provincial accounts stay unscoped (whole estate) for demo purposes.
    """
    if set(user.roles or []) & PROVINCIAL_ROLES:
        return list(user.province_ids or [])
    return []


@router.post("/demo-login", response_model=LoginResponse)
async def demo_login(
    body: DemoLoginRequest,
    request: Request,
    _: None = Depends(login_rate_limit),
    session: AsyncSession = Depends(get_session),
):
    if not settings.seed_demo_users_enabled:
        raise HTTPException(status_code=404, detail="Demo login disabled")
    account = DEMO_ROLE_MAP.get(body.role)
    if account is None:
        raise HTTPException(status_code=404, detail="Unknown demo role")
    user = (
        await session.execute(select(User).where(User.email == account["email"]))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Demo account not available")
    if body.department_id:
        dept_ids, branch_ids = _demo_scope(body.department_id, body.branch_id)
        return _issue(user, dept_ids, branch_ids)
    if body.province_id:
        if body.province_id not in PROVINCES:
            raise HTTPException(status_code=400, detail=f"Unknown province '{body.province_id}'")
        return _issue(user, [], [], province_ids=[body.province_id])
    # No override: demo accounts default to the whole estate (ignore the seeded
    # scope). The login page can still narrow via a scope override above.
    return _issue(user, [], [], roles=_demo_nationwide_roles(user), province_ids=_demo_province_scope(user))


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
        accounts.append(DemoAccount(email=account["email"], label=user.display_name or account["label"], role=account["role"]))
    return accounts


@router.get("/tenancy", response_model=TenancyResponse)
async def tenancy_hierarchy():
    """Public national + provincial hierarchy for the login page.

    Department/branch/province names are public government information; this
    endpoint exists so pre-authenticated users can pick the tenancy context to
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
