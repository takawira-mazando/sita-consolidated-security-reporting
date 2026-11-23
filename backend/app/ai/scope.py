"""Authenticated tenant scope for AI reports."""
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from app.api.auth import JWTClaims, is_global_scope, tenant_filter


@dataclass(frozen=True)
class ReportScope:
    is_platform_scope: bool
    scope_hash: str
    tenant_workspace_id: str | None = None
    tenant_workspace_name: str | None = None
    tenant_scope_unit_ids: tuple[str, ...] = ()
    tenant_scope_level_keys: tuple[str, ...] = ()

    def get_filter(self, model: Any) -> Any:
        """Use the same fail-closed data predicate as the request handler."""
        dummy_claims = JWTClaims(
            roles=["operator"] if self.is_platform_scope else ["soc"],
            tenant_workspace_ids=(
                [self.tenant_workspace_id] if self.tenant_workspace_id else []
            ),
            tenant_scope_unit_ids=list(self.tenant_scope_unit_ids),
            active_tenant_workspace_id=self.tenant_workspace_id,
            active_tenant_scope_level_keys=list(self.tenant_scope_level_keys),
        )
        return tenant_filter(dummy_claims, model)

    def describe(self) -> str:
        if self.tenant_workspace_id:
            scope = (
                "Entire workspace"
                if "root" in self.tenant_scope_level_keys
                else ", ".join(self.tenant_scope_level_keys) or "No authorized tiers"
            )
            return f"{self.tenant_workspace_name or 'Tenant workspace'} - {scope}"
        if self.is_platform_scope:
            return "Platform scope"
        return "No authorized tenant workspace"


def compute_scope_hash(
    tenant_workspace_ids: list[str],
    tenant_scope_unit_ids: list[str],
    tenant_scope_level_keys: list[str],
    is_platform_scope: bool,
) -> str:
    canonical = {
        "tenant_workspace_ids": sorted(tenant_workspace_ids),
        "tenant_scope_unit_ids": sorted(tenant_scope_unit_ids),
        "tenant_scope_level_keys": sorted(tenant_scope_level_keys),
        "platform_scope": bool(is_platform_scope),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def resolve_report_scope(claims: JWTClaims) -> ReportScope:
    tenant_workspace_id = claims.active_tenant_workspace_id
    tenant_scope_unit_ids = sorted(set(claims.tenant_scope_unit_ids or []))
    tenant_scope_level_keys = sorted(
        set(claims.active_tenant_scope_level_keys or [])
    )
    tenant_access = next(
        (
            item
            for item in claims.tenant_workspace_access
            if item.get("workspace_id") == tenant_workspace_id
        ),
        {},
    )
    is_platform_scope = is_global_scope(claims) and tenant_workspace_id is None

    return ReportScope(
        is_platform_scope=is_platform_scope,
        scope_hash=compute_scope_hash(
            [tenant_workspace_id] if tenant_workspace_id else list(claims.tenant_workspace_ids),
            tenant_scope_unit_ids,
            tenant_scope_level_keys,
            is_platform_scope,
        ),
        tenant_workspace_id=tenant_workspace_id,
        tenant_workspace_name=tenant_access.get("workspace_name"),
        tenant_scope_unit_ids=tuple(tenant_scope_unit_ids),
        tenant_scope_level_keys=tuple(tenant_scope_level_keys),
    )
