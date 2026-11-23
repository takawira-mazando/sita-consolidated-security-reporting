from __future__ import annotations

import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, verify_token
from app.connectors.tenant_ldap_registry import tenant_ldap_registry
from app.db import get_session
from app.models.client_organization import ClientOrganization
from app.models.tenant_workspace import ClientTenantWorkspace
from app.models.user import User
from app.monitoring.access_audit import record_access

router = APIRouter(prefix="/mssp", tags=["mssp-administration"])

COCKPITS = {
    "exec": "Executive Leadership & Risk Fusion",
    "soc": "SOC Operations & Incident Queue",
    "appsec": "Application Security & Repositories",
    "dbsec": "Database Activity Monitoring",
    "compliance": "Compliance Assurance & Control Evidence",
    "sre": "Platform & Telemetry Health",
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _pluralize_label(label: str) -> str:
    parts = label.split()
    word = parts[-1]
    lower_word = word.lower()
    if len(word) > 1 and lower_word.endswith("y") and lower_word[-2] not in "aeiou":
        plural_suffix = "IES" if word.isupper() else "ies"
        parts[-1] = word[:-1] + plural_suffix
    elif lower_word.endswith(("s", "x", "z", "ch", "sh")):
        plural_suffix = "ES" if word.isupper() else "es"
        parts[-1] = word + plural_suffix
    else:
        plural_suffix = "S" if word.isupper() else "s"
        parts[-1] = word + plural_suffix
    return " ".join(parts)


class HierarchyLevel(StrictModel):
    model_config = ConfigDict(extra="ignore")
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=64)
    plural_label: str | None = Field(default=None, max_length=128)
    parent_key: str | None = Field(default=None, max_length=64)

    @field_validator("label", "plural_label")
    @classmethod
    def require_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Hierarchy labels cannot be blank")
        return value

    @model_validator(mode="after")
    def derive_plural_label(self):
        self.plural_label = _pluralize_label(self.label)
        return self


class OrganizationUnit(StrictModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=128)
    level_key: str = Field(min_length=1, max_length=64)
    parent_id: str | None = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Organization unit names cannot be blank")
        return value


class TenantRole(StrictModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    cockpit_ids: list[str] = Field(default_factory=list)
    scope_level_keys: list[str] = Field(default_factory=list)
    can_manage_members: bool = False

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role names cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_cockpits(self):
        unknown = set(self.cockpit_ids) - set(COCKPITS)
        if unknown:
            raise ValueError(f"Unknown cockpit identifier(s): {', '.join(sorted(unknown))}")
        if len(set(self.cockpit_ids)) != len(self.cockpit_ids):
            raise ValueError("Cockpit identifiers must be unique")
        if len(set(self.scope_level_keys)) != len(self.scope_level_keys):
            raise ValueError("Provisioning levels must be unique")
        return self


class AccessAssignment(StrictModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=128)
    role_ids: list[str] = Field(default_factory=list)
    scope_unit_id: str | None = Field(default=None, max_length=64)
    admin_access: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("display_name")
    @classmethod
    def require_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display names cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_email(self):
        if not _EMAIL.fullmatch(self.email):
            raise ValueError("Enter a valid email address")
        if len(set(self.role_ids)) != len(self.role_ids):
            raise ValueError("Role identifiers in an assignment must be unique")
        if not self.role_ids and not self.admin_access:
            raise ValueError("An assignment must grant administrator access or at least one RBAC role")
        return self


class WorkspaceCreate(StrictModel):
    identifier: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=128)
    root_label: str = Field(default="Organization", min_length=1, max_length=64)
    administration_model: Literal["mssp_managed", "delegated", "shared"] = "mssp_managed"
    hierarchy_levels: list[HierarchyLevel] = Field(default_factory=list)

    @field_validator("name", "root_label")
    @classmethod
    def require_workspace_labels(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tenant names and root labels cannot be blank")
        return value


class WorkspaceConfiguration(StrictModel):
    root_label: str = Field(min_length=1, max_length=64)
    administration_model: Literal["mssp_managed", "delegated", "shared"]
    hierarchy_levels: list[HierarchyLevel] = Field(default_factory=list)
    org_units: list[OrganizationUnit] = Field(default_factory=list)
    roles: list[TenantRole] = Field(default_factory=list)
    assignments: list[AccessAssignment] = Field(default_factory=list)
    status: Literal["active", "inactive", "suspended"] = "active"

    @field_validator("root_label")
    @classmethod
    def require_root_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tenant root labels cannot be blank")
        return value


class TenantMemberAssignment(StrictModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=128)
    role_ids: list[str] = Field(min_length=1)
    scope_unit_id: str | None = Field(default=None, max_length=64)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.fullmatch(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("display_name")
    @classmethod
    def require_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display names cannot be blank")
        return value


class TenantMemberAssignmentsUpdate(StrictModel):
    model_config = ConfigDict(extra="forbid")
    assignments: list[TenantMemberAssignment] = Field(max_length=1000)


def _validate_configuration(config: WorkspaceConfiguration) -> None:
    level_keys = [level.key for level in config.hierarchy_levels]
    if len(set(level_keys)) != len(level_keys):
        raise HTTPException(status_code=422, detail="Hierarchy level keys must be unique")

    level_by_key = {level.key: level for level in config.hierarchy_levels}
    for level in config.hierarchy_levels:
        if level.parent_key is not None and level.parent_key not in level_by_key:
            raise HTTPException(
                status_code=422,
                detail=f"Hierarchy level '{level.label}' refers to an unknown parent level",
            )
        if level.parent_key == level.key:
            raise HTTPException(
                status_code=422,
                detail=f"Hierarchy level '{level.label}' cannot be its own parent",
            )
        ancestry = set()
        current = level
        while current.parent_key is not None:
            if current.key in ancestry:
                raise HTTPException(
                    status_code=422,
                    detail=f"Hierarchy level '{level.label}' creates a circular parent relationship",
                )
            ancestry.add(current.key)
            current = level_by_key.get(current.parent_key)
            if current is None:
                break

    units = {unit.id: unit for unit in config.org_units}
    if len(units) != len(config.org_units):
        raise HTTPException(status_code=422, detail="Organization unit identifiers must be unique")

    level_positions = {key: index for index, key in enumerate(level_keys)}
    for unit in config.org_units:
        position = level_positions.get(unit.level_key)
        if position is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unit '{unit.name}' uses an undefined hierarchy level",
            )
        if position == 0:
            if unit.parent_id is not None:
                raise HTTPException(
                    status_code=422,
                    detail="Units at the first custom level must be children of the tenant root",
                )
            continue
        parent = units.get(unit.parent_id or "")
        if parent is None or level_positions.get(parent.level_key) != position - 1:
            raise HTTPException(
                status_code=422,
                detail=f"Unit '{unit.name}' must have a parent at the preceding hierarchy level",
            )

    role_ids = [role.id for role in config.roles]
    if len(set(role_ids)) != len(role_ids):
        raise HTTPException(status_code=422, detail="Role identifiers must be unique")
    role_names = [role.name.casefold() for role in config.roles]
    if len(set(role_names)) != len(role_names):
        raise HTTPException(status_code=422, detail="Role names must be unique")
    valid_scope_levels = {"root", *level_keys}
    for role in config.roles:
        unknown_levels = set(role.scope_level_keys) - valid_scope_levels
        if unknown_levels:
            raise HTTPException(
                status_code=422,
                detail=f"Role '{role.name}' uses an undefined provisioning level",
            )
    if config.administration_model == "mssp_managed" and any(
        role.can_manage_members for role in config.roles
    ):
        raise HTTPException(
            status_code=422,
            detail="Member administration must remain with the MSSP in MSSP-managed mode",
        )

    assignment_keys: set[tuple[str, str | None]] = set()
    for assignment in config.assignments:
        if assignment.admin_access and config.administration_model == "mssp_managed":
            raise HTTPException(
                status_code=422,
                detail="Administrator access must remain with the organization in MSSP-managed mode",
            )
        key = (assignment.email.casefold(), assignment.scope_unit_id)
        if key in assignment_keys:
            raise HTTPException(
                status_code=422,
                detail="An email address can have only one assignment at each scope",
            )
        assignment_keys.add(key)
        if set(assignment.role_ids) - set(role_ids):
            raise HTTPException(
                status_code=422,
                detail=f"Assignment for '{assignment.email}' refers to an unknown role",
            )
        if assignment.scope_unit_id in units:
            raise HTTPException(
                status_code=422,
                detail="Access assignments must use a hierarchy tier; unit-level scopes are not supported",
            )
        if assignment.scope_unit_id and assignment.scope_unit_id not in units:
            if assignment.scope_unit_id not in level_keys:
                raise HTTPException(
                    status_code=422,
                    detail=f"Assignment for '{assignment.email}' must use a hierarchy tier, not an organization unit",
                )
            scope_level = assignment.scope_unit_id
        else:
            scope_level = (
                units[assignment.scope_unit_id].level_key
                if assignment.scope_unit_id
                else "root"
            )
        assigned_roles = [role for role in config.roles if role.id in assignment.role_ids]
        if any(
            role.scope_level_keys and scope_level not in role.scope_level_keys
            for role in assigned_roles
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Assignment for '{assignment.email}' uses a role not provisioned at this level",
            )


def _workspace_out(
    workspace: ClientTenantWorkspace,
    identity_statuses: dict[str, str] | None = None,
) -> dict:
    identity_statuses = identity_statuses or {}
    return {
        "id": workspace.id,
        "client_organization_id": workspace.client_organization_id,
        "identifier": workspace.identifier,
        "name": workspace.name,
        "status": workspace.status,
        "root_label": workspace.root_label,
        "administration_model": workspace.administration_model,
        "hierarchy_levels": [
            {**level, "plural_label": _pluralize_label(level["label"])}
            for level in (workspace.hierarchy_levels or [])
        ],
        "org_units": workspace.org_units or [],
        "roles": workspace.roles or [],
        "assignments": [
            {
                **assignment,
                "access_status": identity_statuses.get(
                    str(assignment.get("email", "")).lower().strip(),
                    "identity_integration_required",
                ),
            }
            for assignment in (workspace.assignments or [])
        ],
        "created_at": workspace.created_at,
        "updated_at": workspace.updated_at,
    }


def _directory_readiness(client_identifier: str) -> dict[str, str]:
    directory = next(
        (
            item
            for item in tenant_ldap_registry.list_tenants()
            if item["tenant_id"] == client_identifier
        ),
        None,
    )
    if directory is None:
        return {"status": "not_configured", "name": ""}
    if not directory["enabled"]:
        return {"status": "disabled", "name": directory["client_name"]}
    return {"status": "enabled", "name": directory["client_name"]}


async def _assignment_identity_statuses(
    session: AsyncSession,
    emails: set[str],
    directory_enabled: bool,
) -> dict[str, str]:
    if not emails:
        return {}
    user_result = await session.execute(
        select(User.email, User.is_active).where(func.lower(User.email).in_(emails))
    )
    statuses = {
        str(row.email).lower().strip(): (
            "active" if row.is_active else "account_disabled"
        )
        for row in user_result.all()
    }
    for email in emails:
        statuses.setdefault(
            email,
            "pending_first_sign_in" if directory_enabled else "identity_integration_required",
        )
    return statuses


async def _require_mssp_owner(
    session: AsyncSession,
    claims: JWTClaims,
) -> ClientOrganization:
    roles = set(claims.roles)
    if not roles.intersection({"admin", "client-admin"}) or "operator" in roles or not claims.email:
        raise HTTPException(status_code=403, detail="Client administrator access required")

    result = await session.execute(
        select(ClientOrganization).where(
            func.lower(ClientOrganization.superadmin_email) == claims.email.strip().lower(),
            ClientOrganization.status == "active",
        )
    )
    matches = result.scalars().all()
    if len(matches) != 1:
        raise HTTPException(
            status_code=403,
            detail="No single active client profile is linked to this account",
        )
    return matches[0]


async def _get_workspace(
    session: AsyncSession,
    client_id: str,
    workspace_id: str,
) -> ClientTenantWorkspace:
    result = await session.execute(
        select(ClientTenantWorkspace).where(
            ClientTenantWorkspace.id == workspace_id,
            ClientTenantWorkspace.client_organization_id == client_id,
        )
    )
    workspace = result.scalars().first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Tenant workspace not found")
    return workspace


def _assignment_scope_level(
    workspace: ClientTenantWorkspace,
    assignment: dict,
) -> str | None:
    scope_unit_id = assignment.get("scope_unit_id")
    if not scope_unit_id:
        return "root"
    level_keys = {
        level.get("key") for level in (workspace.hierarchy_levels or [])
    }
    if scope_unit_id in level_keys:
        return scope_unit_id
    return None


def _assignment_has_member_admin_role(
    workspace: ClientTenantWorkspace,
    assignment: dict,
) -> bool:
    roles_by_id = {
        role.get("id"): role for role in (workspace.roles or [])
    }
    return any(
        roles_by_id.get(role_id, {}).get("can_manage_members")
        for role_id in assignment.get("role_ids", [])
    )


async def _get_managed_workspace(
    session: AsyncSession,
    claims: JWTClaims,
    workspace_id: str,
) -> tuple[ClientTenantWorkspace, dict, set[str]]:
    if claims.active_tenant_workspace_id != workspace_id:
        raise HTTPException(
            status_code=403,
            detail="Select the assigned tenant workspace before managing its members",
        )
    access = next(
        (
            item
            for item in claims.tenant_workspace_access
            if item.get("workspace_id") == workspace_id
        ),
        None,
    )
    allowed_levels = set(access.get("admin_scope_level_keys") or []) if access else set()

    result = await session.execute(
        select(ClientTenantWorkspace).where(
            ClientTenantWorkspace.id == workspace_id,
            ClientTenantWorkspace.status == "active",
        )
    )
    workspace = result.scalars().first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Tenant workspace not found or inactive")
    valid_scope_levels = {"root"}
    valid_scope_levels.update(
        level.get("key") for level in (workspace.hierarchy_levels or [])
    )
    allowed_levels.intersection_update(valid_scope_levels)
    if not allowed_levels:
        raise HTTPException(status_code=403, detail="Tenant member administration required")
    if workspace.administration_model == "mssp_managed":
        raise HTTPException(status_code=403, detail="Tenant administration is managed by the MSSP")
    return workspace, access, allowed_levels


async def _require_directory_employee(
    client: ClientOrganization,
    email: str,
) -> dict:
    readiness = _directory_readiness(client.identifier)
    if readiness["status"] != "enabled":
        raise HTTPException(
            status_code=409,
            detail="Enable the tenant directory before assigning directory employees",
        )
    connector = tenant_ldap_registry.get_connector(client.identifier)
    users = await connector.search_users(query=email, limit=50)
    employee = next(
        (
            user
            for user in users
            if user.email and user.email.strip().lower() == email.strip().lower()
        ),
        None,
    )
    if employee is None:
        raise HTTPException(
            status_code=422,
            detail=f"No directory employee matches '{email}'",
        )
    return {
        "email": employee.email.strip().lower(),
        "display_name": employee.display_name.strip() or email,
    }


async def _audit_member_change(
    session: AsyncSession,
    request: Request,
    claims: JWTClaims,
    workspace: ClientTenantWorkspace,
    action: str,
) -> None:
    await record_access(
        session,
        action=action,
        actor=claims.email,
        target=workspace.id,
        tenant_scope={
            "tenant_workspace_id": workspace.id,
            "scope_level_keys": sorted(
                next(
                    (
                        item.get("admin_scope_level_keys", [])
                        for item in claims.tenant_workspace_access
                        if item.get("workspace_id") == workspace.id
                    ),
                    [],
                )
            ),
        },
        actor_role=",".join(sorted(claims.roles)),
        detail={"request_path": request.url.path},
        commit=False,
    )


async def _audit_change(
    session: AsyncSession,
    request: Request,
    claims: JWTClaims,
    client: ClientOrganization,
    action: str,
    target: str,
) -> None:
    await record_access(
        session,
        action=action,
        actor=claims.email,
        target=target,
        tenant_scope={"client_organization_id": client.id},
        actor_role=",".join(sorted(claims.roles)),
        detail={
            "client_identifier": client.identifier,
            "request_path": request.url.path,
        },
        commit=False,
    )


@router.get("/cockpits")
async def list_cockpits(
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    await _require_mssp_owner(session, claims)
    return {"items": [{"id": key, "name": name} for key, name in COCKPITS.items()]}


@router.get("/workspaces")
async def list_workspaces(
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    client = await _require_mssp_owner(session, claims)
    result = await session.execute(
        select(ClientTenantWorkspace)
        .where(ClientTenantWorkspace.client_organization_id == client.id)
        .order_by(ClientTenantWorkspace.name)
    )
    workspaces = result.scalars().all()
    directory = _directory_readiness(client.identifier)
    emails = {
        str(assignment.get("email", "")).lower().strip()
        for workspace in workspaces
        for assignment in (workspace.assignments or [])
    }
    identity_statuses = await _assignment_identity_statuses(
        session, emails, directory["status"] == "enabled"
    )
    return {
        "organization_name": client.name,
        "directory": directory,
        "items": [_workspace_out(item, identity_statuses) for item in workspaces],
    }


@router.get("/workspaces/{workspace_id}/directory/search")
async def search_workspace_directory(
    workspace_id: str,
    q: str = Query(min_length=2, max_length=100),
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    client = await _require_mssp_owner(session, claims)
    workspace = await _get_workspace(session, client.id, workspace_id)
    if workspace.status != "active":
        raise HTTPException(status_code=409, detail="Tenant workspace is not active")

    configured_ids = {
        item["tenant_id"] for item in tenant_ldap_registry.list_tenants()
    }
    if client.identifier not in configured_ids:
        raise HTTPException(
            status_code=409,
            detail=f"Active Directory is not configured for {client.name}",
        )
    connector = tenant_ldap_registry.get_connector(client.identifier)
    if not connector.config.enabled:
        raise HTTPException(
            status_code=409,
            detail=f"Active Directory is disabled for {client.name}",
        )

    users = await connector.search_users(query=q.strip(), limit=50)
    employees = [
        {
            "username": user.username,
            "display_name": user.display_name,
            "position": user.position,
            "email": user.email.strip(),
        }
        for user in users
        if user.email and _EMAIL.fullmatch(user.email.strip())
    ]
    return {
        "organization_name": client.name,
        "directory_name": connector.config.client_name,
        "items": employees,
    }


@router.get("/workspaces/{workspace_id}/members")
async def list_managed_workspace_members(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    workspace, _, allowed_levels = await _get_managed_workspace(
        session, claims, workspace_id
    )
    assignments = [
        assignment
        for assignment in (workspace.assignments or [])
        if not assignment.get("admin_access")
        and not _assignment_has_member_admin_role(workspace, assignment)
        and _assignment_scope_level(workspace, assignment) in allowed_levels
    ]
    emails = {
        str(assignment.get("email", "")).lower().strip()
        for assignment in assignments
    }
    client_result = await session.execute(
        select(ClientOrganization).where(
            ClientOrganization.id == workspace.client_organization_id
        )
    )
    client = client_result.scalars().first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client organization not found")
    readiness = _directory_readiness(client.identifier)
    identity_statuses = await _assignment_identity_statuses(
        session, emails, readiness["status"] == "enabled"
    )
    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "hierarchy_levels": workspace.hierarchy_levels or [],
        "allowed_scope_level_keys": sorted(allowed_levels),
        "directory": readiness,
        "roles": [
            role
            for role in (workspace.roles or [])
            if not role.get("can_manage_members")
            if not role.get("scope_level_keys")
            or set(role.get("scope_level_keys", [])) & allowed_levels
        ],
        "assignments": [
            {
                **assignment,
                "access_status": identity_statuses.get(
                    str(assignment.get("email", "")).lower().strip(),
                    "identity_integration_required",
                ),
            }
            for assignment in assignments
        ],
    }


@router.get("/workspaces/{workspace_id}/members/directory/search")
async def search_managed_workspace_directory(
    workspace_id: str,
    q: str = Query(min_length=2, max_length=100),
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    workspace, _, _ = await _get_managed_workspace(session, claims, workspace_id)
    client_result = await session.execute(
        select(ClientOrganization).where(
            ClientOrganization.id == workspace.client_organization_id
        )
    )
    client = client_result.scalars().first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client organization not found")
    readiness = _directory_readiness(client.identifier)
    if readiness["status"] != "enabled":
        raise HTTPException(
            status_code=409,
            detail="Tenant directory is not enabled for employee search",
        )
    connector = tenant_ldap_registry.get_connector(client.identifier)
    users = await connector.search_users(query=q.strip(), limit=50)
    return {
        "directory_name": connector.config.client_name,
        "items": [
            {
                "username": user.username,
                "display_name": user.display_name,
                "position": user.position,
                "email": user.email.strip(),
            }
            for user in users
            if user.email and _EMAIL.fullmatch(user.email.strip())
        ],
    }


@router.put("/workspaces/{workspace_id}/members")
async def update_managed_workspace_members(
    workspace_id: str,
    payload: TenantMemberAssignmentsUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    workspace, _, allowed_levels = await _get_managed_workspace(
        session, claims, workspace_id
    )
    client_result = await session.execute(
        select(ClientOrganization).where(
            ClientOrganization.id == workspace.client_organization_id
        )
    )
    client = client_result.scalars().first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client organization not found")

    existing_assignments = workspace.assignments or []
    existing_emails = {
        str(assignment.get("email", "")).lower().strip()
        for assignment in existing_assignments
    }
    preserved_assignments = [
        assignment
        for assignment in existing_assignments
        if assignment.get("admin_access")
        or _assignment_has_member_admin_role(workspace, assignment)
        or _assignment_scope_level(workspace, assignment) not in allowed_levels
    ]
    role_by_id = {role.get("id"): role for role in (workspace.roles or [])}
    submitted: list[dict] = []
    assignment_keys: set[tuple[str, str | None]] = set()
    for assignment in payload.assignments:
        key = (assignment.email, assignment.scope_unit_id)
        if key in assignment_keys:
            raise HTTPException(
                status_code=422,
                detail="A member can have only one RBAC assignment at each tier",
            )
        assignment_keys.add(key)
        scope_level = _assignment_scope_level(
            workspace, assignment.model_dump()
        )
        if scope_level not in allowed_levels:
            raise HTTPException(
                status_code=403,
                detail="You may only manage RBAC assignments within your administrator tier",
            )
        if any(
            role_by_id.get(role_id, {}).get("can_manage_members")
            for role_id in assignment.role_ids
        ):
            raise HTTPException(
                status_code=403,
                detail="Member-administrator roles must be granted by the organization administrator",
            )
        if assignment.scope_unit_id in {
            unit.get("id") for unit in (workspace.org_units or [])
        }:
            raise HTTPException(
                status_code=422,
                detail="RBAC assignments must use a hierarchy tier, not an organization unit",
            )
        submitted.append(
            {
                **assignment.model_dump(),
                "admin_access": False,
            }
        )

    new_emails = {
        assignment["email"]
        for assignment in submitted
        if assignment["email"] not in existing_emails
    }
    for assignment in submitted:
        if assignment["email"] in new_emails:
            directory_user = await _require_directory_employee(
                client, assignment["email"]
            )
            assignment["display_name"] = directory_user["display_name"]
        else:
            current = next(
                (
                    item
                    for item in existing_assignments
                    if str(item.get("email", "")).lower().strip()
                    == assignment["email"]
                ),
                None,
            )
            if current:
                assignment["display_name"] = current.get(
                    "display_name", assignment["display_name"]
                )

    combined_assignments = preserved_assignments + submitted
    config = WorkspaceConfiguration(
        root_label=workspace.root_label,
        administration_model=workspace.administration_model,
        hierarchy_levels=workspace.hierarchy_levels or [],
        org_units=workspace.org_units or [],
        roles=workspace.roles or [],
        assignments=combined_assignments,
        status=workspace.status,
    )
    _validate_configuration(config)
    workspace.assignments = combined_assignments
    await _audit_member_change(
        session, request, claims, workspace, "mssp.workspace.members.update"
    )
    await session.commit()
    await session.refresh(workspace)

    visible_assignments = [
        assignment
        for assignment in (workspace.assignments or [])
        if not assignment.get("admin_access")
        and not _assignment_has_member_admin_role(workspace, assignment)
        and _assignment_scope_level(workspace, assignment) in allowed_levels
    ]
    emails = {
        str(assignment.get("email", "")).lower().strip()
        for assignment in visible_assignments
    }
    readiness = _directory_readiness(client.identifier)
    identity_statuses = await _assignment_identity_statuses(
        session, emails, readiness["status"] == "enabled"
    )
    return {
        "workspace_id": workspace.id,
        "assignments": [
            {
                **assignment,
                "access_status": identity_statuses.get(
                    str(assignment.get("email", "")).lower().strip(),
                    "identity_integration_required",
                ),
            }
            for assignment in visible_assignments
        ],
    }


@router.post("/workspaces", status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    client = await _require_mssp_owner(session, claims)
    _validate_configuration(
        WorkspaceConfiguration(
            root_label=payload.root_label,
            administration_model=payload.administration_model,
            hierarchy_levels=payload.hierarchy_levels,
            org_units=[],
            roles=[],
            assignments=[],
            status="active",
        )
    )
    workspace = ClientTenantWorkspace(
        id=str(uuid.uuid4()),
        client_organization_id=client.id,
        identifier=payload.identifier,
        name=payload.name.strip(),
        root_label=payload.root_label.strip(),
        administration_model=payload.administration_model,
        hierarchy_levels=[level.model_dump() for level in payload.hierarchy_levels],
        org_units=[],
        roles=[],
        assignments=[],
        status="active",
    )
    session.add(workspace)
    await _audit_change(session, request, claims, client, "mssp.workspace.create", workspace.id)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A tenant with this identifier already exists in this client profile",
        ) from exc
    await session.refresh(workspace)
    return _workspace_out(workspace)


@router.put("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceConfiguration,
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
):
    client = await _require_mssp_owner(session, claims)
    workspace = await _get_workspace(session, client.id, workspace_id)
    _validate_configuration(payload)
    workspace.root_label = payload.root_label.strip()
    workspace.administration_model = payload.administration_model
    workspace.hierarchy_levels = [level.model_dump() for level in payload.hierarchy_levels]
    workspace.org_units = [unit.model_dump() for unit in payload.org_units]
    workspace.roles = [role.model_dump() for role in payload.roles]
    workspace.assignments = [
        {
            **assignment.model_dump(),
            "email": assignment.email.strip().lower(),
        }
        for assignment in payload.assignments
    ]
    workspace.status = payload.status
    await _audit_change(session, request, claims, client, "mssp.workspace.update", workspace.id)
    await session.commit()
    await session.refresh(workspace)
    emails = {
        str(assignment.get("email", "")).lower().strip()
        for assignment in (workspace.assignments or [])
    }
    directory = _directory_readiness(client.identifier)
    identity_statuses = await _assignment_identity_statuses(
        session, emails, directory["status"] == "enabled"
    )
    return _workspace_out(workspace, identity_statuses)
