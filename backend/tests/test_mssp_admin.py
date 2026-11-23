from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.connectors.ldap_connector import DirectoryUser
from app.api.auth import JWTClaims, require_roles, tenant_filter, verify_token
from app.api.routers import auth as auth_router
from app.api.routers import mssp_admin
from app.models.client_organization import ClientOrganization
from app.models.compliance import ComplianceSnapshot
from app.models.tenant_workspace import ClientTenantWorkspace
from app.models.finding import Finding


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _Scalars(self.rows)

    def all(self):
        return self.rows


class _Session:
    def __init__(self, clients=None, workspaces=None):
        self.clients = clients or []
        self.workspaces = workspaces or []
        self.audit_rows = []

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        params = statement.compile().params
        if model is ClientOrganization:
            if "lower_1" in params:
                email = params.get("lower_1")
                status = params.get("status_1")
                rows = [
                    client for client in self.clients
                    if client.superadmin_email.lower() == email and client.status == status
                ]
            else:
                client_id = params.get("id_1")
                rows = [client for client in self.clients if client.id == client_id]
        elif model is ClientTenantWorkspace:
            client_id = params.get("client_organization_id_1")
            workspace_id = params.get("id_1")
            status = params.get("status_1")
            rows = [
                workspace for workspace in self.workspaces
                if (client_id is None or workspace.client_organization_id == client_id)
                and (workspace_id is None or workspace.id == workspace_id)
                and (status is None or workspace.status == status)
            ]
        else:
            rows = []
        return _Result(rows)

    def add(self, row):
        if isinstance(row, ClientTenantWorkspace):
            self.workspaces.append(row)
        else:
            self.audit_rows.append(row)

    async def commit(self):
        return None

    async def refresh(self, row):
        now = datetime.now(timezone.utc)
        row.created_at = getattr(row, "created_at", None) or now
        row.updated_at = now

    async def rollback(self):
        return None


def _client(
    session,
    roles,
    email="admin@example.test",
    workspace_access=None,
    active_workspace_id=None,
):
    app = FastAPI()
    app.include_router(mssp_admin.router, prefix="/api/v1/admin")
    app.dependency_overrides[mssp_admin.get_session] = lambda: session

    async def claims():
        workspace_ids = [item["workspace_id"] for item in (workspace_access or [])]
        return JWTClaims(
            sub="user-id",
            email=email,
            roles=roles,
            tenant_workspace_ids=workspace_ids,
            tenant_workspace_access=workspace_access or [],
            active_tenant_workspace_id=active_workspace_id,
        )

    app.dependency_overrides[verify_token] = claims
    return TestClient(app)


def _organization(identifier, email="admin@example.test", status="active"):
    return ClientOrganization(
        id=f"client-{identifier}",
        identifier=identifier,
        name=identifier.title(),
        description="",
        client_type="mssp",
        deployment_model="saas",
        status=status,
        status_options=["draft", "active"],
        primary_contact_name="Contact",
        primary_contact_email=email,
        superadmin_name="Client Admin",
        superadmin_email=email,
        access_setup_status="pending_client_workspace",
    )


def _configuration(**overrides):
    values = {
        "root_label": "Department",
        "administration_model": "mssp_managed",
        "hierarchy_levels": [],
        "org_units": [],
        "roles": [],
        "assignments": [],
        "status": "active",
    }
    values.update(overrides)
    return mssp_admin.WorkspaceConfiguration.model_validate(values)


def test_tenant_can_have_no_custom_levels():
    mssp_admin._validate_configuration(_configuration())


def test_workspace_payload_defaults_omitted_optional_sections():
    payload = mssp_admin.WorkspaceConfiguration.model_validate(
        {
            "root_label": "Organization",
            "administration_model": "mssp_managed",
        }
    )

    assert payload.hierarchy_levels == []
    assert payload.org_units == []
    assert payload.roles == []
    assert payload.assignments == []
    assert payload.status == "active"


def test_hierarchy_levels_can_have_parallel_children_and_parent_links():
    config = _configuration(
        hierarchy_levels=[
            {"key": "national", "label": "National", "parent_key": None},
            {"key": "department", "label": "Department", "parent_key": "national"},
            {"key": "region", "label": "Region", "parent_key": "national"},
            {"key": "branch", "label": "Branch", "parent_key": "department"},
        ],
    )

    mssp_admin._validate_configuration(config)


def test_workspace_payload_accepts_display_only_extra_fields():
    payload = mssp_admin.WorkspaceConfiguration.model_validate(
        {
            "root_label": "Organization",
            "administration_model": "mssp_managed",
            "hierarchy_levels": [
                {
                    "key": "national",
                    "label": "National",
                    "plural_label": "Nationals",
                    "parent_key": None,
                    "stale_ui_field": "ignored",
                }
            ],
            "org_units": [],
            "roles": [],
            "assignments": [],
            "status": "active",
        }
    )

    assert payload.hierarchy_levels[0].key == "national"


def test_parallel_hierarchy_payload_updates_workspace():
    client_org = _organization("sita")
    workspace = ClientTenantWorkspace(
        id="workspace-a",
        client_organization_id=client_org.id,
        identifier="test",
        name="Test",
        root_label="Company",
        administration_model="mssp_managed",
        hierarchy_levels=[],
        org_units=[],
        roles=[],
        assignments=[],
        status="active",
    )
    session = _Session(clients=[client_org], workspaces=[workspace])
    client = _client(session, ["client-admin"])

    response = client.put(
        "/api/v1/admin/mssp/workspaces/workspace-a",
        json={
            "root_label": "Company",
            "administration_model": "mssp_managed",
            "hierarchy_levels": [
                {"key": "national", "label": "National", "plural_label": "NATIONALS", "parent_key": None},
                {"key": "department", "label": "Department", "parent_key": "national"},
                {"key": "region", "label": "Region", "parent_key": "national"},
                {"key": "branch", "label": "Branch", "parent_key": "department"},
            ],
            "org_units": [],
            "roles": [],
            "assignments": [],
            "status": "active",
        },
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("label", "expected_plural"),
    [
        ("Branch", "Branches"),
        ("Company", "Companies"),
        ("Business Unit", "Business Units"),
        ("CITY", "CITIES"),
    ],
)
def test_hierarchy_level_plural_is_derived_from_singular_label(label, expected_plural):
    level = mssp_admin.HierarchyLevel.model_validate(
        {"key": "unit", "label": label}
    )

    assert level.plural_label == expected_plural


def test_custom_branch_hierarchy_supports_eight_units_and_cockpit_scopes():
    branches = [
        {
            "id": f"branch-{index}",
            "name": f"Branch {index}",
            "level_key": "branch",
            "parent_id": None,
        }
        for index in range(1, 9)
    ]
    config = _configuration(
        hierarchy_levels=[
            {"key": "branch", "label": "Branch", "plural_label": "Branches"},
        ],
        org_units=branches,
        roles=[
            {
                "id": "soc-lead",
                "name": "SOC Lead",
                "cockpit_ids": ["soc"],
                "can_manage_members": False,
            },
        ],
        assignments=[
            {
                "id": "assignment-1",
                "email": "analyst@example.test",
                "display_name": "Analyst",
                "role_ids": ["soc-lead"],
                "scope_unit_id": "branch",
            },
        ],
    )

    mssp_admin._validate_configuration(config)


def test_nested_units_must_follow_declared_parent_level():
    config = _configuration(
        hierarchy_levels=[
            {"key": "branch", "label": "Branch", "plural_label": "Branches"},
            {"key": "team", "label": "Team", "plural_label": "Teams"},
        ],
        org_units=[
            {"id": "branch-a", "name": "Branch A", "level_key": "branch"},
            {"id": "team-a", "name": "Team A", "level_key": "team", "parent_id": "missing"},
        ],
    )

    with pytest.raises(HTTPException, match="preceding hierarchy level"):
        mssp_admin._validate_configuration(config)


def test_mssp_managed_mode_cannot_delegate_member_administration():
    config = _configuration(
        roles=[
            {
                "id": "unit-admin",
                "name": "Unit Administrator",
                "can_manage_members": True,
            },
        ],
    )

    with pytest.raises(HTTPException, match="must remain with the MSSP"):
        mssp_admin._validate_configuration(config)


def test_shared_administration_allows_scoped_member_administration():
    config = _configuration(
        administration_model="shared",
        roles=[
            {
                "id": "unit-admin",
                "name": "Unit Administrator",
                "scope_level_keys": ["root"],
                "can_manage_members": True,
            },
        ],
    )

    mssp_admin._validate_configuration(config)


def test_admin_access_assignment_does_not_require_rbac_roles():
    config = _configuration(
        administration_model="delegated",
        hierarchy_levels=[{"key": "national", "label": "National"}],
        assignments=[
            {
                "id": "admin-assignment",
                "email": "admin@example.test",
                "display_name": "Tenant Admin",
                "role_ids": [],
                "scope_unit_id": "national",
                "admin_access": True,
            },
        ],
    )

    mssp_admin._validate_configuration(config)


def test_mssp_managed_mode_rejects_direct_admin_access_assignment():
    config = _configuration(
        assignments=[
            {
                "id": "admin-assignment",
                "email": "admin@example.test",
                "display_name": "Tenant Admin",
                "role_ids": [],
                "admin_access": True,
            },
        ],
    )

    with pytest.raises(HTTPException, match="Administrator access must remain"):
        mssp_admin._validate_configuration(config)


@pytest.mark.asyncio
async def test_admin_access_resolves_without_assigning_rbac_roles():
    workspace = type(
        "Workspace",
        (),
        {
            "status": "active",
            "id": "workspace-a",
            "name": "Workspace A",
            "administration_model": "shared",
            "hierarchy_levels": [{"key": "national", "label": "National", "parent_key": None}],
            "org_units": [],
            "roles": [],
            "assignments": [
                {
                    "email": "admin@example.test",
                    "role_ids": [],
                    "scope_unit_id": "national",
                    "admin_access": True,
                },
            ],
        },
    )()

    class AssignmentSession:
        async def execute(self, _statement):
            return _Result([workspace])

    (
        roles,
        workspace_ids,
        scope_ids,
        can_manage,
        workspace_access,
    ) = await auth_router._resolve_workspace_assignments(
        AssignmentSession(), "admin@example.test"
    )

    assert "tenant-admin" in roles
    assert "exec" not in roles
    assert workspace_ids == ["workspace-a"]
    assert scope_ids == ["national"]
    assert can_manage is True
    assert workspace_access[0]["admin_scope_level_keys"] == ["national"]


@pytest.mark.asyncio
async def test_workspace_dashboard_grant_requires_workspace_context_and_scope():
    claims = JWTClaims(
        roles=[],
        tenant_workspace_ids=["workspace-a"],
        tenant_workspace_access=[
            {
                "workspace_id": "workspace-a",
                "cockpit_scopes": {"exec": ["department", "branch"]},
            }
        ],
        active_tenant_workspace_id="workspace-a",
    )

    authorized = await require_roles("dashboard")(claims)
    scope_sql = str(tenant_filter(authorized, Finding).compile())

    assert authorized.active_tenant_scope_level_keys == ["branch", "department"]
    assert "tenant_workspace_id" in scope_sql
    assert "tenant_scope_level_key" in scope_sql


@pytest.mark.asyncio
async def test_parent_tier_grant_covers_descendant_tier_data():
    workspace = type(
        "Workspace",
        (),
        {
            "status": "active",
            "id": "workspace-a",
            "name": "Workspace A",
            "administration_model": "shared",
            "hierarchy_levels": [
                {"key": "department", "label": "Department", "parent_key": None},
                {"key": "branch", "label": "Branch", "parent_key": "department"},
            ],
            "org_units": [],
            "roles": [
                {
                    "id": "department-soc",
                    "cockpit_ids": ["soc"],
                    "scope_level_keys": ["department"],
                },
            ],
            "assignments": [
                {
                    "email": "analyst@example.test",
                    "role_ids": ["department-soc"],
                    "scope_unit_id": "department",
                },
            ],
        },
    )()

    class AssignmentSession:
        async def execute(self, _statement):
            return _Result([workspace])

    result = await auth_router._resolve_workspace_assignments(
        AssignmentSession(), "analyst@example.test"
    )

    assert result[-1][0]["cockpit_scopes"]["soc"] == ["department", "branch"]


@pytest.mark.asyncio
async def test_workspace_dashboard_grant_is_not_global_without_context():
    claims = JWTClaims(
        roles=[],
        tenant_workspace_ids=["workspace-a"],
        tenant_workspace_access=[
            {
                "workspace_id": "workspace-a",
                "cockpit_scopes": {"exec": ["root"]},
            }
        ],
    )

    with pytest.raises(HTTPException, match="Insufficient permissions"):
        await require_roles("dashboard")(claims)

    scope_sql = str(tenant_filter(claims, Finding).compile())
    assert "tenant_workspace_id IS NULL" in scope_sql


def test_legacy_tier_scope_fails_closed_for_unattributed_models():
    claims = JWTClaims(roles=["compliance"], province_ids=["gp"])

    scope_sql = str(tenant_filter(claims, ComplianceSnapshot).compile())

    assert scope_sql == "false"


def test_custom_role_rejects_non_cockpit_permissions():
    with pytest.raises(ValueError, match="Unknown cockpit"):
        mssp_admin.TenantRole.model_validate(
            {
                "id": "custom",
                "name": "Custom",
                "cockpit_ids": ["admin_write"],
            }
        )


def test_role_rejects_duplicate_provisioning_levels():
    with pytest.raises(ValueError, match="Provisioning levels must be unique"):
        mssp_admin.TenantRole.model_validate(
            {
                "id": "soc-lead",
                "name": "SOC Lead",
                "scope_level_keys": ["root", "root"],
            }
        )


def test_role_provisioning_level_must_exist_in_tenant_hierarchy():
    config = _configuration(
        hierarchy_levels=[
            {"key": "branch", "label": "Branch", "plural_label": "Branches"},
        ],
        roles=[
            {
                "id": "soc-lead",
                "name": "SOC Lead",
                "scope_level_keys": ["province"],
            },
        ],
    )

    with pytest.raises(HTTPException, match="undefined provisioning level"):
        mssp_admin._validate_configuration(config)


def test_assignment_scope_must_match_role_provisioning_level():
    config = _configuration(
        hierarchy_levels=[
            {"key": "branch", "label": "Branch", "plural_label": "Branches"},
        ],
        roles=[
            {
                "id": "soc-lead",
                "name": "SOC Lead",
                "scope_level_keys": ["root"],
            },
        ],
        assignments=[
            {
                "id": "assignment-1",
                "email": "analyst@example.test",
                "display_name": "Analyst",
                "role_ids": ["soc-lead"],
                "scope_unit_id": "branch",
            },
        ],
    )

    with pytest.raises(HTTPException, match="not provisioned at this level"):
        mssp_admin._validate_configuration(config)


def test_operator_cannot_manage_client_tenant_workspaces():
    client = _client(_Session(), ["operator"])

    response = client.get("/api/v1/admin/mssp/workspaces")

    assert response.status_code == 403


def test_client_admin_workspace_list_includes_organization_name_without_tenants(monkeypatch):
    organization = _organization("sita")
    organization.name = "SITA"
    session = _Session(clients=[organization])
    client = _client(session, ["client-admin"])
    monkeypatch.setattr(mssp_admin.tenant_ldap_registry, "list_tenants", lambda: [])

    response = client.get("/api/v1/admin/mssp/workspaces")

    assert response.status_code == 200
    assert response.json() == {
        "organization_name": "SITA",
        "directory": {"status": "not_configured", "name": ""},
        "items": [],
    }


def test_client_admin_role_does_not_grant_platform_admin_permissions():
    app = FastAPI()

    @app.get("/restricted")
    async def restricted(claims=Depends(require_roles("admin_read"))):
        return {"email": claims.email}

    async def claims():
        return JWTClaims(sub="client-user", email="client@example.test", roles=["client-admin"])

    app.dependency_overrides[verify_token] = claims
    response = TestClient(app).get("/restricted")

    assert response.status_code == 403


def test_client_admin_can_create_custom_tenant_without_granting_a_platform_role():
    session = _Session(clients=[_organization("sita")])
    client = _client(session, ["client-admin"])

    response = client.post(
        "/api/v1/admin/mssp/workspaces",
        json={
            "identifier": "sample-client",
            "name": "Example Client Organization",
            "root_label": "Organization",
            "administration_model": "delegated",
            "hierarchy_levels": [
                {"key": "branch", "label": "Branch"},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["root_label"] == "Organization"
    assert body["hierarchy_levels"][0]["label"] == "Branch"
    assert body["hierarchy_levels"][0]["plural_label"] == "Branches"
    assert body["roles"] == []
    assert body["assignments"] == []


def test_client_admin_cannot_read_another_client_workspace():
    session = _Session(
        clients=[_organization("client-a")],
        workspaces=[
            ClientTenantWorkspace(
                id="workspace-b",
                client_organization_id="client-client-b",
                identifier="tenant-b",
                name="Tenant B",
                root_label="Organization",
                administration_model="mssp_managed",
                hierarchy_levels=[],
                org_units=[],
                roles=[],
                assignments=[],
                status="active",
            ),
        ],
    )
    client = _client(session, ["client-admin"])

    response = client.put(
        "/api/v1/admin/mssp/workspaces/workspace-b",
        json={
            "root_label": "Organization",
            "administration_model": "mssp_managed",
            "hierarchy_levels": [],
            "org_units": [],
            "roles": [],
            "assignments": [],
            "status": "active",
        },
    )

    assert response.status_code == 404


def test_client_admin_can_save_scoped_cockpit_role_and_delegated_assignment():
    client_org = _organization("sita")
    workspace = ClientTenantWorkspace(
        id="workspace-a",
        client_organization_id=client_org.id,
        identifier="home-affairs",
        name="Example Client Organization",
        root_label="Organization",
        administration_model="mssp_managed",
        hierarchy_levels=[],
        org_units=[],
        roles=[],
        assignments=[],
        status="active",
    )
    session = _Session(clients=[client_org], workspaces=[workspace])
    client = _client(session, ["client-admin"])

    response = client.put(
        "/api/v1/admin/mssp/workspaces/workspace-a",
        json={
            "root_label": "Department",
            "administration_model": "delegated",
            "hierarchy_levels": [
                {"key": "branch", "label": "Branch", "plural_label": "Branches"},
            ],
            "org_units": [
                {"id": "branch-a", "name": "Branch A", "level_key": "branch"},
            ],
            "roles": [
                {
                    "id": "branch-security-admin",
                    "name": "Branch Security Administrator",
                    "cockpit_ids": ["soc", "appsec"],
                    "scope_level_keys": ["branch"],
                    "can_manage_members": True,
                },
            ],
            "assignments": [
                {
                    "id": "assignment-1",
                    "email": "branch.admin@example.test",
                    "display_name": "Branch Admin",
                    "role_ids": ["branch-security-admin"],
                    "scope_unit_id": "branch",
                },
            ],
            "status": "active",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["roles"][0]["cockpit_ids"] == ["soc", "appsec"]
    assert body["roles"][0]["scope_level_keys"] == ["branch"]
    assert body["assignments"][0]["scope_unit_id"] == "branch"
    assert body["assignments"][0]["access_status"] in {
        "pending_first_sign_in",
        "identity_integration_required",
    }


def test_client_admin_can_search_employees_in_client_directory(monkeypatch):
    client_org = _organization("fnb")
    workspace = ClientTenantWorkspace(
        id="workspace-a",
        client_organization_id=client_org.id,
        identifier="fnb-tenant",
        name="FNB South Africa",
        root_label="National",
        administration_model="mssp_managed",
        hierarchy_levels=[],
        org_units=[],
        roles=[],
        assignments=[],
        status="active",
    )
    session = _Session(clients=[client_org], workspaces=[workspace])

    class _Directory:
        config = type("Config", (), {"enabled": True, "client_name": "FNB Active Directory"})()

        async def search_users(self, query, limit):
            assert query == "Jane"
            assert limit == 50
            return [
                DirectoryUser(
                    username="jdoe",
                    display_name="Jane Doe",
                    surname="Doe",
                    position="Security Analyst",
                    employee_code="EMP-1",
                    email="jane.doe@tenant.example",
                )
            ]

    monkeypatch.setattr(
        mssp_admin.tenant_ldap_registry,
        "list_tenants",
        lambda: [{"tenant_id": "fnb"}],
    )
    monkeypatch.setattr(
        mssp_admin.tenant_ldap_registry,
        "get_connector",
        lambda tenant_id: _Directory(),
    )
    client = _client(session, ["client-admin"])

    response = client.get(
        "/api/v1/admin/mssp/workspaces/workspace-a/directory/search",
        params={"q": "Jane"},
    )

    assert response.status_code == 200
    assert response.json()["directory_name"] == "FNB Active Directory"
    assert response.json()["items"][0]["email"] == "jane.doe@tenant.example"


def _delegated_member_workspace(client_org):
    return ClientTenantWorkspace(
        id="workspace-managed",
        client_organization_id=client_org.id,
        identifier="managed-tenant",
        name="Managed tenant",
        root_label="Organization",
        administration_model="delegated",
        hierarchy_levels=[
            {"key": "national", "label": "National", "parent_key": None},
            {"key": "branch", "label": "Branch", "parent_key": "national"},
        ],
        org_units=[],
        roles=[
            {
                "id": "soc-reader",
                "name": "SOC Reader",
                "cockpit_ids": ["soc"],
                "scope_level_keys": ["branch", "national"],
                "can_manage_members": False,
            },
            {
                "id": "member-manager",
                "name": "Member Manager",
                "cockpit_ids": ["soc"],
                "scope_level_keys": ["branch"],
                "can_manage_members": True,
            },
        ],
        assignments=[
            {
                "id": "admin-grant",
                "email": "delegate@example.test",
                "display_name": "Delegate",
                "role_ids": [],
                "scope_unit_id": "branch",
                "admin_access": True,
            },
            {
                "id": "rbac-grant",
                "email": "member@example.test",
                "display_name": "Member",
                "role_ids": ["soc-reader"],
                "scope_unit_id": "branch",
                "admin_access": False,
            },
            {
                "id": "member-admin-grant",
                "email": "other-admin@example.test",
                "display_name": "Other Admin",
                "role_ids": ["member-manager"],
                "scope_unit_id": "branch",
                "admin_access": False,
            },
            {
                "id": "outside-scope-grant",
                "email": "national@example.test",
                "display_name": "National Member",
                "role_ids": ["soc-reader"],
                "scope_unit_id": "national",
                "admin_access": False,
            },
        ],
        status="active",
    )


def _delegated_member_client(session):
    return _client(
        session,
        ["tenant-admin"],
        email="delegate@example.test",
        workspace_access=[
            {
                "workspace_id": "workspace-managed",
                "admin_scope_level_keys": ["branch"],
            },
        ],
        active_workspace_id="workspace-managed",
    )


def test_delegated_member_list_excludes_admin_and_member_admin_grants():
    client_org = _organization("managed")
    workspace = _delegated_member_workspace(client_org)
    client = _delegated_member_client(
        _Session(clients=[client_org], workspaces=[workspace])
    )

    response = client.get("/api/v1/admin/mssp/workspaces/workspace-managed/members")

    assert response.status_code == 200
    body = response.json()
    assert [role["id"] for role in body["roles"]] == ["soc-reader"]
    assert [assignment["id"] for assignment in body["assignments"]] == ["rbac-grant"]


def test_delegated_member_update_preserves_admin_and_out_of_scope_grants():
    client_org = _organization("managed")
    workspace = _delegated_member_workspace(client_org)
    client = _delegated_member_client(
        _Session(clients=[client_org], workspaces=[workspace])
    )

    response = client.put(
        "/api/v1/admin/mssp/workspaces/workspace-managed/members",
        json={"assignments": []},
    )

    assert response.status_code == 200
    assert response.json()["assignments"] == []
    assert {item["id"] for item in workspace.assignments} == {
        "admin-grant",
        "member-admin-grant",
        "outside-scope-grant",
    }


def test_delegated_member_update_cannot_grant_member_admin_role():
    client_org = _organization("managed")
    workspace = _delegated_member_workspace(client_org)
    client = _delegated_member_client(
        _Session(clients=[client_org], workspaces=[workspace])
    )

    response = client.put(
        "/api/v1/admin/mssp/workspaces/workspace-managed/members",
        json={
            "assignments": [
                {
                    "id": "new-grant",
                    "email": "new-member@example.test",
                    "display_name": "New Member",
                    "role_ids": ["member-manager"],
                    "scope_unit_id": "branch",
                }
            ]
        },
    )

    assert response.status_code == 403
    assert "organization administrator" in response.json()["detail"]
