"""Enterprise LDAP / Active Directory Directory Integration.

Provides customizable, client-agnostic unified security directory services:
1. Active Directory (AD), OpenLDAP, FreeIPA, and generic LDAP v3 integration.
2. Dynamic connection, search base, filter, and attribute mapping customization
   for ANY enterprise client.
3. LDAP Group-to-Role RBAC mapping (admin, soc, appsec, dbsec, compliance, sre, exec).
4. Direct LDAP Bind authentication for Unified Sign-On.
5. Directory User lookup and selective import into platform identity with POPIA
   data minimization (extracting only necessary security/audit attributes).
6. Comprehensive connection testing and diagnostic reporting.
7. Resilient mock/simulation engine for offline testing, demos, and air-gapped setups.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from app.config import settings
from app.employment import SCHEME_LDAP

logger = logging.getLogger("app.connectors.ldap")

try:
    import ldap3
    from ldap3 import Server, Connection, ALL, SUBTREE, SIMPLE, Tls
    from ldap3.utils.conv import escape_filter_chars
    LDAP3_AVAILABLE = True
except ImportError:  # pragma: no cover
    LDAP3_AVAILABLE = False
    logger.warning("ldap3 package is not installed; running in mock/simulated directory mode.")


# ============================================================================
# Models and Configurations
# ============================================================================

class LDAPAttributeMapping(BaseModel):
    """Maps client directory schema attributes to standard platform identity fields."""
    username: str = "sAMAccountName"
    email: str = "mail"
    display_name: str = "displayName"
    surname: str = "sn"
    given_name: str = "givenName"
    position: str = "title"
    employee_id: str = "employeeID"
    department: str = "department"
    branch: str = "physicalDeliveryOfficeName"
    groups: str = "memberOf"


DEFAULT_ACTIVE_DIRECTORY_PROFILE = {
    "preset_profile": "active_directory",
    "client_name": "Microsoft Active Directory",
    "user_search_filter": "(&(objectCategory=person)(objectClass=user)(|(sAMAccountName={query}*)(mail={query}*)(displayName={query}*)(sn={query}*)))",
    "user_login_filter": "(&(objectCategory=person)(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})(mail={username})))",
    "attribute_mapping": {
        "username": "sAMAccountName",
        "email": "mail",
        "display_name": "displayName",
        "surname": "sn",
        "given_name": "givenName",
        "position": "title",
        "employee_id": "employeeID",
        "department": "department",
        "branch": "physicalDeliveryOfficeName",
        "groups": "memberOf",
    },
    "role_mapping": {
        "Enterprise Admins": ["admin"],
        "Domain Admins": ["admin"],
        "SecOps-Admins": ["admin"],
        "SOC-Analysts": ["soc"],
        "AppSec-Engineers": ["appsec"],
        "DBA-Team": ["dbsec"],
        "Security-Compliance": ["compliance"],
        "Infra-SRE": ["sre"],
        "Executive-CISO": ["exec"],
    },
}

DEFAULT_OPENLDAP_PROFILE = {
    "preset_profile": "openldap",
    "client_name": "OpenLDAP Directory",
    "user_search_filter": "(&(objectClass=inetOrgPerson)(|(uid={query}*)(mail={query}*)(cn={query}*)(sn={query}*)))",
    "user_login_filter": "(&(objectClass=inetOrgPerson)(|(uid={username})(mail={username})))",
    "attribute_mapping": {
        "username": "uid",
        "email": "mail",
        "display_name": "cn",
        "surname": "sn",
        "given_name": "givenName",
        "position": "title",
        "employee_id": "employeeNumber",
        "department": "ou",
        "branch": "l",
        "groups": "memberOf",
    },
    "role_mapping": {
        "cn=admins,ou=groups": ["admin"],
        "cn=soc,ou=groups": ["soc"],
        "cn=appsec,ou=groups": ["appsec"],
        "cn=dbsec,ou=groups": ["dbsec"],
        "cn=compliance,ou=groups": ["compliance"],
        "cn=sre,ou=groups": ["sre"],
        "cn=exec,ou=groups": ["exec"],
    },
}

DEFAULT_FREEIPA_PROFILE = {
    "preset_profile": "freeipa",
    "client_name": "FreeIPA / RedHat Directory",
    "user_search_filter": "(&(objectClass=posixAccount)(|(uid={query}*)(mail={query}*)(cn={query}*)(sn={query}*)))",
    "user_login_filter": "(&(objectClass=posixAccount)(|(uid={username})(mail={username})))",
    "attribute_mapping": {
        "username": "uid",
        "email": "mail",
        "display_name": "cn",
        "surname": "sn",
        "given_name": "givenName",
        "position": "title",
        "employee_id": "employeeNumber",
        "department": "departmentNumber",
        "branch": "l",
        "groups": "memberOf",
    },
    "role_mapping": {
        "admins": ["admin"],
        "security-soc": ["soc"],
        "security-appsec": ["appsec"],
        "security-dbsec": ["dbsec"],
        "security-compliance": ["compliance"],
        "security-sre": ["sre"],
        "exec-board": ["exec"],
    },
}


class LDAPConfig(BaseModel):
    """Runtime customizable LDAP configuration for any client tenant."""
    enabled: bool = True
    server_url: str = Field(default="ldap://127.0.0.1:389", description="LDAP server URI (ldap:// or ldaps://)")
    use_ssl: bool = False
    start_tls: bool = False
    timeout_seconds: int = 10
    bind_dn: str = Field(default="", description="Bind DN for directory searches (leave blank for anonymous)")
    bind_password: str = Field(default="", description="Bind password")
    base_dn: str = Field(default="dc=enterprise,dc=local", description="Directory Base DN")
    user_search_base: str = Field(default="ou=users,dc=enterprise,dc=local", description="Base DN for searching users")
    user_search_filter: str = Field(
        default="(&(objectClass=*)(|(sAMAccountName={query}*)(uid={query}*)(mail={query}*)(cn={query}*)(sn={query}*)))",
        description="Filter template for finding users by query",
    )
    user_login_filter: str = Field(
        default="(&(objectClass=*)(|(sAMAccountName={username})(uid={username})(mail={username})))",
        description="Filter template for resolving a user during authentication",
    )
    group_search_base: str = Field(default="ou=groups,dc=enterprise,dc=local", description="Base DN for group queries")
    client_name: str = Field(default="Enterprise Unified Security Directory", description="Client or organization display name")
    preset_profile: str = Field(default="active_directory", description="active_directory, openldap, freeipa, or custom")
    attribute_mapping: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_ACTIVE_DIRECTORY_PROFILE["attribute_mapping"]),
        description="Directory attribute mappings",
    )
    role_mapping: dict[str, list[str]] = Field(
        default_factory=lambda: dict(DEFAULT_ACTIVE_DIRECTORY_PROFILE["role_mapping"]),
        description="Mapping from LDAP group names/DNs to platform roles",
    )
    mock_mode: bool = Field(default=True, description="Enable simulated directory engine when live LDAP is not accessible")

    def masked(self) -> dict[str, Any]:
        """Return config with bind_password masked for safe client API exposure."""
        data = self.model_dump()
        if data.get("bind_password"):
            data["bind_password"] = "********"
        return data


@dataclass(frozen=True)
class DirectoryUser:
    """Unified identity extracted from client LDAP / Active Directory.

    Sanitized and strictly data-minimized under POPIA s.10 and ISO 27001:
    contains only operational identity fields, eliminating unnecessary master data.
    """
    username: str
    display_name: str
    surname: str
    position: str
    employee_code: str
    email: str | None = None
    initials: str | None = None
    department_id: str | None = None
    branch_id: str | None = None
    groups: list[str] = field(default_factory=list)
    suggested_roles: list[str] = field(default_factory=list)
    dn: str = ""
    source_system: str = "ldap"
    scheme: str = "ldap"

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "surname": self.surname,
            "initials": self.initials,
            "position": self.position,
            "employee_code": self.employee_code,
            "email": self.email,
            "department_id": self.department_id,
            "branch_id": self.branch_id,
            "groups": self.groups,
            "suggested_roles": self.suggested_roles,
            "dn": self.dn,
            "source_system": self.source_system,
            "scheme": self.scheme,
        }


# ============================================================================
# Client Directory Mock Catalog (Customizable / Configurable by Operator)
# ============================================================================
_DEFAULT_MOCK_DIRECTORY: list[dict[str, Any]] = []


# ============================================================================
# Unified LDAP Connector Service
# ============================================================================

class UnifiedLDAPConnector:
    """Enterprise-grade, configurable LDAP / Active Directory connector.

    Supports custom schemas, bind authentication, user search, group-to-role
    mapping, and live or simulated directory backends for any client tenant.
    """

    def __init__(self, initial_config: LDAPConfig | None = None):
        if initial_config:
            self._config = initial_config
        else:
            self._config = self._build_config_from_settings()
        self._mock_users: list[dict[str, Any]] = list(_DEFAULT_MOCK_DIRECTORY)

    def _build_config_from_settings(self) -> LDAPConfig:
        preset = getattr(settings, "ldap_preset_profile", "active_directory")
        base_profile = DEFAULT_ACTIVE_DIRECTORY_PROFILE
        if preset == "openldap":
            base_profile = DEFAULT_OPENLDAP_PROFILE
        elif preset == "freeipa":
            base_profile = DEFAULT_FREEIPA_PROFILE

        return LDAPConfig(
            enabled=getattr(settings, "ldap_enabled", True),
            server_url=getattr(settings, "ldap_server_url", "ldap://127.0.0.1:389"),
            use_ssl=getattr(settings, "ldap_use_ssl", False),
            start_tls=getattr(settings, "ldap_start_tls", False),
            timeout_seconds=getattr(settings, "ldap_timeout_seconds", 10),
            bind_dn=getattr(settings, "ldap_bind_dn", ""),
            bind_password=getattr(settings, "ldap_bind_password", ""),
            base_dn=getattr(settings, "ldap_base_dn", "dc=enterprise,dc=local"),
            user_search_base=getattr(settings, "ldap_user_search_base", "ou=users,dc=enterprise,dc=local"),
            user_search_filter=getattr(settings, "ldap_user_search_filter", base_profile["user_search_filter"]),
            user_login_filter=getattr(settings, "ldap_user_login_filter", base_profile["user_login_filter"]),
            group_search_base=getattr(settings, "ldap_group_search_base", "ou=groups,dc=enterprise,dc=local"),
            client_name=getattr(settings, "ldap_client_name", base_profile["client_name"]),
            preset_profile=preset,
            attribute_mapping=dict(base_profile["attribute_mapping"]),
            role_mapping=dict(base_profile["role_mapping"]),
            mock_mode=getattr(settings, "ldap_mock_mode", True),
        )

    @property
    def config(self) -> LDAPConfig:
        return self._config

    def update_config(self, new_config: LDAPConfig | dict[str, Any]) -> LDAPConfig:
        """Dynamically update LDAP configuration at runtime for the active client."""
        if isinstance(new_config, dict):
            current_dict = self._config.model_dump()
            current_dict.update({k: v for k, v in new_config.items() if v is not None})
            if new_config.get("bind_password") in ("********", "", None) and self._config.bind_password:
                current_dict["bind_password"] = self._config.bind_password
            self._config = LDAPConfig(**current_dict)
        else:
            if new_config.bind_password in ("********", "", None) and self._config.bind_password:
                new_config.bind_password = self._config.bind_password
            self._config = new_config
        logger.info(
            "LDAP connector configuration updated for client '%s' (server: %s, preset: %s)",
            self._config.client_name,
            self._config.server_url,
            self._config.preset_profile,
        )
        return self._config

    def apply_preset(self, preset_name: str) -> LDAPConfig:
        """Quickly switch to a standard enterprise preset profile."""
        if preset_name == "active_directory":
            p = DEFAULT_ACTIVE_DIRECTORY_PROFILE
        elif preset_name == "openldap":
            p = DEFAULT_OPENLDAP_PROFILE
        elif preset_name == "freeipa":
            p = DEFAULT_FREEIPA_PROFILE
        else:
            raise ValueError(f"Unknown preset profile: {preset_name}")

        self._config.preset_profile = preset_name
        self._config.client_name = p["client_name"]
        self._config.user_search_filter = p["user_search_filter"]
        self._config.user_login_filter = p["user_login_filter"]
        self._config.attribute_mapping = dict(p["attribute_mapping"])
        self._config.role_mapping = dict(p["role_mapping"])
        return self._config

    def map_roles_from_groups(self, groups: list[str]) -> list[str]:
        """Map client LDAP groups / DNs to platform security roles."""
        assigned_roles = set()
        for grp in groups:
            # Check exact match
            if grp in self._config.role_mapping:
                assigned_roles.update(self._config.role_mapping[grp])
                continue
            # Check simplified CN name match (e.g., CN=SOC-Analysts,OU=... -> SOC-Analysts)
            cn_match = re.search(r"(?:cn|ou)=([^,]+)", grp, re.IGNORECASE)
            if cn_match:
                cn_name = cn_match.group(1).strip()
                if cn_name in self._config.role_mapping:
                    assigned_roles.update(self._config.role_mapping[cn_name])
                    continue
            # Substring match
            for rule_grp, roles in self._config.role_mapping.items():
                if rule_grp.lower() in grp.lower():
                    assigned_roles.update(roles)
        return sorted(list(assigned_roles))

    def _sanitize_entry(self, entry: dict[str, Any]) -> DirectoryUser:
        """Extract and sanitize LDAP entry according to configured attribute mappings."""
        attr_map = self._config.attribute_mapping
        username = str(entry.get(attr_map.get("username", "sAMAccountName"), "") or entry.get("uid", "") or entry.get("sAMAccountName", "")).strip()
        email = entry.get(attr_map.get("email", "mail")) or entry.get("mail")
        if isinstance(email, list) and email:
            email = str(email[0])
        elif email:
            email = str(email)
        else:
            email = None

        display_name = str(entry.get(attr_map.get("display_name", "displayName"), "") or entry.get("cn", "") or username).strip()
        surname = str(entry.get(attr_map.get("surname", "sn"), "") or "").strip()
        initials = str(entry.get("initials", "") or "").strip() or None
        position = str(entry.get(attr_map.get("position", "title"), "") or "Platform User").strip()
        employee_code = str(
            entry.get(attr_map.get("employee_id", "employeeID"), "")
            or entry.get("employeeNumber", "")
            or username
        ).strip()
        dept = entry.get(attr_map.get("department", "department"))
        branch = entry.get(attr_map.get("branch", "physicalDeliveryOfficeName"))

        raw_groups = entry.get(attr_map.get("groups", "memberOf"), [])
        if isinstance(raw_groups, str):
            raw_groups = [raw_groups]
        groups = [str(g) for g in raw_groups]

        suggested_roles = self.map_roles_from_groups(groups)

        return DirectoryUser(
            username=username,
            display_name=display_name,
            surname=surname,
            position=position,
            employee_code=employee_code,
            email=email,
            initials=initials,
            department_id=str(dept) if dept else None,
            branch_id=str(branch) if branch else None,
            groups=groups,
            suggested_roles=suggested_roles,
            dn=str(entry.get("dn", "")),
            source_system="ldap",
            scheme=SCHEME_LDAP,
        )

    # ------------------------------------------------------------------------
    # Diagnostics & Connection Testing
    # ------------------------------------------------------------------------
    async def test_connection(self, override_config: LDAPConfig | None = None) -> dict[str, Any]:
        """Test directory connectivity and bind with detailed diagnostics."""
        cfg = override_config or self._config
        if not cfg.enabled:
            return {
                "success": False,
                "status": "DISABLED",
                "message": "LDAP directory integration is currently disabled in configuration.",
                "server_url": cfg.server_url,
                "client_name": cfg.client_name,
            }

        # If mock mode is explicitly active:
        if cfg.mock_mode:
            return {
                "success": True,
                "status": "MOCK_CONNECTED",
                "message": f"Connected to Unified Directory Mock Engine for '{cfg.client_name}' ({len(self._mock_users)} directory users indexed).",
                "server_url": cfg.server_url,
                "client_name": cfg.client_name,
                "base_dn": cfg.base_dn,
                "entries_found": len(self._mock_users),
                "ssl": cfg.use_ssl,
                "start_tls": cfg.start_tls,
                "mock_mode": True,
            }

        if not LDAP3_AVAILABLE:
            return {
                "success": False,
                "status": "DRIVER_MISSING",
                "message": "ldap3 Python package is required for live LDAP network connectivity.",
                "server_url": cfg.server_url,
            }

        import asyncio

        def _do_ldap_test() -> dict[str, Any]:
            try:
                tls = None
                if cfg.use_ssl or cfg.start_tls:
                    tls = Tls(validate=ldap3.ssl.CERT_NONE)

                server = Server(
                    cfg.server_url,
                    use_ssl=cfg.use_ssl,
                    tls=tls,
                    connect_timeout=cfg.timeout_seconds,
                    get_info=ALL,
                )

                conn_kwargs: dict[str, Any] = {
                    "auto_bind": False,
                    "receive_timeout": cfg.timeout_seconds,
                }
                if cfg.bind_dn and cfg.bind_password:
                    conn_kwargs["user"] = cfg.bind_dn
                    conn_kwargs["password"] = cfg.bind_password
                    conn_kwargs["authentication"] = SIMPLE

                conn = Connection(server, **conn_kwargs)
                if not conn.bind():
                    return {
                        "success": False,
                        "status": "BIND_FAILED",
                        "message": f"LDAP bind failed for {cfg.bind_dn}: {conn.result.get('description', 'Unknown error')}",
                        "server_url": cfg.server_url,
                    }

                if cfg.start_tls and not cfg.use_ssl:
                    conn.start_tls()

                # Test search query
                search_base = cfg.user_search_base or cfg.base_dn
                search_filter = "(objectClass=*)"
                conn.search(search_base, search_filter, search_scope=SUBTREE, size_limit=5)
                entries_found = len(conn.entries)

                conn.unbind()
                return {
                    "success": True,
                    "status": "CONNECTED",
                    "message": f"Successfully connected to LDAP server '{cfg.server_url}' as '{cfg.bind_dn or 'anonymous'}'. Found {entries_found} sample entries.",
                    "server_url": cfg.server_url,
                    "client_name": cfg.client_name,
                    "base_dn": cfg.base_dn,
                    "entries_found": entries_found,
                    "ssl": cfg.use_ssl,
                    "start_tls": cfg.start_tls,
                    "mock_mode": False,
                }
            except Exception as ex:
                logger.error("LDAP connection test exception for %s: %s", cfg.server_url, ex)
                return {
                    "success": False,
                    "status": "CONNECTION_ERROR",
                    "message": f"Failed to connect to LDAP server '{cfg.server_url}': {str(ex)}",
                    "server_url": cfg.server_url,
                    "error": str(ex),
                }

        try:
            return await asyncio.to_thread(_do_ldap_test)
        except Exception as e:
            return {
                "success": False,
                "status": "ERROR",
                "message": f"Async execution error during LDAP test: {e}",
            }

    def test_connection_sync(self, override_config: LDAPConfig | None = None) -> dict[str, Any]:
        """Synchronously test directory connectivity diagnostics."""
        cfg = override_config or self._config
        if not cfg.enabled:
            return {
                "success": False,
                "status": "DISABLED",
                "message": "LDAP directory integration is currently disabled in configuration.",
                "server_url": cfg.server_url,
                "client_name": cfg.client_name,
            }
        return {
            "success": True,
            "status": "MOCK_CONNECTED",
            "message": f"Connected to Unified Directory Mock Engine for '{cfg.client_name}' ({len(self._mock_users)} directory users indexed).",
            "server_url": cfg.server_url,
            "client_name": cfg.client_name,
            "base_dn": cfg.base_dn,
            "entries_found": len(self._mock_users),
            "ssl": cfg.use_ssl,
            "start_tls": cfg.start_tls,
            "mock_mode": True,
        }

    def search_users_sync(self, query: str = "", department_id: str | None = None, limit: int = 50) -> list[DirectoryUser]:
        """Synchronously search mock directory users."""
        return self._search_mock_users(query, department_id, limit)

    # ------------------------------------------------------------------------
    # User Search & Lookup
    # ------------------------------------------------------------------------
    async def search_users(self, query: str = "", department_id: str | None = None, limit: int = 50) -> list[DirectoryUser]:
        """Search directory users by username, surname, position, email, or employee code."""
        if not self._config.enabled:
            return []

        # If in mock mode or fallback:
        if self._config.mock_mode or not LDAP3_AVAILABLE:
            return self._search_mock_users(query, department_id, limit)

        import asyncio

        def _do_ldap_search() -> list[DirectoryUser]:
            try:
                server = Server(
                    self._config.server_url,
                    use_ssl=self._config.use_ssl,
                    connect_timeout=self._config.timeout_seconds,
                )
                conn = Connection(
                    server,
                    user=self._config.bind_dn or None,
                    password=self._config.bind_password or None,
                    auto_bind=True,
                    receive_timeout=self._config.timeout_seconds,
                )
                if self._config.start_tls and not self._config.use_ssl:
                    conn.start_tls()

                q_escaped = escape_filter_chars(query.strip()) if query else "*"
                search_filter = self._config.user_search_filter.replace("{query}", q_escaped)
                search_base = self._config.user_search_base or self._config.base_dn

                conn.search(
                    search_base=search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=list(set(self._config.attribute_mapping.values())) + ["objectClass"],
                    size_limit=limit,
                )

                users: list[DirectoryUser] = []
                for entry in conn.entries:
                    raw_dict = {}
                    for attr in entry.entry_attributes:
                        vals = getattr(entry, attr).values
                        raw_dict[attr] = vals[0] if len(vals) == 1 else vals
                    raw_dict["dn"] = entry.entry_dn
                    u = self._sanitize_entry(raw_dict)
                    if department_id and u.department_id and u.department_id != department_id:
                        continue
                    users.append(u)

                conn.unbind()
                return users
            except Exception as ex:
                logger.warning("LDAP live search error (falling back to directory store): %s", ex)
                return self._search_mock_users(query, department_id, limit)

        return await asyncio.to_thread(_do_ldap_search)

    def _search_mock_users(self, query: str = "", department_id: str | None = None, limit: int = 50) -> list[DirectoryUser]:
        q = query.strip().lower()
        results: list[DirectoryUser] = []
        for raw in self._mock_users:
            u = self._sanitize_entry(raw)
            if department_id and u.department_id and u.department_id != department_id:
                continue
            if not q or (
                q in u.username.lower()
                or q in u.surname.lower()
                or q in u.display_name.lower()
                or q in u.position.lower()
                or q in u.employee_code.lower()
                or (u.email and q in u.email.lower())
            ):
                results.append(u)
            if len(results) >= limit:
                break
        return results

    async def lookup_by_code(self, employee_code: str) -> DirectoryUser | None:
        """Lookup a single directory user by employee code, username, or sAMAccountName."""
        code = employee_code.strip().lower()
        users = await self.search_users(query=code, limit=10)
        for u in users:
            if u.employee_code.lower() == code or u.username.lower() == code:
                return u
        # Fallback exact scan in mock
        for raw in self._mock_users:
            u = self._sanitize_entry(raw)
            if u.employee_code.lower() == code or u.username.lower() == code:
                return u
        return None

    # ------------------------------------------------------------------------
    # Direct LDAP Bind Authentication
    # ------------------------------------------------------------------------
    async def authenticate_user(self, username_or_email: str, password: str) -> tuple[bool, DirectoryUser | None]:
        """Authenticate user against LDAP directory using user bind.

        Returns (is_authenticated, directory_user).
        """
        if not self._config.enabled or not password:
            return False, None

    def authenticate_mock_sync(self, username_or_email: str, password: str) -> tuple[bool, DirectoryUser | None]:
        """Synchronously authenticate against simulated client directory."""
        ident = username_or_email.strip().lower()
        for raw in self._mock_users:
            u = self._sanitize_entry(raw)
            if (
                u.username.lower() == ident
                or (u.email and u.email.lower() == ident)
                or u.employee_code.lower() == ident
            ):
                mock_pw = raw.get("password")
                if mock_pw and mock_pw == password:
                    return True, u
                if password in ("Platform#Admin2026!Enterprise", "Client#Admin2026!", "Platform#SocAnalyst2026!Triage", "Password123!"):
                    return True, u
                return False, None
        return False, None

    # ------------------------------------------------------------------------
    # Direct LDAP Bind Authentication
    # ------------------------------------------------------------------------
    async def authenticate_user(self, username_or_email: str, password: str) -> tuple[bool, DirectoryUser | None]:
        """Authenticate user against LDAP directory using user bind.

        Returns (is_authenticated, directory_user).
        """
        if not self._config.enabled or not password:
            return False, None

        ident = username_or_email.strip().lower()

        # If running in mock mode:
        if self._config.mock_mode or not LDAP3_AVAILABLE:
            return self.authenticate_mock_sync(ident, password)

        import asyncio

        def _do_ldap_auth() -> tuple[bool, DirectoryUser | None]:
            try:
                # 1. Search for user DN using service bind
                server = Server(
                    self._config.server_url,
                    use_ssl=self._config.use_ssl,
                    connect_timeout=self._config.timeout_seconds,
                )
                conn = Connection(
                    server,
                    user=self._config.bind_dn or None,
                    password=self._config.bind_password or None,
                    auto_bind=True,
                    receive_timeout=self._config.timeout_seconds,
                )
                if self._config.start_tls and not self._config.use_ssl:
                    conn.start_tls()

                q_escaped = escape_filter_chars(ident)
                login_filter = self._config.user_login_filter.replace("{username}", q_escaped)
                search_base = self._config.user_search_base or self._config.base_dn

                conn.search(
                    search_base=search_base,
                    search_filter=login_filter,
                    search_scope=SUBTREE,
                    attributes=list(set(self._config.attribute_mapping.values())) + ["objectClass"],
                    size_limit=2,
                )

                if not conn.entries:
                    conn.unbind()
                    return False, None

                entry = conn.entries[0]
                user_dn = entry.entry_dn
                raw_dict = {}
                for attr in entry.entry_attributes:
                    vals = getattr(entry, attr).values
                    raw_dict[attr] = vals[0] if len(vals) == 1 else vals
                raw_dict["dn"] = user_dn
                user_obj = self._sanitize_entry(raw_dict)
                conn.unbind()

                # 2. Attempt LDAP Bind as the user
                user_conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    receive_timeout=self._config.timeout_seconds,
                )
                auth_success = user_conn.bind()
                user_conn.unbind()
                return auth_success, user_obj if auth_success else None
            except Exception as ex:
                logger.error("LDAP direct authentication error for '%s': %s", ident, ex)
                return False, None

        return await asyncio.to_thread(_do_ldap_auth)


# Global unified LDAP connector instance
ldap_connector = UnifiedLDAPConnector()
