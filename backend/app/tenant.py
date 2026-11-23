"""Generic platform role policy.

Client hierarchy levels and organization units are configured per tenant and
are not defined in this module.
"""

PLATFORM_SCOPE_ROLES = frozenset({"admin", "exec", "operator", "sre"})
SCOPED_COCKPIT_ROLES = frozenset({"appsec", "dbsec", "soc"})
TENANT_ADMIN_ROLES = frozenset({"tenant-admin", "transversal-admin"})

# Compatibility surfaces for legacy API payloads. They contain no bundled
# organization data; new hierarchy and unit records come from tenant workspaces.
DEPARTMENTS: dict[str, str] = {}
BRANCHES: dict[str, tuple[str, str]] = {}
PROVINCES: dict[str, str] = {}
PROVINCIAL_DEPARTMENTS: dict[str, tuple[str, str]] = {}
PROVINCE_DEPARTMENTS: dict[str, list[str]] = {}
DEPARTMENT_TO_PROVINCE: dict[str, str] = {}
DEPARTMENT_TO_MINISTRY: dict[str, str] = {}
MINISTRIES: dict[str, str] = {}
CLUSTERS: dict[str, str] = {}
MINISTRY_TO_CLUSTER: dict[str, str] = {}
APP_DEPARTMENTS: dict[str, str] = {}
APP_BRANCHES: dict[str, str] = {}
DB_TO_DEPARTMENT: dict[str, str] = {}
DB_TO_BRANCH: dict[str, str] = {}

NATIONWIDE_ROLES = PLATFORM_SCOPE_ROLES
DEPARTMENT_ROLES = SCOPED_COCKPIT_ROLES
PROVINCIAL_ROLES = frozenset()
OPERATIONAL_DEPARTMENT_ROLES = SCOPED_COCKPIT_ROLES


def provincial_departments_for_province(_scope_id: str | None) -> list[str]:
    return []


def province_for_department(_unit_id: str | None) -> str | None:
    return None


def is_provincial_department(_unit_id: str | None) -> bool:
    return False


def department_for_app(_app_name: str | None) -> str | None:
    return None


def department_for_db(_database_name: str | None) -> str | None:
    return None


def branch_for_app(_app_name: str | None) -> str | None:
    return None


def branch_for_db(_database_name: str | None) -> str | None:
    return None


def ministry_for_department(_unit_id: str | None) -> str | None:
    return None


def cluster_for_department(_unit_id: str | None) -> str | None:
    return None


def cluster_for_ministry(_portfolio_id: str | None) -> str | None:
    return None


def ministry_for_app(_app_name: str | None, _database_name: str | None = None) -> str | None:
    return None


def cluster_for_app(_app_name: str | None, _database_name: str | None = None) -> str | None:
    return None


def ministry_for_db(_database_name: str | None) -> str | None:
    return None


def cluster_for_db(_database_name: str | None) -> str | None:
    return None

ADMIN_TIERS = {
    "operator": 5,
    "admin": 4,
    "transversal-admin": 3,
}

SERVICE_AND_REPORTING_ROLES = SCOPED_COCKPIT_ROLES | {
    "ai",
    "compliance",
    "exec",
    "sre",
}

GRANTABLE_ROLES = {
    "operator": {"admin", "operator"},
    "admin": SERVICE_AND_REPORTING_ROLES | {"transversal-admin"},
    "transversal-admin": SERVICE_AND_REPORTING_ROLES,
    "sre": SCOPED_COCKPIT_ROLES,
}


def tier_for_role(role: str) -> int:
    """Return the administration tier for a platform role."""
    return ADMIN_TIERS.get(role, 0)
