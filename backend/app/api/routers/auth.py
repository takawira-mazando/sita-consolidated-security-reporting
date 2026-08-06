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

router = APIRouter(prefix="/auth", tags=["auth"])

ALL_ROLES = ["exec", "soc", "appsec", "dbsec", "compliance", "sre"]

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

DEMO_ACCOUNTS = [
    {"email": "exec@example.com", "password": "pass123", "roles": ["exec"], "label": "Executive", "role": "exec"},
    {"email": "soc@example.com", "password": "pass123", "roles": ["soc"], "label": "SOC Analyst", "role": "soc"},
    {"email": "appsec@example.com", "password": "pass123", "roles": ["appsec"], "label": "AppSec", "role": "appsec"},
    {"email": "dbsec@example.com", "password": "pass123", "roles": ["dbsec"], "label": "DB Security", "role": "dbsec"},
    {"email": "compliance@example.com", "password": "pass123", "roles": ["compliance"], "label": "Compliance", "role": "compliance"},
    {"email": "sre@example.com", "password": "pass123", "roles": ["sre"], "label": "Service Ops", "role": "sre"},
    {"email": "admin@example.com", "password": "admin123", "roles": ALL_ROLES, "label": "Admin", "role": "admin"},
]

DEMO_ROLE_MAP = {account["role"]: account for account in DEMO_ACCOUNTS}


class LoginRequest(BaseModel):
    email: str
    password: str


class DemoLoginRequest(BaseModel):
    role: str


class UserOut(BaseModel):
    sub: str
    email: str
    roles: list[str]
    name: str | None = None


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
                    is_active=True,
                )
            )
            created += 1
    if created:
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


def _issue(user: User) -> LoginResponse:
    return LoginResponse(
        token=create_access_token(sub=user.id, email=user.email, roles=user.roles),
        user=UserOut(sub=user.id, email=user.email, roles=user.roles, name=user.display_name),
    )


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
    return _issue(user)


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


@router.get("/me", response_model=UserOut)
async def me(claims: JWTClaims = Depends(verify_token)):
    return UserOut(sub=claims.sub, email=claims.email, roles=claims.roles)
