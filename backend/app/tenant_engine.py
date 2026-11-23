"""Generic, Multi-Tenant Organizational and RBAC Hierarchy Engine.

Decouples tenancy, tiers, and RBAC from any hardcoded client (such as SITA or SA
Government). Provides:
1. N-level configurable organizational hierarchy (e.g. Org -> Department -> Branch
   or Enterprise -> Division -> Business Unit -> Team).
2. Dynamic Role-Based Access Control (RBAC) with customizable tiers, grant matrices,
   and scope validators.
3. Pluggable Tenant Profiles allowing multiple client use cases (SITA / SA Government,
   Corporate Enterprise, Banking/Financial, Healthcare, etc.) to run on the exact same engine.
4. Full backward-compatibility shims for existing database columns, tokens, and APIs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class HierarchyLevel:
    """Defines a level in a tenant's organizational hierarchy."""
    level: int
    name: str                 # slug, e.g. "department", "division", "business_unit"
    label: str                # UI display name, e.g. "Department", "Division"
    plural_label: str         # UI plural name, e.g. "Departments", "Divisions"
    description: str = ""


@dataclass
class OrgUnit:
    """A generic node in the client's organizational tree."""
    id: str
    name: str
    level: int = 0
    parent_id: str | None = None
    group_id: str | None = None         # e.g., province, region, cluster, zone
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleDefinition:
    """Defines a platform role, its administrative tier, and scoping rules."""
    id: str
    name: str
    description: str = ""
    tier: int = 0                       # 0: non-admin, 3: delegated, 4: admin, 5: operator
    scope_type: str = "scoped"          # "global" (whole estate) or "scoped" (bound to org units)
    permissions: set[str] = field(default_factory=set)
    grantable_by: set[str] = field(default_factory=set)


@dataclass
class ControlPlaneConfig:
    """Customizable control plane governance configuration for a tenant."""
    directory_type: str = "Active Directory / LDAP"   # e.g., "Active Directory", "OpenLDAP", "Azure AD / Entra ID", "Okta OIDC"
    directory_ou_base: str = "OU=Security,DC=tenant,DC=internal"
    admin_ceiling_enforced: bool = True              # Strict one-way delegation ceiling (anti-elevation)
    lateral_isolation_enforced: bool = True          # Cross-tenant admin blocked
    jwt_signing_algorithm: str = "RS256"             # RS256 or HS256
    token_ttl_minutes: int = 480                     # Session lifespan (8h)
    audit_trail_immutable: bool = True              # WORM audit logging for directory events
    custom_role_creation_allowed: bool = True        # Tenant can define novel roles
    max_hierarchy_depth: int = 5                     # Max nested organizational tiers


@dataclass
class IngestionAdapterDef:
    """Pluggable log and telemetry ingestion adapter definition.

    Allows any log, event stream, or OEM telemetry to be ingested into the
    tenant's data plane and contribute dynamically to risk fusion scoring.
    """
    id: str
    name: str                            # e.g., "CrowdStrike Falcon EDR", "AWS CloudTrail", "Syslog CEF Stream"
    category: str                        # "edr", "appsec", "dam", "waf", "cloud", "network", "siem", "custom"
    protocol: str                        # "syslog", "cef", "leef", "webhook_json", "kafka", "rest_polling", "s3_bucket"
    weight: float = 0.20                 # Contribution to composite risk score (0.0 to 1.0)
    enabled: bool = True
    description: str = ""
    parser_schema: str = "auto"          # "auto", "cef_standard", "json_ecs", "syslog_rfc5424", "custom_mapping"
    rate_limit_eps: int = 5000           # Events per second ceiling


@dataclass
class DataPlaneConfig:
    """Customizable telemetry, data isolation, and risk engine configuration for a tenant."""
    fail_closed_sql: bool = True                     # Unscoped queries fail-closed (WHERE false)
    tenant_filter_column: str = "department_id"      # Core SQL isolation column key (maps to tenant/org)

    # Pluggable Ingestion Adapters: can ingest ANY log or telemetry source with the appropriate adapter
    ingestion_adapters: list[IngestionAdapterDef] = field(default_factory=lambda: [
        IngestionAdapterDef(
            id="appscan-adapter",
            name="HCL AppScan SAST/DAST",
            category="appsec",
            protocol="rest_polling",
            weight=0.35,
            description="Static & Dynamic Code Security findings and SCA dependencies",
        ),
        IngestionAdapterDef(
            id="imperva-dam-adapter",
            name="Imperva DAM (Database Activity)",
            category="dam",
            protocol="syslog",
            weight=0.25,
            description="Database query violations, privileged SQL access & sensitive datastore monitoring",
        ),
        IngestionAdapterDef(
            id="imperva-waf-adapter",
            name="Imperva WAF (Web App Firewall)",
            category="waf",
            protocol="cef",
            weight=0.15,
            description="Edge perimeter attack blocks, OWASP Top 10 exploits & DDoS mitigation",
        ),
        IngestionAdapterDef(
            id="apisec-adapter",
            name="API Security & Exposure",
            category="apisec",
            protocol="webhook_json",
            weight=0.15,
            description="Shadow API discovery, undocumented endpoint exposure & schema drift",
        ),
        IngestionAdapterDef(
            id="compliance-adapter",
            name="Compliance Assurance (POPIA/GDPR)",
            category="compliance",
            protocol="rest_polling",
            weight=0.10,
            description="Regulatory control gaps, audit evidence collection & framework penalties",
        ),
    ])

    # Supported universal ingestion protocols for tenant-added custom log adapters
    supported_protocols: list[str] = field(default_factory=lambda: [
        "Syslog (RFC 5424 / 3164)",
        "CEF (Common Event Format)",
        "LEEF (Log Event Extended Format)",
        "JSON Webhook / HTTP Event Collector (HEC)",
        "Apache Kafka / Streaming PubSub",
        "S3 / Cloud Storage Bucket Polling",
        "REST API Polling Adapter",
        "eBPF / OSQuery Endpoint Stream",
    ])

    telemetry_sources: list[str] = field(default_factory=lambda: [
        "HCL AppScan SAST/DAST",
        "Imperva DAM (Database Activity)",
        "Imperva WAF (Web Application Firewall)",
        "Shadow & Managed API Discovery",
    ])
    risk_weights: dict[str, float] = field(default_factory=lambda: {
        "appscan": 0.35,
        "imperva": 0.25,
        "exposure": 0.20,
        "compliance": 0.20,
    })
    pii_masking_enabled: bool = True                 # POPIA / GDPR masking of employee & citizen PII
    raw_sql_redacted: bool = True                    # Parameterized query values hidden from non-DB roles
    compliance_frameworks: list[str] = field(default_factory=lambda: [
        "POPIA / GDPR",
        "ISO/IEC 27001",
        "NIST CSF",
    ])
    cockpits_available: list[str] = field(default_factory=lambda: [
        "Executive Leadership & Risk Fusion",
        "SOC Operations & Incident Queue",
        "Application Security & Repositories",
        "Database Activity Monitoring (DAM)",
        "Compliance Assurance & Control Evidence",
        "Platform & Telemetry Health",
    ])


@dataclass
class TenantProfile:
    """Encapsulates the complete organizational, tier, and RBAC model for a client or tenant."""
    id: str
    name: str
    description: str = ""
    client_type: str = "enterprise"     # "government", "enterprise", "financial", "custom"

    # Control Plane & Data Plane specifications (customizable per tenant)
    control_plane: ControlPlaneConfig = field(default_factory=ControlPlaneConfig)
    data_plane: DataPlaneConfig = field(default_factory=DataPlaneConfig)

    # Hierarchy definition
    hierarchy_levels: list[HierarchyLevel] = field(default_factory=list)

    # Organizational units (id -> OrgUnit)
    org_units: dict[str, OrgUnit] = field(default_factory=dict)

    # Groups / Regional groupings (id -> label, e.g. provinces or geographic zones)
    groups: dict[str, str] = field(default_factory=dict)

    # High-level clusters or portfolio segments (e.g. ministry/cluster rollups)
    clusters: dict[str, str] = field(default_factory=dict)
    portfolios: dict[str, str] = field(default_factory=dict)
    portfolio_to_cluster: dict[str, str] = field(default_factory=dict)
    org_to_portfolio: dict[str, str] = field(default_factory=dict)

    # Roles and Tiers
    roles: dict[str, RoleDefinition] = field(default_factory=dict)
    admin_tiers: dict[str, int] = field(default_factory=dict)
    grantable_roles: dict[str, set[str]] = field(default_factory=dict)
    global_roles: set[str] = field(default_factory=set)
    scoped_roles: set[str] = field(default_factory=set)

    # Asset Mappings: App / DB -> OrgUnit
    app_to_org: dict[str, str] = field(default_factory=dict)
    app_to_sub_unit: dict[str, str] = field(default_factory=dict)
    db_to_org: dict[str, str] = field(default_factory=dict)
    db_to_sub_unit: dict[str, str] = field(default_factory=dict)

    # Demo seed personas for this profile
    demo_accounts: list[dict[str, Any]] = field(default_factory=list)

    # ------------------------------------------------------------------------
    # Lookup and Validation Helpers
    # ------------------------------------------------------------------------
    def get_level_label(self, level: int = 0) -> str:
        if 0 <= level < len(self.hierarchy_levels):
            return self.hierarchy_levels[level].label
        return f"Level {level}"

    def get_org_units_by_level(self, level: int = 0) -> dict[str, str]:
        """Returns {id: name} of all org units at a given hierarchy level."""
        return {
            uid: unit.name
            for uid, unit in self.org_units.items()
            if unit.level == level
        }

    def get_children(self, parent_id: str) -> dict[str, str]:
        """Returns {id: name} of immediate child units."""
        return {
            uid: unit.name
            for uid, unit in self.org_units.items()
            if unit.parent_id == parent_id
        }

    def tier_for_role(self, role: str) -> int:
        return self.admin_tiers.get(role, 0)

    def is_global_role(self, role: str) -> bool:
        return role in self.global_roles

    def is_scoped_role(self, role: str) -> bool:
        return role in self.scoped_roles

    def group_for_org_unit(self, org_id: str | None) -> str | None:
        if not org_id:
            return None
        unit = self.org_units.get(org_id)
        return unit.group_id if unit else None

    def org_units_for_group(self, group_id: str | None) -> list[str]:
        if not group_id:
            return []
        return [
            uid for uid, unit in self.org_units.items()
            if unit.group_id == group_id and unit.level == 0
        ]

    def org_unit_for_app(self, app_name: str | None) -> str | None:
        if not app_name:
            return None
        return self.app_to_org.get(str(app_name).lower())

    def sub_unit_for_app(self, app_name: str | None) -> str | None:
        if not app_name:
            return None
        return self.app_to_sub_unit.get(str(app_name).lower())

    def org_unit_for_db(self, db_name: str | None) -> str | None:
        if not db_name:
            return None
        return self.db_to_org.get(str(db_name).upper())

    def sub_unit_for_db(self, db_name: str | None) -> str | None:
        if not db_name:
            return None
        return self.db_to_sub_unit.get(str(db_name).upper())


class TenantProfileRegistry:
    """Global registry of tenant profiles with active profile management."""
    def __init__(self):
        self._profiles: dict[str, TenantProfile] = {}
        self._active_profile_id: str | None = None

    def register(self, profile: TenantProfile) -> None:
        self._profiles[profile.id] = profile
        logger.info("Registered tenant profile: %s ('%s')", profile.id, profile.name)

    def unregister(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            if self._active_profile_id == profile_id:
                self._active_profile_id = next(iter(self._profiles.keys()), None)
            logger.info("Unregistered tenant profile: %s", profile_id)
            return True
        return False

    def get(self, profile_id: str) -> TenantProfile | None:
        return self._profiles.get(profile_id)

    def get_active(self) -> TenantProfile:
        if self._active_profile_id in self._profiles:
            return self._profiles[self._active_profile_id]
        if self._profiles:
            return next(iter(self._profiles.values()))
        raise RuntimeError("No tenant profile registered in TenantProfileRegistry")

    def set_active(self, profile_id: str) -> TenantProfile:
        if profile_id not in self._profiles:
            raise ValueError(f"Unknown tenant profile: '{profile_id}'. Available: {list(self._profiles.keys())}")
        self._active_profile_id = profile_id
        logger.info("Switched active tenant profile to '%s'", profile_id)
        return self._profiles[profile_id]

    def list_profiles(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "client_type": p.client_type,
                "is_active": p.id == self._active_profile_id,
                "levels": [lvl.label for lvl in p.hierarchy_levels],
                "org_unit_count": len([u for u in p.org_units.values() if u.level == 0]),
                "sub_unit_count": len([u for u in p.org_units.values() if u.level > 0]),
                "group_count": len(p.groups),
                "control_plane": {
                    "directory_type": p.control_plane.directory_type,
                    "admin_ceiling_enforced": p.control_plane.admin_ceiling_enforced,
                    "lateral_isolation_enforced": p.control_plane.lateral_isolation_enforced,
                    "jwt_signing_algorithm": p.control_plane.jwt_signing_algorithm,
                },
                "data_plane": {
                    "fail_closed_sql": p.data_plane.fail_closed_sql,
                    "telemetry_sources": p.data_plane.telemetry_sources,
                    "risk_weights": p.data_plane.risk_weights,
                    "pii_masking_enabled": p.data_plane.pii_masking_enabled,
                    "compliance_frameworks": p.data_plane.compliance_frameworks,
                    "ingestion_adapters": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "category": a.category,
                            "protocol": a.protocol,
                            "weight": a.weight,
                            "enabled": a.enabled,
                            "description": a.description,
                        }
                        for a in p.data_plane.ingestion_adapters
                    ],
                    "supported_protocols": p.data_plane.supported_protocols,
                },
            }
            for p in self._profiles.values()
        ]


# Singleton instance
tenant_registry = TenantProfileRegistry()
