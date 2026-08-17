from datetime import datetime
from math import ceil
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    ROLES_HIERARCHY,
    can_manage,
    require_roles,
    scope_covers,
    tenant_filter,
)
from app.db import get_session
from app.ingestion.dlq import DLQManager
from app.models.connector_status import ConnectorHealth
from app.models.dlq import RejectedRecord
from app.models.person import Person
from app.models.user import User
from app.security import hash_password
from app.tenant import BRANCHES, DEPARTMENTS, PROVINCES

router = APIRouter(tags=["admin"])

VALID_ROLES = set(ROLES_HIERARCHY.keys())


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["soc"])
    department_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    province_ids: list[str] = Field(default_factory=list)
    # Accounts can only be provisioned for HR-provisioned employees. There is
    # no path to create an external/non-employee user.
    person_id: str


class UserUpdate(BaseModel):
    display_name: str | None = None
    roles: list[str] | None = None
    department_ids: list[str] | None = None
    branch_ids: list[str] | None = None
    province_ids: list[str] | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    person_id: str | None = None


class HRSyncRecord(BaseModel):
    employee_number: str
    email: str | None = None
    id_number: str | None = None
    title: str | None = None
    initials: str | None = None
    surname: str | None = None
    display_name: str | None = None
    job_title: str | None = None
    org_unit: str | None = None
    department_id: str | None = None
    branch_id: str | None = None
    manager_id: str | None = None
    manager_name: str | None = None
    work_phone: str | None = None
    location: str | None = None
    employment_status: str = "active"
    clearance_level: str | None = None


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
        "person": {
            "employee_number": person.employee_number,
            "title": person.title,
            "initials": person.initials,
            "surname": person.surname,
            "display_name": person.display_name,
            "id_number": _mask_id_number(person.id_number),
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
        if person is not None
        else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _mask_id_number(id_number: str | None) -> str | None:
    if not id_number:
        return None
    if len(id_number) <= 4:
        return "****"
    return "*" * (len(id_number) - 4) + id_number[-4:]


def _validate_departments(department_ids: list[str]) -> None:
    invalid = [d for d in department_ids if d not in DEPARTMENTS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown department(s): {sorted(invalid)}. Valid: {sorted(DEPARTMENTS)}",
        )


def _validate_provinces(province_ids: list[str]) -> None:
    invalid = [p for p in province_ids if p not in PROVINCES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown province(s): {sorted(invalid)}. Valid: {sorted(PROVINCES)}",
        )


def _validate_branches(branch_ids: list[str], department_ids: list[str]) -> None:
    for branch in branch_ids:
        if branch not in BRANCHES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown branch '{branch}'. Valid: {sorted(BRANCHES)}",
            )
        parent = BRANCHES[branch][1]
        if parent not in department_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Branch '{branch}' belongs to department '{parent}', "
                    f"which is not in the user's assigned departments: {sorted(department_ids)}"
                ),
            )


def _validate_scope(roles: list[str], department_ids: list[str], branch_ids: list[str], province_ids: list[str] | None = None) -> None:
    from app.tenant import DEPARTMENT_ROLES, PROVINCIAL_ROLES
    has_department_role = bool(set(roles) & DEPARTMENT_ROLES)
    has_scope = bool(department_ids or province_ids)
    if has_department_role and not has_scope:
        raise HTTPException(
            status_code=400,
            detail=(
                "Department-scoped roles (soc/appsec/dbsec/dept-admin/branch-admin/"
                "province-soc-lead/province-dept-admin/local-appsec) require at "
                "least one assigned department or province."
            ),
        )
    if set(roles) & PROVINCIAL_ROLES and not province_ids and not department_ids:
        raise HTTPException(
            status_code=400,
            detail="Provincial roles (province-soc-lead/province-dept-admin/local-appsec) require at least one assigned province or department.",
        )
    if "branch-admin" in roles and not branch_ids:
        raise HTTPException(
            status_code=400,
            detail="Role 'branch-admin' requires at least one assigned branch.",
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
    return {
        "items": [
            {"id": dept_id, "name": name}
            for dept_id, name in DEPARTMENTS.items()
        ]
    }


@router.get("/branches")
async def list_branches(
    department_id: str | None = None,
    claims = Depends(require_roles("admin_read")),
):
    items = [
        {
            "id": branch_id,
            "name": name,
            "department_id": parent,
            "department_name": DEPARTMENTS.get(parent),
        }
        for branch_id, (name, parent) in BRANCHES.items()
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
    return {
        "items": items,
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
    """
    Create a new user with strict tenancy and Role-Based Access Control (RBAC) validation.

    This endpoint integrates the full SITA tenancy model (Provinces, Departments, Branches) 
    and enforces **Delegated Authority**. The caller may only create users whose roles and 
    scope fall strictly within their own administrative boundaries.

    ### Delegated Authority (Hierarchical Tiers)
    - **Tier 5 (Platform Operator / creator):** Role `operator`. National scope. Can create the SITA superuser (`admin`) and peer `operator` accounts only (rotation). Nothing else.
    - **Tier 4 (SITA Superuser):** Role `admin`. National scope. Can create `transversal-admin`, `exec`, `compliance`, `sre`, `dept-admin`, `province-dept-admin`, `branch-admin` and the operational roles — never a peer `admin` or an `operator`.
    - **Tier 3 (Transversal Admin):** Role `transversal-admin`. Assigned scope (may be national). Can create `transversal-admin` (peer), `exec`, `compliance`, `sre`, `dept-admin`, `province-dept-admin`, `branch-admin` and the operational roles within its scope.
    - **Tier 2 (Department Admin):** Role `dept-admin` / `province-dept-admin`. Department/province scope. Can create `branch-admin` (dept-admin only) and the operational roles within their assigned departments/province.
    - **Tier 1 (Branch Admin):** Role `branch-admin`. Branch scope. Can create the operational roles *only* within their assigned branch.
    - **Tier 0 (Service Ops):** Role `sre`. Estate-wide scope, operational roles only (`soc`, `appsec`, `dbsec`, `province-soc-lead`, `local-appsec`) — no admin tiers.

    ### Payload Requirements
    - **person_id**: Required. Must reference an HR-provisioned employee record
      (look it up via `GET /admin/persons`). Accounts can only be created for
      employees imported from the HR system — there is no path for external or
      non-employee users.
    - **email**: Must match the HR employee's registered email.
    - **roles**: Must contain valid SITA roles.
    - **department_ids**: Must contain valid department slugs (e.g., `home-affairs-digital`) if the role requires department scoping.
    - **branch_ids**: If provided, must belong to the specified department.
    
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

    person = await session.get(Person, body.person_id)
    if person is None:
        raise HTTPException(
            status_code=400,
            detail=f"No HR employee record found for person_id '{body.person_id}'. "
            "Use /admin/persons to look up an HR-provisioned employee.",
        )
    person_email = (person.email or "").lower().strip()
    if not person_email:
        raise HTTPException(
            status_code=400,
            detail="HR record has no registered email; an account cannot be provisioned.",
        )
    if email != person_email:
        raise HTTPException(
            status_code=400,
            detail="Account email must match the HR employee's registered email.",
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
    return _to_out(user, person)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
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
                detail=f"No HR employee record found for person_id '{body.person_id}'.",
            )
        user.person_id = person.id
    elif user.person_id:
        person = await session.get(Person, user.person_id)

    await session.commit()
    await session.refresh(user)
    return _to_out(user, person)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
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
    return {"status": "deleted", "id": user_id}


@router.get("/persons")
async def list_persons(
    q: str | None = None,
    source: str | None = None,
    employment_status: str | None = None,
    page: int = 1,
    size: int = 50,
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    """Browse HR-provisioned person records (the only identity source for creating user accounts)."""
    size = min(max(size, 1), 200)
    page = max(page, 1)
    filters = []
    if q:
        like = f"%{q.lower()}%"
        filters.append(
            Person.employee_number.ilike(like)
            | Person.surname.ilike(like)
            | Person.initials.ilike(like)
            | Person.email.ilike(like)
            | Person.job_title.ilike(like)
        )
    if source:
        filters.append(Person.source == source)
    if employment_status:
        filters.append(Person.employment_status == employment_status)
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
    return {
        "items": [
            {
                "id": p.id,
                "employee_number": p.employee_number,
                "email": p.email,
                "title": p.title,
                "initials": p.initials,
                "surname": p.surname,
                "display_name": p.display_name,
                "id_number": _mask_id_number(p.id_number),
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
            for p in rows
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if size else 0,
    }


async def _upsert_hr_records(
    session: AsyncSession,
    claims,
    records: list[HRSyncRecord],
) -> dict:
    """Shared HR -> identity.persons pipeline.

    Used by the push endpoint (POST /admin/hr/sync) and the simulated-HR pull
    (POST /admin/hr/sim/sync). Keyed on employee_number. HR sync never modifies
    roles or department/branch scopes — those are set by admins on the linked
    user. Terminated employees are soft-disabled on any linked platform account.
    """
    created = updated = deactivated = skipped = 0
    seen: set[str] = set()
    for record in records:
        emp_no = record.employee_number.strip()
        if not emp_no or emp_no in seen:
            skipped += 1
            continue
        seen.add(emp_no)
        if record.department_id and record.department_id not in DEPARTMENTS:
            skipped += 1
            continue
        if record.branch_id and record.branch_id not in BRANCHES:
            skipped += 1
            continue
        if record.branch_id and (
            record.department_id and BRANCHES[record.branch_id][1] != record.department_id
        ):
            skipped += 1
            continue
        if not scope_covers(
            claims,
            [record.department_id] if record.department_id else [],
            [record.branch_id] if record.branch_id else [],
        ):
            skipped += 1
            continue
        person = (
            await session.execute(
                select(Person).where(Person.employee_number == emp_no)
            )
        ).scalar_one_or_none()
        is_new = person is None
        if is_new:
            person = Person(employee_number=emp_no, source="hr")
            session.add(person)
        person.email = (record.email or "").lower().strip() or None
        person.id_number = record.id_number
        person.title = record.title
        person.initials = record.initials
        person.surname = record.surname
        person.display_name = record.display_name
        person.job_title = record.job_title
        person.org_unit = record.org_unit
        person.department_id = record.department_id
        person.branch_id = record.branch_id
        person.manager_id = record.manager_id
        person.manager_name = record.manager_name
        person.work_phone = record.work_phone
        person.location = record.location
        person.employment_status = record.employment_status
        person.clearance_level = record.clearance_level
        person.is_active = record.employment_status not in ("terminated", "inactive")

        # Soft-disable any linked platform account on termination.
        if not person.is_active and person.id:
            linked = (
                await session.execute(
                    select(User).where(User.person_id == person.id, User.is_active.is_(True))
                )
            ).scalars().all()
            for u in linked:
                u.is_active = False
                deactivated += 1
        if is_new:
            created += 1
        else:
            updated += 1
        await session.flush()
    await session.commit()
    return {
        "status": "ok",
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "skipped": skipped,
    }


@router.post("/hr/sync")
async def hr_sync(
    records: list[HRSyncRecord],
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    """Upsert person records from the HR system (PERSAL/payroll or SCIM feed).

    Keyed on employee_number. HR sync never modifies roles or department/branch
    scopes — those are set by admins on the linked user. Terminated employees
    are soft-disabled on any linked platform account (is_active=False).
    """
    return await _upsert_hr_records(session, claims, records)


# The simulated external HR system lives in a separate `hr` schema and stands
# in for a real PERSAL/SCIM feed so the HR-only provisioning flow can be
# exercised end-to-end. See infrastructure/scripts/init-db.sql (DDL) and
# infrastructure/scripts/seed-hr-system.sql (seed).
_SIM_HR_SELECT = text(
    "SELECT employee_number, id_number, title, initials, first_name, surname,"
    " display_name, email, job_title, org_unit, department_code, branch_code,"
    " manager_employee_number, manager_name, work_phone, location,"
    " employment_status, clearance_level FROM hr.employees"
)


def _sim_row_to_sync(row: Mapping[str, Any]) -> HRSyncRecord:
    """Map one hr.employees row to the canonical HR sync record.

    The simulated HR system stores SITA tenancy slugs in department_code /
    branch_code, so the record maps straight onto department_id / branch_id and
    every validation and tenant-scoping rule in the shared pipeline applies
    unchanged.
    """
    return HRSyncRecord(
        employee_number=row["employee_number"],
        email=row.get("email"),
        id_number=row.get("id_number"),
        title=row.get("title"),
        initials=row.get("initials"),
        surname=row.get("surname"),
        display_name=row.get("display_name") or row.get("first_name"),
        job_title=row.get("job_title"),
        org_unit=row.get("org_unit"),
        department_id=row.get("department_code"),
        branch_id=row.get("branch_code"),
        manager_id=row.get("manager_employee_number"),
        manager_name=row.get("manager_name"),
        work_phone=row.get("work_phone"),
        location=row.get("location"),
        employment_status=row.get("employment_status") or "active",
        clearance_level=row.get("clearance_level"),
    )


@router.get("/hr/sim/employees")
async def sim_hr_employees(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_read")),
):
    """Browse the simulated external HR system's employee master.

    Read-only helper so the simulated feed can be inspected before syncing.
    """
    rows = (await session.execute(_SIM_HR_SELECT)).mappings().all()
    return {
        "system": "simulated-hr",
        "total": len(rows),
        "items": [dict(r) for r in rows],
    }


@router.post("/hr/sim/sync")
async def hr_sim_sync(
    session: AsyncSession = Depends(get_session),
    claims = Depends(require_roles("admin_write")),
):
    """Pull every row from the simulated external HR system and run the exact
    same HR sync pipeline used for live feeds (POST /admin/hr/sync).

    This is how the HR-only account provisioning flow is tested: the pull lands
    records in identity.persons, which then become the only source that user
    accounts can be provisioned from.
    """
    rows = (await session.execute(_SIM_HR_SELECT)).mappings().all()
    records = [_sim_row_to_sync(r) for r in rows]
    result = await _upsert_hr_records(session, claims, records)
    return {"system": "simulated-hr", "pulled": len(records), **result}
