"""Generic profile template for client workspaces."""
from app.tenant import ADMIN_TIERS, GRANTABLE_ROLES
from app.tenant_engine import RoleDefinition, TenantProfile

GLOBAL_ROLES = frozenset({"exec", "compliance", "sre"})
SCOPED_ROLES = frozenset({"soc", "appsec", "dbsec", "ai"})


def build_profile(client_id: str, client_name: str) -> TenantProfile:
    """Create an empty profile; hierarchy and organization units are tenant-defined."""
    roles = {
        role_id: RoleDefinition(
            id=role_id,
            name=label,
            description=description,
            tier=ADMIN_TIERS.get(role_id, 0),
            scope_type="global" if role_id in GLOBAL_ROLES or role_id in {"admin", "operator"} else "scoped",
        )
        for role_id, label, description in (
            ("operator", "Platform Operator", "Manages platform administration."),
            ("admin", f"{client_name} Administrator", "Manages client access."),
            ("transversal-admin", "Delegated Administrator", "Manages permitted access within assigned scope."),
            ("exec", "Executive", "Reviews executive security posture."),
            ("compliance", "Compliance", "Reviews configured compliance frameworks."),
            ("sre", "Service Operations", "Reviews service and telemetry health."),
            ("soc", "SOC Analyst", "Reviews alerts and security findings."),
            ("appsec", "Application Security", "Reviews application security findings."),
            ("dbsec", "Data Security", "Reviews database and data security events."),
            ("ai", "Threat Intelligence", "Reviews security intelligence."),
        )
    }

    return TenantProfile(
        id=client_id,
        name=client_name,
        description="Generic multi-tenant profile. Configure hierarchy levels and organization units for each client.",
        client_type="mssp",
        roles=roles,
        admin_tiers=dict(ADMIN_TIERS),
        grantable_roles={role: set(grants) for role, grants in GRANTABLE_ROLES.items()},
        global_roles=set(GLOBAL_ROLES),
        scoped_roles=set(SCOPED_ROLES),
    )
