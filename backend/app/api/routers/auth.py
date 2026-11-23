import hashlib
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import employment
from app.api.auth import JWTClaims, verify_token
from app.config import settings
from app.connectors.ldap_connector import ldap_connector
from app.connectors.tenant_ldap_registry import tenant_ldap_registry
from app.tenant_engine import tenant_registry
from app.db import get_session
from app.models.client_organization import ClientOrganization
from app.models.client_superadmin_invitation import ClientSuperadminInvitation
from app.models.person import EmploymentIdentifier, Person
from app.models.tenant_workspace import ClientTenantWorkspace
from app.models.user import User
from app.monitoring.access_audit import (
    record_access,
    request_context,
    scope_digest,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

ALL_ROLES = ["exec", "soc", "appsec", "dbsec", "compliance", "sre"]

# Roles grant capabilities; scope (assigned departments/branches) is set per
# user by admin. National roles (exec, compliance, sre) and admin default to
# the whole estate (empty scope); department roles are scoped to their
# assigned departments (optionally narrowed to branches).
DEMO_ACCOUNTS = [
    {
        "email": "operator@example.com",
        "password": "Platform#Operator2026!Local",
        "roles": ["operator"],
        "label": "Platform Administrator (operator@)",
        "role": "operator",
    },  # nosec B105
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
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")


class CompleteClientSuperadminInvitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=40, max_length=128)
    password: str = Field(..., min_length=12, max_length=128)


class UserOut(BaseModel):
    sub: str
    email: str
    roles: list[str]
    platform_roles: list[str] = []
    name: str | None = None
    tenant_workspace_ids: list[str] = []
    tenant_scope_unit_ids: list[str] = []
    tenant_can_manage_members: bool = False
    tenant_workspace_access: list[dict] = []
    active_tenant_workspace_id: str | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class DemoAccount(BaseModel):
    email: str
    label: str
    role: str
    password: str | None = None


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
        else:
            existing.roles = account["roles"]
            existing.department_ids = []
            existing.branch_ids = []
            existing.province_ids = []
            existing.is_active = True
    await session.commit()
    return created


async def bootstrap_platform_administrator(session: AsyncSession) -> bool:
    """Create the initial platform administrator when the user table is empty."""
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    if count > 0:
        return False
    session.add(
        User(
            email=settings.bootstrap_admin_email.lower().strip(),
            password_hash=hash_password(settings.bootstrap_admin_password or "Admin_Dev_2026!Sec"),
            display_name="Hosi Administrator",
            roles=["operator"],
            is_active=True,
        )
    )
    await session.commit()
    return True


def _issue(
    user: User,
    roles: list[str] | None = None,
    tenant_workspace_ids: list[str] | None = None,
    tenant_scope_unit_ids: list[str] | None = None,
    tenant_can_manage_members: bool = False,
    tenant_workspace_access: list[dict] | None = None,
) -> LoginResponse:
    issued_roles = list(roles if roles is not None else (user.roles or []))
    workspace_roles = {
        cockpit_id
        for workspace in (tenant_workspace_access or [])
        for cockpit_id in (workspace.get("cockpit_scopes") or {})
    }
    display_roles = list(dict.fromkeys([*issued_roles, *sorted(workspace_roles)]))
    if tenant_can_manage_members and "tenant-admin" not in display_roles:
        display_roles.append("tenant-admin")
    return LoginResponse(
        token=create_access_token(
            sub=user.id,
            email=user.email,
            roles=issued_roles,
            tenant_workspace_ids=tenant_workspace_ids or [],
            tenant_scope_unit_ids=tenant_scope_unit_ids or [],
            tenant_can_manage_members=tenant_can_manage_members,
            tenant_workspace_access=tenant_workspace_access or [],
        ),
        user=UserOut(
            sub=user.id,
            email=user.email,
            roles=display_roles,
            platform_roles=issued_roles,
            name=user.display_name,
            tenant_workspace_ids=tenant_workspace_ids or [],
            tenant_scope_unit_ids=tenant_scope_unit_ids or [],
            tenant_can_manage_members=tenant_can_manage_members,
            tenant_workspace_access=tenant_workspace_access or [],
            active_tenant_workspace_id=(
                tenant_workspace_access[0]["workspace_id"]
                if tenant_workspace_access
                else None
            ),
        ),
    )


async def _audit_auth(
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
    workspace_ids = list(user.tenant_workspace_ids or []) if user else []
    scope_unit_ids = list(user.tenant_scope_unit_ids or []) if user else []
    roles = list(user.roles or []) if user else []

    detail = {"outcome": outcome, **request_context(request)}
    if reason:
        detail["reason"] = reason

    await record_access(
        session,
        action=action,
        actor=actor,
        target=actor,
        tenant_scope={
            "tenant_workspace_ids": workspace_ids,
            "tenant_scope_unit_ids": scope_unit_ids,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(workspace_ids, scope_unit_ids, [], roles),
        detail=detail,
    )


async def _audit_auth_denied(
    session: AsyncSession,
    request: Request | None,
    action: str,
    actor: str,
    status_code: int,
    reason: str,
) -> None:
    await _audit_auth(
        session,
        request,
        action,
        actor,
        outcome="denied",
        reason=f"{status_code}:{reason}",
    )


async def _resolve_workspace_assignments(
    session: AsyncSession,
    email: str,
) -> tuple[list[str], list[str], list[str], bool, list[dict]]:
    """Resolve tenant grants without elevating them into global platform scopes."""
    normalized_email = email.lower().strip()
    result = await session.execute(
        select(ClientTenantWorkspace).where(ClientTenantWorkspace.status == "active")
    )
    workspaces = result.scalars().all()

    platform_roles: set[str] = set()
    scope_unit_ids: set[str] = set()
    workspace_ids: set[str] = set()
    can_manage_members = False
    workspace_access: dict[str, dict] = {}

    for workspace in workspaces:
        level_by_key = {
            level.get("key"): level for level in (workspace.hierarchy_levels or [])
        }
        units_by_id = {unit.get("id"): unit for unit in (workspace.org_units or [])}

        def assigned_levels(scope_unit_id: str | None) -> list[str]:
            if not scope_unit_id:
                return ["root", *level_by_key]
            level_key = scope_unit_id
            if level_key not in level_by_key:
                unit = units_by_id.get(level_key)
                level_key = unit.get("level_key") if unit else None
            if level_key not in level_by_key:
                return []
            allowed = {level_key}
            changed = True
            while changed:
                changed = False
                for key, level in level_by_key.items():
                    if key not in allowed and level.get("parent_key") in allowed:
                        allowed.add(key)
                        changed = True
            return [key for key in level_by_key if key in allowed]

        for assignment in workspace.assignments or []:
            if str(assignment.get("email", "")).lower().strip() != normalized_email:
                continue
            workspace_ids.add(workspace.id)
            role_by_id = {role["id"]: role for role in (workspace.roles or [])}
            scope_unit_id = assignment.get("scope_unit_id")
            if scope_unit_id:
                scope_unit_ids.add(scope_unit_id)
            scope_levels = assigned_levels(scope_unit_id)
            workspace_grant = workspace_access.setdefault(
                workspace.id,
                {
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "administration_model": workspace.administration_model,
                    "admin_scope_level_keys": [],
                    "cockpit_scopes": {},
                },
            )

            assigned_roles = [
                role_by_id[role_id]
                for role_id in assignment.get("role_ids", [])
                if role_id in role_by_id
            ]
            for role in assigned_roles:
                for cockpit_id in role.get("cockpit_ids", []):
                    if cockpit_id in ALL_ROLES:
                        allowed_levels = workspace_grant["cockpit_scopes"].setdefault(
                            cockpit_id, []
                        )
                        allowed_levels.extend(
                            level for level in scope_levels if level not in allowed_levels
                        )
            if workspace.administration_model in ("delegated", "shared") and (
                assignment.get("admin_access") is True
                or (
                    "admin_access" not in assignment
                    and any(role.get("can_manage_members") for role in assigned_roles)
                )
            ):
                can_manage_members = True
                workspace_grant["admin_scope_level_keys"].extend(
                    level
                    for level in scope_levels
                    if level not in workspace_grant["admin_scope_level_keys"]
                )

    if can_manage_members:
        platform_roles.add("tenant-admin")
    return (
        list(dict.fromkeys(platform_roles)),
        list(dict.fromkeys(workspace_ids)),
        list(dict.fromkeys(scope_unit_ids)),
        can_manage_members,
        list(workspace_access.values()),
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
        # Fallback to multi-tenant LDAP directory authentication for enterprise unified security
        ldap_auth_ok = False
        ldap_user_id = None
        detected_tenant = None
        ldap_auth_ok, ldap_user_id, detected_tenant = await tenant_ldap_registry.authenticate(
            attempted, body.password
        )

        if ldap_auth_ok and ldap_user_id is not None:
            if user is None:
                # Auto-provision local user account from verified LDAP identity
                p_id = str(uuid.uuid4())
                person = Person(
                    id=p_id,
                    employee_number=ldap_user_id.employee_code,
                    surname=ldap_user_id.surname,
                    initials=ldap_user_id.initials,
                    display_name=ldap_user_id.display_name,
                    job_title=ldap_user_id.position,
                    email=(ldap_user_id.email or attempted).lower().strip(),
                    department_id=ldap_user_id.department_id,
                    branch_id=ldap_user_id.branch_id,
                    source="ldap",
                    is_active=True,
                )
                session.add(person)
                session.add(
                    EmploymentIdentifier(
                        person_id=p_id,
                        scheme=employment.SCHEME_LDAP,
                        value=ldap_user_id.employee_code or ldap_user_id.username,
                        source_system="ldap",
                    )
                )
                user = User(
                    id=str(uuid.uuid4()),
                    email=(ldap_user_id.email or attempted).lower().strip(),
                    password_hash=hash_password(body.password),
                    display_name=ldap_user_id.display_name,
                    roles=ldap_user_id.suggested_roles or ["soc"],
                    person_id=p_id,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                if ldap_user_id.display_name and not user.display_name:
                    user.display_name = ldap_user_id.display_name
                await session.commit()
        else:
            await _audit_auth_denied(
                session, request, "auth.login_failed", attempted, 401, "invalid_credentials"
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        await _audit_auth_denied(
            session, request, "auth.login_failed", attempted, 403, "account_disabled"
        )
        raise HTTPException(status_code=403, detail="Account is disabled")
    (
        assigned_roles,
        assigned_workspaces,
        assigned_scope_units,
        can_manage_members,
        assigned_workspace_access,
    ) = await _resolve_workspace_assignments(session, user.email)
    effective_roles = list(dict.fromkeys([*(user.roles or []), *assigned_roles]))
    issued = _issue(
        user,
        effective_roles,
        assigned_workspaces,
        assigned_scope_units,
        can_manage_members,
        assigned_workspace_access,
    )
    await _audit_auth(session, request, "auth.login", attempted, "success", issued)
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
        await _audit_auth_denied(
            session, request, "auth.login_failed", account["email"], 401, "demo_unavailable"
        )
        raise HTTPException(status_code=401, detail="Demo account not available")
    (
        assigned_roles,
        assigned_workspaces,
        assigned_scope_units,
        can_manage_members,
        assigned_workspace_access,
    ) = await _resolve_workspace_assignments(session, user.email)
    effective_roles = list(dict.fromkeys([*(user.roles or []), *assigned_roles]))
    issued = _issue(
        user,
        effective_roles,
        assigned_workspaces,
        assigned_scope_units,
        can_manage_members,
        assigned_workspace_access,
    )
    await _audit_auth(session, request, "auth.demo_login", account["email"], "success", issued)
    return issued


@router.get(
    "/demo-accounts",
    response_model=list[DemoAccount],
    response_model_exclude_unset=True,
)
async def demo_accounts(
    session: AsyncSession = Depends(get_session),
):
    if not settings.seed_demo_users_enabled:
        return []
    emails = [a["email"] for a in DEMO_ACCOUNTS]
    rows = (await session.execute(select(User).where(User.email.in_(emails)))).scalars().all()
    by_email = {u.email: u for u in rows}
    accounts = []
    expose_local_credentials = settings.environment.lower() in (
        "dev",
        "development",
        "test",
        "testing",
    )
    for account in DEMO_ACCOUNTS:
        user = by_email.get(account["email"])
        if user is None or not user.is_active:
            continue
        account_details = {
            "email": account["email"],
            "label": user.display_name or account["label"],
            "role": account["role"],
        }
        if expose_local_credentials:
            account_details["password"] = account["password"]
        accounts.append(DemoAccount(**account_details))
    return accounts


@router.post("/client-superadmin-invitations/complete")
async def complete_client_superadmin_invitation(
    body: CompleteClientSuperadminInvitation,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    result = await session.execute(
        select(ClientSuperadminInvitation)
        .where(
            ClientSuperadminInvitation.token_hash == token_hash,
            ClientSuperadminInvitation.used_at.is_(None),
            ClientSuperadminInvitation.revoked_at.is_(None),
            ClientSuperadminInvitation.expires_at > now,
        )
        .with_for_update()
    )
    invitation = result.scalars().first()
    if invitation is None:
        raise HTTPException(status_code=400, detail="This invitation is invalid, expired, or already used.")

    client = await session.get(ClientOrganization, invitation.client_organization_id)
    person = await session.get(Person, invitation.person_id)
    if (
        client is None
        or client.status != "active"
        or client.superadmin_email.strip().lower() != invitation.email
        or person is None
        or not person.is_active
        or person.employment_status != "active"
        or person.source not in employment.VERIFIED_PERSON_SOURCES
        or (person.email or "").strip().lower() != invitation.email
    ):
        raise HTTPException(
            status_code=400,
            detail="This invitation is no longer valid for the selected client professional.",
        )

    existing_user = (
        await session.execute(select(User).where(func.lower(User.email) == invitation.email))
    ).scalars().first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="A platform account already exists for this professional.")

    user = User(
        id=str(uuid.uuid4()),
        email=invitation.email,
        password_hash=hash_password(body.password),
        display_name=person.display_name or f"{person.initials or ''} {person.surname or ''}".strip(),
        roles=["client-admin"],
        department_ids=[],
        branch_ids=[],
        province_ids=[],
        person_id=person.id,
        is_active=True,
    )
    invitation.used_at = now
    client.access_setup_status = "pending_client_workspace"
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="The account could not be created; it may already exist.",
        ) from exc

    await _audit_auth(
        session,
        request,
        "auth.client_superadmin_invite_complete",
        invitation.email,
        "success",
    )
    return {"status": "password_set", "email": invitation.email}



@router.get("/me", response_model=UserOut)
async def me(claims: JWTClaims = Depends(verify_token)):
    workspace_roles = {
        cockpit_id
        for workspace in claims.tenant_workspace_access
        for cockpit_id in (workspace.get("cockpit_scopes") or {})
    }
    return UserOut(
        sub=claims.sub,
        email=claims.email,
        roles=list(dict.fromkeys([*claims.roles, *sorted(workspace_roles)])),
        platform_roles=claims.roles,
        tenant_workspace_ids=claims.tenant_workspace_ids,
        tenant_scope_unit_ids=claims.tenant_scope_unit_ids,
        tenant_can_manage_members=claims.tenant_can_manage_members,
        tenant_workspace_access=claims.tenant_workspace_access,
        active_tenant_workspace_id=claims.active_tenant_workspace_id,
    )
