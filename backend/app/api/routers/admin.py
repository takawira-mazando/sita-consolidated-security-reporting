import asyncio
import logging
import re
import secrets
from datetime import datetime, timezone
from math import ceil
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import employment
from app.api.auth import (
    ROLES_HIERARCHY,
    can_manage,
    person_within_scope,
    require_roles,
    scope_covers,
    tenant_filter,
    verify_token,
)
from app.config import settings
from app.db import get_session
from app.employment import (
    SCHEME_LDAP,
    IdentifierSchemeError,
)
from app.connectors.ldap_connector import ldap_connector, LDAPConfig, DirectoryUser
from app.connectors.tenant_ldap_registry import tenant_ldap_registry, TenantLDAPConfig, TierRoleAssignment
from app.tenant_engine import tenant_registry
from app.tenant_profiles import get_active_profile, set_active_profile
from app.ingestion.dlq import DLQManager
from app.models.connector_status import ConnectorHealth
from app.models.dlq import RejectedRecord
from app.models.person import EmploymentIdentifier, Person
from app.models.user import User
from app.models.client_organization import ClientOrganization
from app.monitoring.access_audit import (
    record_access,
    request_context,
    scope_digest,
)
from app.pii import apply_person_policy
from app.security import hash_password
from app.services.client_superadmin_invite import (
    InvitationEmailConfigurationError,
    InvitationEmailDeliveryError,
    send_client_superadmin_credentials,
)
from app.tenant import BRANCHES, DEPARTMENTS, PROVINCES

router = APIRouter(tags=["admin"])

logger = logging.getLogger(__name__)

VALID_ROLES = set(ROLES_HIERARCHY.keys())


def _mask_id_number(val: str | None) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if len(s) <= 4:
        return "****"
    return "*" * (len(s) - 4) + s[-4:]


async def require_hosi_provider(claims=Depends(verify_token)):
    if "operator" not in claims.roles:
        raise HTTPException(status_code=403, detail="Hosi Technologies provider access required")
    return claims


async def _audit_admin_read(
    session: AsyncSession,
    request: Request | None,
    claims: Any,
    action: str,
    returned: int,
    total: int,
) -> None:
    """Record a privileged read of identity or person records.

    ``returned`` and ``total`` are both recorded: a caller paging through the
    full set of users is a materially different event from one that opened the
    first page of twenty.
    """
    depts = list(getattr(claims, "department_ids", None) or [])
    branches = list(getattr(claims, "branch_ids", None) or [])
    provinces = list(getattr(claims, "province_ids", None) or [])
    roles = list(getattr(claims, "roles", None) or [])
    await record_access(
        session,
        action=action,
        actor=getattr(claims, "email", None) or claims.sub,
        target=action.split(".")[-1],
        tenant_scope={
            "department_ids": depts,
            "branch_ids": branches,
            "province_ids": provinces,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(depts, branches, provinces, roles),
        detail={
            "rows_returned": returned,
            "rows_in_scope": total,
            **request_context(request),
        },
    )


async def _audit_privilege_change(
    session: AsyncSession,
    request: Request | None,
    claims: Any,
    action: str,
    target: str,
    detail: dict,
) -> None:
    """Record a change to an account's roles, scope or active state.

    Delegated authority (`can_manage`) makes account administration the main
    privilege-escalation surface in the platform: a role or scope change is the
    only way to widen what a session can reach, so each one is signed and bound
    to the actor who made it.
    """
    depts = list(getattr(claims, "department_ids", None) or [])
    branches = list(getattr(claims, "branch_ids", None) or [])
    provinces = list(getattr(claims, "province_ids", None) or [])
    roles = list(getattr(claims, "roles", None) or [])
    await record_access(
        session,
        action=action,
        actor=getattr(claims, "email", None) or claims.sub,
        target=target,
        tenant_scope={
            "department_ids": depts,
            "branch_ids": branches,
            "province_ids": provinces,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(depts, branches, provinces, roles),
        detail={**detail, **request_context(request)},
    )


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["soc"])
    department_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    province_ids: list[str] = Field(default_factory=list)
    # Accounts can only be provisioned for directory identities. There is
    # no path to create an external/non-employee user.
    #
    # Identify the employee by an existing directory-provisioned person key or
    # an LDAP directory identifier.
    person_id: str | None = None
    identifier_scheme: str | None = None
    identifier_value: str | None = None

    @model_validator(mode="after")
    def _validate_directory_person(self):
        if not self.person_id and not (self.identifier_scheme and self.identifier_value):
            raise ValueError(
                "User account must be linked to an existing LDAP directory identity "
                "using person_id or an LDAP identifier."
            )
        return self


class UserUpdate(BaseModel):
    display_name: str | None = None
    roles: list[str] | None = None
    department_ids: list[str] | None = None
    branch_ids: list[str] | None = None
    province_ids: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    person_id: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    roles: list[str]
    department_ids: list[str]
    branch_ids: list[str]
    province_ids: list[str] = []
    department_id: str | None = None
    department_name: str | None = None
    province_name: str | None = None
    branch_names: list[str] = []
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _to_out(user: User, person: Person | None = None) -> dict:
    depts = list(user.department_ids or [])
    branches = list(user.branch_ids or [])
    provinces = list(user.province_ids or [])
    primary = depts[0] if depts else None
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "roles": list(user.roles or []),
        "department_ids": depts,
        "branch_ids": branches,
        "province_ids": provinces,
        "department_id": primary,
        "department_name": DEPARTMENTS.get(primary) if primary else None,
        "province_name": PROVINCES.get(provinces[0]) if provinces else None,
        "branch_names": [BRANCHES[b][0] for b in branches if b in BRANCHES],
        "person_id": user.person_id,
        "person": apply_person_policy(
            {
                "employee_number": person.employee_number,
                "title": person.title,
                "initials": person.initials,
                "surname": person.surname,
                "display_name": person.display_name,
                "id_number": person.id_number,
                "job_title": person.job_title,
                "org_unit": person.org_unit,
                "department_id": person.department_id,
                "branch_id": person.branch_id,
                "manager_id": person.manager_id,
                "manager_name": person.manager_name,
                "work_phone": person.work_phone,
                "location": person.location,
                "employment_status": person.employment_status,
                "clearance_level": person.clearance_level,
                "source": person.source,
            }
        )
        if person is not None
        else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
def _active_departments() -> dict[str, str]:
    profile = get_active_profile()
    units = profile.get_org_units_by_level(0)
    merged = dict(DEPARTMENTS)
    merged.update(units)
    return merged


def _active_branches() -> dict[str, tuple[str, str]]:
    profile = get_active_profile()
    branches = {
        uid: (unit.name, unit.parent_id or "")
        for uid, unit in profile.org_units.items()
        if unit.level == 1
    }
    merged = dict(BRANCHES)
    merged.update(branches)
    return merged


def _validate_departments(department_ids: list[str]) -> None:
    valid = _active_departments()
    invalid = [d for d in department_ids if d not in valid]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail="One or more specified departments are invalid",
        )


def _validate_provinces(province_ids: list[str]) -> None:
    profile = get_active_profile()
    valid_groups = dict(PROVINCES)
    valid_groups.update(profile.groups)
    invalid = [p for p in province_ids if p not in valid_groups]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail="One or more specified provinces are invalid",
        )


def _validate_branches(branch_ids: list[str], department_ids: list[str]) -> None:
    valid_branches = _active_branches()
    for branch in branch_ids:
        if branch not in valid_branches:
            raise HTTPException(
                status_code=400,
                detail="One or more specified branches are invalid",
            )
        parent = valid_branches[branch][1]
        if parent not in department_ids:
            raise HTTPException(
                status_code=400,
                detail="Branch does not belong to the user's assigned departments",
            )


def _validate_scope(roles: list[str], department_ids: list[str], branch_ids: list[str], province_ids: list[str] | None = None) -> None:
    from app.tenant import DEPARTMENT_ROLES, PROVINCIAL_ROLES
    has_department_role = bool(set(roles) & DEPARTMENT_ROLES)
    has_scope = bool(department_ids or province_ids)
    if has_department_role and not has_scope:
        raise HTTPException(
            status_code=400,
            detail=(
                "Tenant-scoped operational roles (soc/appsec/dbsec/"
                "province-soc-lead/local-appsec) require at "
                "least one assigned department or province."
            ),
        )
    if set(roles) & PROVINCIAL_ROLES and not province_ids and not department_ids:
        raise HTTPException(
            status_code=400,
            detail="Regional SITA operator roles (province-soc-lead/local-appsec) require at least one assigned province or department.",
        )
    if branch_ids and not department_ids:
        raise HTTPException(
            status_code=400,
            detail="Branch scope requires at least one assigned department.",
        )


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


@router.get("/departments")
async def list_departments(
    claims = Depends(require_roles("admin_read")),
):
    valid = _active_departments()
    return {
        "items": [
            {"id": dept_id, "name": name}
            for dept_id, name in valid.items()
        ]
    }


@router.get("/branches")
async def list_branches(
    department_id: str | None = None,
    claims = Depends(require_roles("admin_read")),
):
    valid_depts = _active_departments()
    valid_branches = _active_branches()
    items = [
        {
            "id": branch_id,
            "name": name,
            "department_id": parent,
            "department_name": valid_depts.get(parent),
        }
        for branch_id, (name, parent) in valid_branches.items()
        if department_id is None or parent == department_id
    ]
    return {"items": items}


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
    page: int = Query(default=1, ge=1, le=10000),
    size: int = Query(default=20, ge=1, le=200),
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


@router.post("/connectors/pull-logs")
async def pull_logs_endpoint(
    source: str = "all",
    count: int = 10,
    claims = Depends(require_roles("admin_write")),
):
    from scripts.demo_pull_logs import ingest_to_lake, pull_appscan_logs, pull_thales_logs
    pulled = {}
    if source in ("all", "appscan"):
        appscan_records = await pull_appscan_logs(count=count)
        n = await ingest_to_lake(appscan_records, "appscan")
        pulled["appscan"] = {"pulled": len(appscan_records), "ingested": n}
    if source in ("all", "thales"):
        thales_records = await pull_thales_logs(count=count)
        n = await ingest_to_lake(thales_records, "thales")
        pulled["thales"] = {"pulled": len(thales_records), "ingested": n}
    return {
        "status": "success",
        "results": pulled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Logs successfully pulled and synchronized into data lake.",
    }


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
    request: Request,
    page: int = Query(default=1, ge=1, le=10000),
    size: int = Query(default=20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    size = min(max(size, 1), 200)
    page = max(page, 1)
    rows = (await session.execute(
        select(User, Person)
        .outerjoin(Person, Person.id == User.person_id)
        .order_by(User.created_at.desc())
    )).all()
    in_scope = [
        (u, p)
        for u, p in rows
        if scope_covers(
            claims,
            list(u.department_ids or []),
            list(u.branch_ids or []),
            list(u.province_ids or []),
        )
    ]
    total = len(in_scope)
    items = [_to_out(u, p) for u, p in in_scope[(page - 1) * size : (page - 1) * size + size]]
    await _audit_admin_read(session, request, claims, "data.read.users", len(items), total)
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


async def _resolve_provisioning_target(session: AsyncSession, body: UserCreate, claims: Any = None) -> Person:
    """Resolve the LDAP directory identity an account is being provisioned against."""
    has_key = bool(body.person_id)
    has_identifier = bool(body.identifier_scheme or body.identifier_value)

    if has_key and has_identifier:
        raise HTTPException(
            status_code=400,
            detail=(
                "Supply either person_id or identifier_scheme + identifier_value, "
                "not both."
            ),
        )

    if has_key:
        person = await session.get(Person, body.person_id)
        if person is None:
            raise HTTPException(
                status_code=400,
                detail=f"No LDAP directory identity found for person_id '{body.person_id}'. "
                "Use /admin/persons to look up an employee.",
            )
        if not person.is_active or person.source not in employment.VERIFIED_PERSON_SOURCES:
            raise HTTPException(
                status_code=400,
                detail="Only active LDAP directory identities may receive platform roles.",
            )
        return person

    if has_identifier:
        if not (body.identifier_scheme and body.identifier_value):
            raise HTTPException(
                status_code=400,
                detail="identifier_scheme and identifier_value must both be supplied.",
            )
        scheme_norm = body.identifier_scheme.lower().strip()
        if scheme_norm != SCHEME_LDAP:
            raise HTTPException(
                status_code=400,
                detail="Only LDAP directory identifiers are accepted.",
            )
        try:
            person = await resolve_person_by_identifier(
                session, scheme_norm, body.identifier_value
            )
        except IdentifierSchemeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if person is not None and (
            not person.is_active or person.source not in employment.VERIFIED_PERSON_SOURCES
        ):
            raise HTTPException(
                status_code=400,
                detail="Only active LDAP directory identities may receive platform roles.",
            )

        if person is None:
            val = body.identifier_value.strip()
            dir_user = await ldap_connector.lookup_by_code(val)
            if dir_user is not None:
                person = Person(
                    id=str(uuid.uuid4()),
                    employee_number=dir_user.employee_code or dir_user.username,
                    surname=dir_user.surname,
                    initials=dir_user.initials,
                    display_name=dir_user.display_name,
                    job_title=dir_user.position,
                    email=(dir_user.email or body.email).lower().strip(),
                    department_id=dir_user.department_id or (body.department_ids[0] if body.department_ids else None),
                    branch_id=dir_user.branch_id or (body.branch_ids[0] if body.branch_ids else None),
                    source="ldap",
                    is_active=True,
                )
                session.add(person)
                await session.flush()
                await _record_employment_identifier(
                    session,
                    person,
                    scheme=SCHEME_LDAP,
                    value=dir_user.employee_code or dir_user.username,
                    source_system="ldap",
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No LDAP directory identity carries identifier "
                        f"'{body.identifier_value}'. Confirm the identifier or import the directory user."
                    ),
                )
        return person

    raise HTTPException(
        status_code=400,
        detail="Select an existing LDAP directory identity or supply its LDAP identifier.",
    )


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    """
    Create a platform account for a verified enterprise directory identity.

    The platform administrator assigns security roles and government tenant data
    scopes. The platform operator may create or rotate superadmin accounts.
    Department, branch, and province assignments constrain data access; they do
    not delegate user administration. Exactly one directory `person_id` or an
    LDAP identifier
    must be supplied.
    - **email**: Must match the directory user's registered email.
    - **roles**: Must contain valid platform roles.
    - **department_ids**: Must contain valid department slugs (e.g., `treasury`) if the role requires department scoping.
    - **branch_ids**: If provided, must belong to the specified department.

    ### Provisioning checks
    The caller must be the platform superadmin (or bootstrap operator). The
    identity must be active and verified by LDAP / Enterprise Directory. The
    assigned tenant scope must pass the role/scope validators.

    ### Security
    - Requires `admin_write` permission.
    - Attempts to escalate privileges or scope will result in `HTTP 403 Forbidden`.
    """
    _validate_roles(body.roles)
    _validate_departments(body.department_ids)
    _validate_branches(body.branch_ids, body.department_ids)
    _validate_provinces(body.province_ids)
    _validate_scope(body.roles, body.department_ids, body.branch_ids, body.province_ids)
    if not can_manage(claims, body.roles, body.department_ids, body.branch_ids, body.province_ids):
        raise HTTPException(
            status_code=403,
            detail="You may only create users whose roles and scope are within your delegated authority.",
        )
    email = body.email.lower().strip()
    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    person = await _resolve_provisioning_target(session, body, claims)

    if not person.is_active:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Employee record for '{person.display_name or person.employee_number}' "
                "is not active (separated or terminated). An account may only be "
                "provisioned against a current employee."
            ),
        )

    # Tenancy gate: whose employee is this? Distinct from the delegation check
    # above, which only asks whether the granted authority is within the
    # caller's own reach. This also prevents provisioning another tenant's
    # directory identity inside the caller's tenant.
    if not person_within_scope(claims, person):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Employee '{person.display_name or person.employee_number}' belongs "
                f"to department '{person.department_id or 'unassigned'}' / branch "
                f"'{person.branch_id or 'unassigned'}', which is outside your assigned "
                "tenancy scope. You may only provision employees within your own scope."
            ),
        )

    person_email = (person.email or "").lower().strip()
    if not person_email:
        raise HTTPException(
            status_code=400,
            detail="LDAP directory identity has no registered email; an account cannot be provisioned.",
        )
    if email != person_email:
        raise HTTPException(
            status_code=400,
            detail="Account email must match the LDAP directory identity's email.",
        )

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=person.display_name or body.display_name,
        roles=body.roles,
        department_ids=list(dict.fromkeys(body.department_ids)),
        branch_ids=list(dict.fromkeys(body.branch_ids)),
        province_ids=list(dict.fromkeys(body.province_ids)),
        person_id=person.id,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await _audit_privilege_change(
        session,
        None,
        claims,
        action="admin.user.create",
        target=email,
        detail={
            "roles": list(user.roles or []),
            "department_ids": list(user.department_ids or []),
            "branch_ids": list(user.branch_ids or []),
            "province_ids": list(user.province_ids or []),
            "person_id": user.person_id,
        },
    )
    return _to_out(user, person)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    user = await _get_user_or_404(session, user_id)
    depts = body.department_ids if body.department_ids is not None else list(user.department_ids or [])
    branches = body.branch_ids if body.branch_ids is not None else list(user.branch_ids or [])
    provinces = body.province_ids if body.province_ids is not None else list(user.province_ids or [])
    target_roles = body.roles if body.roles is not None else list(user.roles or [])
    if not can_manage(claims, target_roles, depts, branches, provinces):
        raise HTTPException(
            status_code=403,
            detail="You may only update users whose roles and scope are within your delegated authority.",
        )
    if body.roles is not None:
        _validate_roles(body.roles)
        _validate_scope(body.roles, depts, branches, provinces)
        if user.id == claims.sub and not body.roles:
            raise HTTPException(status_code=400, detail="You cannot remove all roles from your own account")
    _validate_departments(depts)
    _validate_branches(branches, depts)
    _validate_provinces(provinces)
    if body.is_active is False and user.id == claims.sub:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    # Captured before mutation so the record shows the authority change, not
    # just the end state — an audit that only logs the new roles cannot answer
    # "who granted this and from what".
    prior = {
        "roles": list(user.roles or []),
        "department_ids": list(user.department_ids or []),
        "branch_ids": list(user.branch_ids or []),
        "province_ids": list(user.province_ids or []),
        "is_active": bool(user.is_active),
    }

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.roles is not None:
        user.roles = body.roles
    if body.department_ids is not None:
        user.department_ids = list(dict.fromkeys(body.department_ids))
    if body.branch_ids is not None:
        user.branch_ids = list(dict.fromkeys(body.branch_ids))
    if body.province_ids is not None:
        user.province_ids = list(dict.fromkeys(body.province_ids))
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)

    person = None
    if body.person_id is not None:
        person = await session.get(Person, body.person_id)
        if person is None:
            raise HTTPException(
                status_code=400,
                detail=f"No LDAP directory person found for person_id '{body.person_id}'.",
            )
        if not person.is_active or person.source not in employment.VERIFIED_PERSON_SOURCES:
            raise HTTPException(
                status_code=400,
                detail="Only active LDAP directory identities may be linked to an account.",
            )
        user.person_id = person.id
    elif user.person_id:
        person = await session.get(Person, user.person_id)

    await session.commit()
    await session.refresh(user)
    after = {
        "roles": list(user.roles or []),
        "department_ids": list(user.department_ids or []),
        "branch_ids": list(user.branch_ids or []),
        "province_ids": list(user.province_ids or []),
        "is_active": bool(user.is_active),
    }
    changed = sorted(field for field, before in prior.items() if before != after[field])
    await _audit_privilege_change(
        session,
        request,
        claims,
        action="admin.user.update",
        target=user.email,
        detail={
            "user_id": user.id,
            "before": prior,
            "after": after,
            "changed_fields": changed,
            "password_reset": bool(body.password),
        },
    )
    return _to_out(user, person)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    user = await _get_user_or_404(session, user_id)
    if user.id == claims.sub:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    if not can_manage(
        claims,
        list(user.roles or []),
        list(user.department_ids or []),
        list(user.branch_ids or []),
        list(user.province_ids or []),
    ):
        raise HTTPException(
            status_code=403,
            detail="You may only delete users within your delegated scope.",
        )
    await session.delete(user)
    await session.commit()
    await _audit_privilege_change(
        session,
        request,
        claims,
        action="admin.user.delete",
        target=user.email,
        detail={
            "user_id": user.id,
            "roles": list(user.roles or []),
            "department_ids": list(user.department_ids or []),
            "branch_ids": list(user.branch_ids or []),
            "province_ids": list(user.province_ids or []),
        },
    )
    return {"status": "deleted", "id": user_id}


@router.get("/ipinfo")
async def get_ip_info(
    session: AsyncSession = Depends(get_session),
):
    """Proxy endpoint for ipapi.co JSON data (CORS-safe)."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://ipapi.co/json", timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"ipapi returned {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/persons")
async def list_persons(
    request: Request,
    q: str | None = None,
    source: str | None = None,
    employment_status: str | None = None,
    page: int = Query(default=1, ge=1, le=10000),
    size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    """Browse LDAP-sourced person records available for user provisioning."""
    size = min(max(size, 1), 200)
    page = max(page, 1)
    filters = []
    if q:
        if "\x00" in q or "%00" in q:
            raise HTTPException(status_code=400, detail="Invalid character in search query")
        like = f"%{q.strip().lower()}%"
        filters.append(
            Person.employee_number.ilike(like)
            | Person.surname.ilike(like)
            | Person.initials.ilike(like)
            | Person.email.ilike(like)
            | Person.job_title.ilike(like)
        )
    if source:
        if "\x00" in source or "%00" in source:
            raise HTTPException(status_code=400, detail="Invalid character in source parameter")
        filters.append(Person.source == source.strip())
    if employment_status:
        if "\x00" in employment_status or "%00" in employment_status:
            raise HTTPException(status_code=400, detail="Invalid character in employment_status parameter")
        filters.append(Person.employment_status == employment_status.strip())
    scope = tenant_filter(claims, Person)
    if scope is not None:
        filters.append(scope)
    base = select(Person).where(*filters)
    total = (
        await session.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()
    rows = (
        await session.execute(
            base.order_by(Person.surname, Person.initials)
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()
    # Person records carry special personal information (SA ID numbers,
    # clearance levels, work phones). Record who read them and how many, so a
    # bulk browse is distinguishable from a single-record lookup.
    await _audit_admin_read(session, request, claims, "data.read.persons", len(rows), total)
    return {
        "items": [
            apply_person_policy(
                {
                    "id": p.id,
                    "employee_number": p.employee_number,
                    "email": p.email,
                    "title": p.title,
                    "initials": p.initials,
                    "surname": p.surname,
                    "display_name": p.display_name,
                    "id_number": p.id_number,
                    "job_title": p.job_title,
                    "org_unit": p.org_unit,
                    "department_id": p.department_id,
                    "department_name": DEPARTMENTS.get(p.department_id),
                    "branch_id": p.branch_id,
                    "branch_name": BRANCHES[p.branch_id][0] if p.branch_id in BRANCHES else None,
                    "manager_id": p.manager_id,
                    "manager_name": p.manager_name,
                    "work_phone": p.work_phone,
                    "location": p.location,
                    "employment_status": p.employment_status,
                    "clearance_level": p.clearance_level,
                    "source": p.source,
                    "is_active": p.is_active,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
            )
            for p in rows
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


async def _record_employment_identifier(
    session: AsyncSession,
    person: Person,
    *,
    scheme: str,
    value: str,
    source_system: str,
) -> None:
    """Attach a validated LDAP identifier to a person, idempotently.

    Re-importing the same directory entry reuses its existing row. An
    identifier already bound to another person is rejected rather than
    silently reassigned.
    """
    validated = employment.validate(scheme, value)
    await session.flush()  # person.id must exist before the FK is written

    existing = (
        await session.execute(
            select(EmploymentIdentifier).where(
                EmploymentIdentifier.scheme == scheme,
                EmploymentIdentifier.value == validated,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.person_id == person.id:
            existing.source_system = source_system
            return
        raise IdentifierSchemeError(
            f"{scheme} {validated!r} is already bound to a different person "
            f"({existing.person_id}); refusing to reassign"
        )

    session.add(
        EmploymentIdentifier(
            person_id=person.id,
            scheme=scheme,
            value=validated,
            source_system=source_system,
        )
    )


async def resolve_person_by_identifier(
    session: AsyncSession, scheme: str, value: str
) -> Person | None:
    """Resolve an LDAP directory identifier to a person record.

    Used by account provisioning and directory reconciliation. Returns
    ``None`` rather than raising for an unknown identifier so callers can
    distinguish "no such employee" from "malformed input"; use
    ``employment.validate`` first when the distinction matters.
    """
    validated = employment.validate(scheme, value)
    row = (
        await session.execute(
            select(EmploymentIdentifier).where(
                EmploymentIdentifier.scheme == scheme,
                EmploymentIdentifier.value == validated,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return await session.get(Person, row.person_id)


@router.get("/persons/by-identifier")
async def find_person_by_identifier(
    scheme: str,
    value: str,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    """Look up a person record by its LDAP directory identifier.

    The identifier is validated against the LDAP account-name format before
    resolving its linked person record.
    """
    try:
        employment.validate(scheme, value)
    except IdentifierSchemeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    person = await resolve_person_by_identifier(session, scheme, value)
    if person is None:
        return {"found": False, "scheme": scheme, "value": value}

    identifiers = (
        await session.execute(
            select(EmploymentIdentifier).where(
                EmploymentIdentifier.person_id == person.id
            )
        )
    ).scalars().all()

    return {
        "found": True,
        "scheme": scheme,
        "value": value,
        "person": apply_person_policy(
            {
                "id": person.id,
                "employee_number": person.employee_number,
                "email": person.email,
                "display_name": person.display_name,
                "id_number": person.id_number,
                "work_phone": person.work_phone,
                "clearance_level": person.clearance_level,
                "department_id": person.department_id,
                "branch_id": person.branch_id,
                "employment_status": person.employment_status,
                "is_active": person.is_active,
            }
        ),
        "identifiers": [
            {"scheme": i.scheme, "value": i.value, "source_system": i.source_system}
            for i in identifiers
        ],
    }


@router.get("/employment/schemes")
async def list_identifier_schemes(
    claims = Depends(require_roles("admin_read")),
):
    """The identifier schemes the platform recognises, with their validation rules.

    Surfaced so an operator provisioning an account can see which identifier is
    expected rather than discovering the constraint through a 400.
    """
    return {
        "schemes": [
            {
                "id": s.id,
                "label": s.label,
                "authority": s.authority,
                "identifies": s.identifies,
                "pattern_description": s.pattern_description,
                "national": False,
                "notes": s.notes,
            }
            for s in employment.SCHEMES.values()
        ],
        "note": (
            "The SA identity number identifies a person, not an employment, and "
            "is deliberately not an account key. See app/employment.py."
        ),
    }


# ============================================================================
# Enterprise LDAP / Active Directory (Customizable to any client)
# ============================================================================

class LDAPConfigUpdatePayload(BaseModel):
    enabled: bool | None = None
    server_url: str | None = None
    use_ssl: bool | None = None
    start_tls: bool | None = None
    timeout_seconds: int | None = None
    bind_dn: str | None = None
    bind_password: str | None = None
    base_dn: str | None = None
    user_search_base: str | None = None
    user_search_filter: str | None = None
    user_login_filter: str | None = None
    group_search_base: str | None = None
    client_name: str | None = None
    preset_profile: str | None = None
    attribute_mapping: dict[str, str] | None = None
    role_mapping: dict[str, list[str]] | None = None
    mock_mode: bool | None = None


class LDAPTestPayload(BaseModel):
    server_url: str | None = None
    bind_dn: str | None = None
    bind_password: str | None = None
    base_dn: str | None = None
    use_ssl: bool | None = None
    start_tls: bool | None = None
    timeout_seconds: int | None = None
    mock_mode: bool | None = None


class DirectoryImportPayload(BaseModel):
    username_or_code: str
    create_user_account: bool = False
    assigned_roles: list[str] | None = None
    department_id: str | None = None
    branch_id: str | None = None
    tenant_id: str | None = None


class TierRoleMappingPayload(BaseModel):
    tier_mappings: list[TierRoleAssignment] = Field(default_factory=list)


@router.get("/directory/tenants")
async def list_directory_tenants(
    claims = Depends(require_roles("admin_read")),
):
    """List all configured tenant LDAP directories across the platform."""
    return {"tenants": tenant_ldap_registry.list_tenants()}


@router.get("/directory/tenants/{tenant_id}/tier-mappings")
async def get_tenant_tier_mappings(
    tenant_id: str,
    claims = Depends(require_roles("admin_read")),
):
    """Retrieve directory group-to-role and tier mappings for a specific client tenant."""
    cfg = tenant_ldap_registry.get_tenant_config(tenant_id)
    return {
        "tenant_id": tenant_id,
        "tenant_name": cfg.tenant_name,
        "tier_mappings": [m.model_dump() for m in cfg.tier_role_mappings],
    }


@router.put("/directory/tenants/{tenant_id}/tier-mappings")
async def update_tenant_tier_mappings(
    tenant_id: str,
    payload: TierRoleMappingPayload,
    claims = Depends(require_roles("admin_write")),
):
    """Update directory group-to-role and tier mappings for a specific client tenant."""
    cfg = tenant_ldap_registry.get_tenant_config(tenant_id)
    cfg.tier_role_mappings = payload.tier_mappings

    # Also update role_mapping for fast lookup
    new_role_map = dict(cfg.role_mapping)
    for m in payload.tier_mappings:
        if m.group_name and m.roles:
            new_role_map[m.group_name] = m.roles
    cfg.role_mapping = new_role_map

    tenant_ldap_registry.update_tenant_config(tenant_id, cfg)
    return {
        "status": "updated",
        "tenant_id": tenant_id,
        "tier_mappings": [m.model_dump() for m in cfg.tier_role_mappings],
    }


CLIENT_ORGANIZATION_STATUSES = ["draft", "active", "inactive", "suspended", "archived"]


class ClientOrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(..., min_length=2, max_length=128)
    description: str = Field(default="", max_length=4000)
    client_type: str = Field(..., min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    deployment_model: str = Field(..., pattern=r"^(saas|on_premises)$")
    primary_contact_name: str = Field(..., min_length=2, max_length=128)
    primary_contact_email: str = Field(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    superadmin_name: str = Field(..., min_length=2, max_length=128)
    superadmin_email: str = Field(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ClientOrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=128)
    description: str | None = Field(default=None, max_length=4000)
    client_type: str | None = Field(default=None, min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    deployment_model: str | None = Field(default=None, pattern=r"^(saas|on_premises)$")
    status: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9 _-]*$")
    primary_contact_name: str | None = Field(default=None, min_length=2, max_length=128)
    primary_contact_email: str | None = Field(default=None, min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    superadmin_name: str | None = Field(default=None, min_length=2, max_length=128)
    superadmin_email: str | None = Field(default=None, min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _client_organization_out(client: ClientOrganization) -> dict[str, Any]:
    return {
        "id": client.id,
        "identifier": client.identifier,
        "name": client.name,
        "description": client.description,
        "client_type": client.client_type,
        "deployment_model": client.deployment_model,
        "status": client.status,
        "status_options": client.status_options or CLIENT_ORGANIZATION_STATUSES,
        "primary_contact_name": client.primary_contact_name,
        "primary_contact_email": client.primary_contact_email,
        "superadmin_name": client.superadmin_name,
        "superadmin_email": client.superadmin_email,
        "access_setup_status": client.access_setup_status,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }


@router.get("/client-organizations")
async def list_client_organizations(
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_hosi_provider),
):
    result = await session.execute(
        select(ClientOrganization).order_by(ClientOrganization.created_at.desc())
    )
    return {"items": [_client_organization_out(item) for item in result.scalars().all()]}


@router.post("/client-organizations", status_code=201)
async def create_client_organization(
    payload: ClientOrganizationCreate,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_hosi_provider),
):
    client = ClientOrganization(
        id=str(uuid.uuid4()),
        identifier=payload.identifier,
        name=payload.name,
        description=payload.description,
        client_type=payload.client_type,
        deployment_model=payload.deployment_model,
        status="draft",
        status_options=CLIENT_ORGANIZATION_STATUSES.copy(),
        primary_contact_name=payload.primary_contact_name,
        primary_contact_email=payload.primary_contact_email.lower(),
        superadmin_name=payload.superadmin_name,
        superadmin_email=payload.superadmin_email.lower(),
        access_setup_status="pending_superadmin_setup",
    )
    session.add(client)
    try:
        await session.commit()
        await session.refresh(client)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A client profile with this identifier already exists") from exc
    logger.info("Provider created client organization %s", client.id)
    return _client_organization_out(client)


@router.patch("/client-organizations/{client_id}")
async def update_client_organization(
    client_id: str,
    payload: ClientOrganizationUpdate,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_hosi_provider),
):
    client = await session.get(ClientOrganization, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client profile not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            setattr(client, field, value.lower() if field.endswith("_email") else value)
    if client.status not in (client.status_options or CLIENT_ORGANIZATION_STATUSES):
        client.status_options = [*(client.status_options or CLIENT_ORGANIZATION_STATUSES), client.status]

    await session.commit()
    await session.refresh(client)
    logger.info("Provider updated client organization %s", client.id)
    return _client_organization_out(client)


@router.post("/client-organizations/{client_id}/superadmin-account", status_code=201)
async def provision_client_superadmin(
    client_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_hosi_provider),
):
    client = await session.get(ClientOrganization, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client profile not found")
    if client.status != "active":
        raise HTTPException(status_code=409, detail="Activate the client profile before provisioning its superadmin")

    display_name = (client.superadmin_name or "").strip()
    email = (client.superadmin_email or "").strip().lower()
    if not display_name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(
            status_code=409,
            detail="Add a valid designated superadmin name and email to the client profile before provisioning.",
        )

    existing_user = (
        await session.execute(select(User).where(func.lower(User.email) == email))
    ).scalars().first()
    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="This email already has a platform account. Manage that account instead of provisioning another.",
        )

    temporary_password = secrets.token_urlsafe(18)
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(temporary_password),
        display_name=display_name,
        roles=["client-admin"],
        department_ids=[],
        branch_ids=[],
        province_ids=[],
        is_active=True,
    )
    session.add(user)
    client.superadmin_email = email
    client.access_setup_status = "pending_client_workspace"

    try:
        await session.commit()
        await session.refresh(client)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not create the superadmin account; try again") from exc

    email_status = await _email_client_superadmin_credentials(
        email=email,
        client_name=client.name,
        temporary_password=temporary_password,
    )

    await _audit_privilege_change(
        session,
        request,
        claims,
        action="admin.client_superadmin.provision",
        target=client.id,
        detail={"client_identifier": client.identifier, "email": email},
    )
    logger.info("Provisioned client superadmin account for client %s", client.id)
    return {
        "status": "credential_created",
        "email": email,
        "temporary_password": temporary_password,
        "email_status": email_status,
        "client": _client_organization_out(client),
    }


async def _email_client_superadmin_credentials(
    *,
    email: str,
    client_name: str,
    temporary_password: str,
) -> str:
    try:
        await asyncio.to_thread(
            send_client_superadmin_credentials,
            email=email,
            client_name=client_name,
            temporary_password=temporary_password,
        )
    except InvitationEmailConfigurationError as exc:
        logger.warning("SMTP is not configured for client superadmin credentials: %s", exc)
        return "not_configured"
    except InvitationEmailDeliveryError as exc:
        logger.warning("Could not email client superadmin credentials: %s", exc)
        return "delivery_failed"
    return "sent"


@router.post("/client-organizations/{client_id}/superadmin-account/password")
async def rotate_client_superadmin_password(
    client_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_hosi_provider),
):
    client = await session.get(ClientOrganization, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client profile not found")
    if client.status != "active":
        raise HTTPException(status_code=409, detail="Activate the client profile before resetting its superadmin password")

    display_name = (client.superadmin_name or "").strip()
    email = (client.superadmin_email or "").strip().lower()
    if not display_name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(
            status_code=409,
            detail="Add a valid designated superadmin name and email to the client profile before resetting its password.",
        )

    user = (
        await session.execute(select(User).where(func.lower(User.email) == email))
    ).scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="No superadmin account exists for this client profile")
    if user.roles != ["client-admin"] or user.person_id is not None:
        raise HTTPException(
            status_code=409,
            detail="This email is not linked to a client superadmin account managed by this portal.",
        )
    if not user.is_active:
        raise HTTPException(status_code=409, detail="The client superadmin account is disabled.")

    temporary_password = secrets.token_urlsafe(18)
    user.password_hash = hash_password(temporary_password)
    user.display_name = display_name
    try:
        await session.commit()
        await session.refresh(client)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Could not reset the superadmin password; try again") from exc

    email_status = await _email_client_superadmin_credentials(
        email=email,
        client_name=client.name,
        temporary_password=temporary_password,
    )
    await _audit_privilege_change(
        session,
        request,
        claims,
        action="admin.client_superadmin.password_reset",
        target=client.id,
        detail={"client_identifier": client.identifier, "email": email},
    )
    logger.info("Reset client superadmin password for client %s", client.id)
    return {
        "status": "credential_rotated",
        "email": email,
        "temporary_password": temporary_password,
        "email_status": email_status,
        "client": _client_organization_out(client),
    }


class TenantProfileCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    description: str = Field(default="")
    client_type: str = Field(default="enterprise")


class TenantProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    client_type: str | None = None


@router.get("/tenant-profiles")
async def list_tenant_profiles(
    claims = Depends(require_roles("admin_read")),
):
    """List available tenant profiles (SITA Government, Global Enterprise, etc.)."""
    return {
        "profiles": tenant_registry.list_profiles(),
        "active_profile": tenant_registry.get_active().id,
    }


@router.post("/tenant-profiles", status_code=201)
async def create_tenant_profile(
    payload: TenantProfileCreate,
    claims = Depends(require_roles("admin_write")),
):
    """Developer / Operator endpoint to provision a new Client Tenant profile."""
    from app.tenant_profiles.template import build_profile
    if tenant_registry.get(payload.id):
        raise HTTPException(status_code=400, detail=f"Tenant profile '{payload.id}' already exists")
    profile = build_profile(client_id=payload.id, client_name=payload.name)
    profile.description = payload.description or f"Custom profile for {payload.name}"
    profile.client_type = payload.client_type or "enterprise"
    tenant_registry.register(profile)
    return {
        "status": "created",
        "id": profile.id,
        "name": profile.name,
        "client_type": profile.client_type,
    }


@router.put("/tenant-profiles/{profile_id}")
async def update_tenant_profile(
    profile_id: str,
    payload: TenantProfileUpdate,
    claims = Depends(require_roles("admin_write")),
):
    """Developer / Operator endpoint to edit an existing Client Tenant profile."""
    profile = tenant_registry.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Tenant profile '{profile_id}' not found")
    if payload.name:
        profile.name = payload.name
    if payload.description is not None:
        profile.description = payload.description
    if payload.client_type:
        profile.client_type = payload.client_type
    return {
        "status": "updated",
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "client_type": profile.client_type,
    }


@router.delete("/tenant-profiles/{profile_id}")
async def delete_tenant_profile(
    profile_id: str,
    claims = Depends(require_roles("admin_write")),
):
    """Developer / Operator endpoint to delete / unregister a Client Tenant profile."""
    profile = tenant_registry.get(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Tenant profile '{profile_id}' not found")
    tenant_registry.unregister(profile_id)
    return {
        "status": "deleted",
        "id": profile_id,
        "detail": f"Tenant profile '{profile_id}' has been permanently removed",
    }


@router.post("/tenant-profiles/{profile_id}/activate")
async def activate_tenant_profile(
    profile_id: str,
    claims = Depends(require_roles("admin_write")),
):
    """Switch active organizational tenant profile (customizes hierarchy and tier labels)."""
    try:
        profile = tenant_registry.set_active(profile_id)
        return {
            "status": "activated",
            "active_profile": profile.id,
            "name": profile.name,
            "hierarchy_levels": [
                {"level": l.level, "name": l.name, "label": l.label, "plural_label": l.plural_label}
                for l in profile.hierarchy_levels
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/directory/config")
async def get_directory_config(
    tenant_id: str | None = Query(default=None, description="Optional tenant/client identifier"),
    claims = Depends(require_roles("admin_read")),
):
    """Retrieve the enterprise LDAP/Directory configuration for this tenant or default."""
    conn = tenant_ldap_registry.get_connector(tenant_id)
    return conn.config.masked()


@router.put("/directory/config")
async def update_directory_config(
    payload: LDAPConfigUpdatePayload,
    tenant_id: str | None = Query(default=None, description="Optional tenant/client identifier"),
    claims = Depends(require_roles("admin_write")),
):
    """Update runtime LDAP/Directory settings customized for a specific client tenant."""
    target_tenant = tenant_id or "default"
    current_conn = tenant_ldap_registry.get_connector(target_tenant)
    current = current_conn.config.model_dump()
    updates = payload.model_dump(exclude_unset=True)
    current.update(updates)

    # Update tenant registry
    updated_cfg = tenant_ldap_registry.update_tenant_config(target_tenant, current)

    # Also update global singleton for backward compatibility
    ldap_connector.update_config(updated_cfg)

    return {
        "status": "updated",
        "tenant_id": target_tenant,
        "client_name": updated_cfg.client_name,
        "config": updated_cfg.masked(),
    }
@router.post("/directory/preset/{preset_name}")
async def apply_directory_preset(
    preset_name: str,
    tenant_id: str | None = Query(default=None, description="Optional tenant/client identifier"),
    claims = Depends(require_roles("admin_write")),
):
    """Apply an enterprise directory preset (active_directory, openldap, or freeipa)."""
    target_tenant = tenant_id or "default"
    conn = tenant_ldap_registry.get_connector(target_tenant)
    try:
        updated = conn.apply_preset(preset_name.lower().strip())
        tenant_ldap_registry.update_tenant_config(target_tenant, updated)
        ldap_connector.apply_preset(preset_name.lower().strip())
        return {
            "status": "preset_applied",
            "tenant_id": target_tenant,
            "preset": preset_name,
            "client_name": updated.client_name,
            "config": updated.masked(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/directory/test")
async def test_directory_connection(
    payload: LDAPTestPayload | None = None,
    tenant_id: str | None = Query(default=None, description="Optional tenant/client identifier"),
    claims = Depends(require_roles("admin_read")),
):
    """Test LDAP connectivity and authentication with diagnostics for a specific tenant."""
    conn = tenant_ldap_registry.get_connector(tenant_id)
    test_cfg = None
    if payload:
        data = conn.config.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        test_cfg = LDAPConfig(**data)
    result = await conn.test_connection(test_cfg)
    result["tenant_id"] = tenant_id or "default"
    return result


@router.get("/directory/search")
async def search_directory_users(
    q: str | None = Query(default=None, description="Search term (username, surname, position, email, or code)"),
    department_id: str | None = Query(default=None, description="Filter by department"),
    tenant_id: str | None = Query(default=None, description="Optional tenant/client identifier"),
    limit: int = Query(default=50, ge=1, le=200),
    claims = Depends(require_roles("admin_read")),
):
    """Search users from the configured client LDAP / Active Directory."""
    conn = tenant_ldap_registry.get_connector(tenant_id or department_id)
    users = await conn.search_users(query=q or "", department_id=department_id, limit=limit)
    return {
        "tenant_id": tenant_id or "default",
        "client_name": conn.config.client_name,
        "total": len(users),
        "items": [u.to_dict() for u in users],
    }


@router.post("/directory/import")
async def import_directory_user(
    payload: DirectoryImportPayload,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    """Import a user from the enterprise LDAP directory into platform Person and optional User account."""
    conn = tenant_ldap_registry.get_connector(payload.tenant_id or payload.department_id)
    code = payload.username_or_code.strip()
    dir_user = await conn.lookup_by_code(code)
    if dir_user is None:
        raise HTTPException(status_code=404, detail=f"User '{code}' not found in client LDAP directory.")

    # Find or create Person
    person = (
        await session.execute(
            select(Person).where(Person.employee_number == dir_user.employee_code)
        )
    ).scalar_one_or_none()

    dept = payload.department_id or dir_user.department_id
    branch = payload.branch_id or dir_user.branch_id

    if person is None:
        person = Person(
            id=str(uuid.uuid4()),
            employee_number=dir_user.employee_code,
            surname=dir_user.surname,
            initials=dir_user.initials,
            display_name=dir_user.display_name,
            job_title=dir_user.position,
            email=dir_user.email,
            department_id=dept,
            branch_id=branch,
            source="ldap",
            is_active=True,
        )
        session.add(person)
        await session.flush()
        await _record_employment_identifier(
            session,
            person,
            scheme=SCHEME_LDAP,
            value=dir_user.employee_code or dir_user.username,
            source_system="ldap",
        )
    else:
        person.surname = dir_user.surname
        person.job_title = dir_user.position
        person.initials = dir_user.initials
        person.display_name = dir_user.display_name or person.display_name
        person.source = "ldap"
        if dir_user.email:
            person.email = dir_user.email
        if dept:
            person.department_id = dept
        if branch:
            person.branch_id = branch
        await session.flush()

    user_out = None
    if payload.create_user_account and dir_user.email:
        # Check if user account already exists
        user = (
            await session.execute(select(User).where(User.email == dir_user.email.lower().strip()))
        ).scalar_one_or_none()
        roles_to_assign = payload.assigned_roles or dir_user.suggested_roles or ["soc"]
        if user is None:
            user = User(
                id=str(uuid.uuid4()),
                email=dir_user.email.lower().strip(),
                password_hash=hash_password(f"LdapSync#{uuid.uuid4().hex[:8]}!"),
                display_name=dir_user.display_name,
                roles=roles_to_assign,
                department_ids=[dept] if dept else [],
                branch_ids=[branch] if branch else [],
                province_ids=[],
                person_id=person.id,
                is_active=True,
            )
            session.add(user)
        else:
            user.display_name = dir_user.display_name
            user.person_id = person.id
            if payload.assigned_roles:
                user.roles = payload.assigned_roles
            if dept:
                user.department_ids = [dept]
            if branch:
                user.branch_ids = [branch]
        await session.flush()
        user_out = {"id": user.id, "email": user.email, "roles": user.roles}

    await session.commit()
    return {
        "status": "imported",
        "person_id": person.id,
        "employee_code": person.employee_number,
        "surname": person.surname,
        "position": person.job_title,
        "department_id": person.department_id,
        "branch_id": person.branch_id,
        "email": person.email,
        "source": "ldap",
        "user_account": user_out,
    }
