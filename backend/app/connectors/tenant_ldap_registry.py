"""Multi-Tenant LDAP / Active Directory Registry.

Enables per-client and per-tier configurable LDAP directory integration across
the platform:
1. Every tenant/client maintains its own dedicated directory server URL, Base DN,
   search filters, service bind credentials, and attribute mappings.
2. Group-to-role mappings are customizable per tenant and tier level.
3. Multi-client directory authentication and discovery.
4. Complete administrative API access for listing, updating, testing, and switching
   LDAP configurations on a per-tenant basis.
"""
from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field

from app.connectors.ldap_connector import (
    LDAPConfig,
    UnifiedLDAPConnector,
    DirectoryUser,
    DEFAULT_ACTIVE_DIRECTORY_PROFILE,
    DEFAULT_OPENLDAP_PROFILE,
    DEFAULT_FREEIPA_PROFILE,
)

logger = logging.getLogger("app.connectors.tenant_ldap")


class TierRoleAssignment(BaseModel):
    """Maps a directory group to a platform role, administrative tier, and scope."""
    group_name: str
    roles: list[str] = Field(default_factory=list)
    tier: int = 0                           # 0: non-admin, 3: delegated, 4: superadmin
    default_scope: list[str] = Field(default_factory=list)
    description: str = ""


class TenantLDAPConfig(LDAPConfig):
    """LDAP configuration scoped to a specific tenant / client."""
    tenant_id: str = "default"
    tenant_name: str = "Default Tenant"
    tier_role_mappings: list[TierRoleAssignment] = Field(default_factory=list)


class TenantLDAPRegistry:
    """Registry managing directory connectors for multiple tenants / clients."""

    def __init__(self):
        self._connectors: dict[str, UnifiedLDAPConnector] = {}
        self._tenant_configs: dict[str, TenantLDAPConfig] = {}
        self._default_tenant_id: str = "default"

        # Initialize default connector
        default_conn = UnifiedLDAPConnector()
        self._connectors["default"] = default_conn
        self._tenant_configs["default"] = TenantLDAPConfig(
            tenant_id="default",
            tenant_name=default_conn.config.client_name,
            **default_conn.config.model_dump(),
        )

    def register_tenant(self, tenant_id: str, config: TenantLDAPConfig) -> UnifiedLDAPConnector:
        """Register or update an LDAP connector for a tenant."""
        conn = UnifiedLDAPConnector(initial_config=config)
        self._connectors[tenant_id] = conn
        self._tenant_configs[tenant_id] = config
        logger.info("Registered tenant LDAP connector for tenant '%s' ('%s')", tenant_id, config.tenant_name)
        return conn

    def get_connector(self, tenant_id: str | None = None) -> UnifiedLDAPConnector:
        """Retrieve the connector for a specific tenant, or fallback to default."""
        if tenant_id and tenant_id in self._connectors:
            return self._connectors[tenant_id]
        if self._default_tenant_id in self._connectors:
            return self._connectors[self._default_tenant_id]
        return next(iter(self._connectors.values()))

    def get_tenant_config(self, tenant_id: str | None = None) -> TenantLDAPConfig:
        target = tenant_id or self._default_tenant_id
        if target in self._tenant_configs:
            return self._tenant_configs[target]
        # Return fallback default
        return self._tenant_configs.get(self._default_tenant_id) or TenantLDAPConfig()

    def update_tenant_config(self, tenant_id: str, new_config: dict[str, Any] | TenantLDAPConfig) -> TenantLDAPConfig:
        """Update LDAP settings for a given tenant."""
        current = self._tenant_configs.get(tenant_id)
        if isinstance(new_config, dict):
            if current:
                merged = current.model_dump()
                # Do not overwrite with masked password
                if new_config.get("bind_password") in ("********", "", None):
                    new_config.pop("bind_password", None)
                merged.update(new_config)
                cfg = TenantLDAPConfig(**merged)
            else:
                cfg = TenantLDAPConfig(tenant_id=tenant_id, **new_config)
        else:
            cfg = new_config

        cfg.tenant_id = tenant_id
        self.register_tenant(tenant_id, cfg)
        return cfg

    def list_tenants(self) -> list[dict[str, Any]]:
        """List all configured tenant directories."""
        res = []
        for tid, cfg in self._tenant_configs.items():
            res.append({
                "tenant_id": tid,
                "tenant_name": cfg.tenant_name,
                "client_name": cfg.client_name,
                "server_url": cfg.server_url,
                "base_dn": cfg.base_dn,
                "preset_profile": cfg.preset_profile,
                "enabled": cfg.enabled,
                "mock_mode": cfg.mock_mode,
                "tier_mappings_count": len(cfg.tier_role_mappings),
            })
        return res

    def authenticate_sync(
        self, username_or_email: str, password: str, tenant_id: str | None = None
    ) -> tuple[bool, DirectoryUser | None, str | None]:
        """Synchronously authenticate against tenant directory (for mock and offline modes)."""
        if tenant_id and tenant_id in self._connectors:
            conn = self._connectors[tenant_id]
            ok, user = conn.authenticate_mock_sync(username_or_email, password)
            if ok and user:
                return True, user, tenant_id
            return False, None, tenant_id

        for tid, conn in self._connectors.items():
            ok, user = conn.authenticate_mock_sync(username_or_email, password)
            if ok and user:
                return True, user, tid

        return False, None, None

    async def authenticate(
        self, username_or_email: str, password: str, tenant_id: str | None = None
    ) -> tuple[bool, DirectoryUser | None, str | None]:
        """Authenticate user against tenant directory. Returns (authenticated, user, tenant_id)."""
        # If tenant_id is specified, try that tenant's directory
        if tenant_id and tenant_id in self._connectors:
            conn = self._connectors[tenant_id]
            ok, user = await conn.authenticate_user(username_or_email, password)
            if ok and user:
                return True, user, tenant_id
            return False, None, tenant_id

        # Multi-client discovery: scan configured tenant connectors
        for tid, conn in self._connectors.items():
            ok, user = await conn.authenticate_user(username_or_email, password)
            if ok and user:
                return True, user, tid

        return False, None, None

    async def test_tenant_connection(
        self, tenant_id: str | None = None, override_config: LDAPConfig | None = None
    ) -> dict[str, Any]:
        """Test connection for a specific tenant directory."""
        conn = self.get_connector(tenant_id)
        res = await conn.test_connection(override_config)
        res["tenant_id"] = tenant_id or "default"
        return res


# Global singleton instance
tenant_ldap_registry = TenantLDAPRegistry()
