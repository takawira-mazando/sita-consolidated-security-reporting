"""Tests for Generic Multi-Tenant Engine and Per-Tenant LDAP Registry."""
from __future__ import annotations

import pytest
from app.tenant_engine import (
    HierarchyLevel,
    OrgUnit,
    RoleDefinition,
    TenantProfile,
    tenant_registry,
)
from app.tenant_profiles import get_active_profile, set_active_profile
from app.connectors.tenant_ldap_registry import (
    tenant_ldap_registry,
    TenantLDAPConfig,
    TierRoleAssignment,
)


class TestGenericTenantEngine:
    def test_default_active_profile_is_sita(self):
        p = get_active_profile()
        assert p.id == "sita"
        assert len(p.hierarchy_levels) >= 2
        assert p.hierarchy_levels[0].name == "department"
        assert p.hierarchy_levels[1].name == "branch"

    def test_switch_to_enterprise_profile(self):
        p = set_active_profile("generic_enterprise")
        assert p.id == "generic_enterprise"
        assert p.hierarchy_levels[0].name == "division"
        assert p.hierarchy_levels[1].name == "business_unit"

        # Check org units
        divs = p.get_org_units_by_level(0)
        assert "corp-finance" in divs
        assert "retail-banking" in divs

        # Check sub units
        children = p.get_children("corp-finance")
        assert "fin-transfers" in children
        assert "fin-treasury" in children

        # Switch back to sita
        set_active_profile("sita")
        assert get_active_profile().id == "sita"

    def test_custom_profile_registration(self):
        custom = TenantProfile(
            id="acme_health",
            name="Acme Healthcare Group",
            description="Healthcare hospital & clinic estate",
            client_type="healthcare",
            hierarchy_levels=[
                HierarchyLevel(level=0, name="hospital", label="Hospital", plural_label="Hospitals"),
                HierarchyLevel(level=1, name="ward", label="Ward / Unit", plural_label="Wards"),
            ],
            org_units={
                "hosp-north": OrgUnit(id="hosp-north", name="North General Hospital", level=0),
                "ward-icu": OrgUnit(id="ward-icu", name="Intensive Care Unit", level=1, parent_id="hosp-north"),
            },
            groups={"region-1": "Region 1 (Metro)"},
            roles={
                "admin": RoleDefinition("admin", "Chief Medical Information Officer", tier=4, scope_type="global"),
                "nurse-lead": RoleDefinition("nurse-lead", "Ward Lead", tier=0, scope_type="scoped"),
            },
            admin_tiers={"admin": 4},
            global_roles={"admin"},
            scoped_roles={"nurse-lead"},
        )
        tenant_registry.register(custom)
        assert tenant_registry.get("acme_health") is not None

        set_active_profile("acme_health")
        active = get_active_profile()
        assert active.id == "acme_health"
        assert active.get_level_label(0) == "Hospital"
        assert active.get_level_label(1) == "Ward / Unit"

        # Cleanup
        set_active_profile("sita")


class TestTenantLDAPRegistry:
    def test_builtin_tenants_registered(self):
        tenants = tenant_ldap_registry.list_tenants()
        tenant_ids = [t["tenant_id"] for t in tenants]
        assert "default" in tenant_ids
        assert "sita" in tenant_ids
        assert "generic_enterprise" in tenant_ids

    def test_get_connector_by_tenant(self):
        sita_conn = tenant_ldap_registry.get_connector("sita")
        assert sita_conn is not None
        assert "sita" in sita_conn.config.server_url.lower()

        ent_conn = tenant_ldap_registry.get_connector("generic_enterprise")
        assert ent_conn is not None
        assert "corp-enterprise" in ent_conn.config.server_url.lower()

    def test_tenant_tier_role_mappings(self):
        sita_cfg = tenant_ldap_registry.get_tenant_config("sita")
        assert len(sita_cfg.tier_role_mappings) > 0
        superadmin_map = next((m for m in sita_cfg.tier_role_mappings if "SuperAdmin" in m.group_name), None)
        assert superadmin_map is not None
        assert "admin" in superadmin_map.roles
        assert superadmin_map.tier == 4

    def test_update_tenant_ldap_config(self):
        new_cfg = {
            "client_name": "Updated SITA Directory",
            "server_url": "ldap://ad2.sita.gov.za:636",
            "use_ssl": True,
        }
        res = tenant_ldap_registry.update_tenant_config("sita", new_cfg)
        assert res.client_name == "Updated SITA Directory"
        assert res.server_url == "ldap://ad2.sita.gov.za:636"
        assert res.use_ssl is True

        # Verify connector was re-instantiated with new config
        conn = tenant_ldap_registry.get_connector("sita")
        assert conn.config.server_url == "ldap://ad2.sita.gov.za:636"
        assert conn.config.use_ssl is True

    def test_tenant_ldap_authentication(self):
        # Authenticate against mock directory for enterprise
        ok, user, tid = tenant_ldap_registry.authenticate_sync(
            "smthembu", "Client#Admin2026!", tenant_id="sita"
        )
        assert ok is True
        assert user is not None
        assert user.username == "smthembu"
        assert tid == "sita"

    def test_multi_client_user_discovery(self):
        # Scan without specifying tenant_id -> discovers in configured connectors
        ok, user, tid = tenant_ldap_registry.authenticate_sync(
            "smthembu", "Client#Admin2026!"
        )
        assert ok is True
        assert user is not None
        assert tid is not None

    def test_tenant_connector_config(self):
        conn = tenant_ldap_registry.get_connector("generic_enterprise")
        assert conn.config.mock_mode is True
        assert conn.config.client_name == "Global Enterprise Security Directory"
        assert conn.config.base_dn == "dc=corp,dc=internal"
