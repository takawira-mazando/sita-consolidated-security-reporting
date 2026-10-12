"""Synthetic OEM feed generator.

Produces realistic OEM-shaped payloads (matching each connector's poll()
output) so the M2/M3 pipeline, dashboards, tests and REST-served reports can
be developed and exercised while live OEM connectivity is pending.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.tenant import (
    APP_DEPARTMENTS,
    DB_TO_DEPARTMENT,
    DHA_BRANCH_APPS,
    DHA_BRANCH_CASSANDRA_CLUSTERS,
)

APPS = list(APP_DEPARTMENTS)
DB_NAMES = list(DB_TO_DEPARTMENT)

# Flattened lists for random selection
DHA_APPS_FLAT = [app for apps in DHA_BRANCH_APPS.values() for app in apps]
DHA_CASSANDRA_FLAT = [cluster for clusters in DHA_BRANCH_CASSANDRA_CLUSTERS.values() for cluster in clusters]

OWASP_CATEGORIES = [
    "A01-broken-access-control",
    "A02-crypto-failures",
    "A03-injection",
    "A04-insecure-design",
    "A07-identification-auth-failures",
    "A09-security-logging-failures",
    "A10-ssrf",
]

SEVERITY_LEVELS = ["1 - Low", "2 - Medium", "3 - High", "4 - Critical"]

IMPERVA_SEVERITIES = ["Info", "Notice", "Warning", "Error", "Critical", "Emergency", "Alert"]

VIOLATION_TYPES = ["unauth_access", "sql_injection", "privilege_abuse", "data_exfil", "policy_other", "anomaly"]

ATTACK_TYPES = ["sqli", "xss", "rce", "lfi", "shellshock", "scanner-probe", "brute-force"]

DB_USERS = ["sa", "app_user", "etl_svc", "dba_admin", "reporting"]

THALES_SERVERS = ["172.31.82.207"]
THALES_KEYSPACES = ["select_keyspace"]
THALES_OPERATIONS = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"]
THALES_CATEGORIES = ["QUERY", "DML", "DDL", "ADMIN"]
THALES_CASSANDRA_CLUSTERS = ["CassandraVer401"]
THALES_SONAR_SOURCES = ["172.16.4.89_c5d8ad97-fccd-4841-90f6-df38824a67a0"]
THALES_DB_CLUSTER_NAME = "FlorenceCassandraCluster"
THALES_DB_USER = "florence_node1"

API_ENDPOINTS = [
    "/api/v1/pay",
    "/api/v1/refunds",
    "/api/v2/admin",
    "/api/v3/export",
    "/soap/login",
    "/api/v1/users/{id}",
    "/api/v1/orders",
]

COMPLIANCE_FRAMEWORKS = ["popia", "iso_27001"]


def _rand(seq):
    return random.choice(seq)  # nosec B311


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class SyntheticOEMFeed:
    """Deterministic-seeded generator (set `seed` for reproducible fixtures)."""

    def __init__(self, seed: int | None = 42, now: datetime | None = None):
        self.rng = random.Random(seed)  # nosec B311
        self.now = now or datetime.now(timezone.utc)

    def _id(self, prefix: str) -> str:
        return f"{prefix}-2026-{self.rng.randint(1000, 9999)}"

    def appscan_finding(self, days_ago: int | None = None, branch_id: str | None = None) -> dict:
        dt = self.now - timedelta(
            days=self.rng.randint(0, days_ago or 30),
            hours=self.rng.randint(0, 23),
        )
        # Use DHA branch-specific apps if branch_id provided and valid
        if branch_id and branch_id in DHA_BRANCH_APPS:
            apps = DHA_BRANCH_APPS[branch_id]
        elif branch_id and branch_id.startswith("dha-"):
            apps = DHA_APPS_FLAT
        else:
            apps = APPS
        return {
            "id": self._id("ASC"),
            "application_name": _rand(apps),
            "vulnerability_name": f"{_rand(OWASP_CATEGORIES)} finding",
            "description": "Synthetic AppScan vulnerability record for pipeline testing.",
            "owasp_category": _rand(OWASP_CATEGORIES),
            "severity": _rand(SEVERITY_LEVELS),
            "status": self.rng.choice(["Open", "In Progress", "Fixed", "Ignored"]),
            "first_found_date": _iso(dt - timedelta(days=self.rng.randint(1, 20))),
            "last_found_date": _iso(dt),
            "cve": self.rng.choice(["CVE-2026-31142", "CVE-2026-27815", "CVE-2026-29188", None]),
            "cvss": round(self.rng.uniform(3.0, 9.8), 1),
        }

    def imperva_dam_event(self) -> dict:
        dt = self.now - timedelta(minutes=self.rng.randint(0, 60 * 24))
        return {
            "event_id": self._id("DAM"),
            "database_name": _rand(DB_NAMES),
            "rule_name": _rand(VIOLATION_TYPES),
            "attack_type": _rand(ATTACK_TYPES),
            "violation_type": _rand(VIOLATION_TYPES),
            "severity": _rand(IMPERVA_SEVERITIES),
            "timestamp": _iso(dt),
            "db_user": _rand(DB_USERS),
            "source_ip": f"203.0.113.{self.rng.randint(1, 254)}",
            "rows_affected": self.rng.randint(0, 1_000_000),
        }

    def imperva_waf_event(self) -> dict:
        dt = self.now - timedelta(minutes=self.rng.randint(0, 60 * 24))
        return {
            "event_id": self._id("WAF"),
            "application_name": _rand(APPS),
            "attack_name": _rand(ATTACK_TYPES),
            "request_uri": _rand(API_ENDPOINTS),
            "attack_type": _rand(ATTACK_TYPES),
            "block_time": _iso(dt),
            "action": self.rng.choice(["block", "block", "log"]),
            "source_ip": f"198.51.100.{self.rng.randint(1, 254)}",
        }

    def apisec_endpoint(self) -> dict:
        dt = self.now - timedelta(days=self.rng.randint(0, 30))
        return {
            "api_id": self._id("API"),
            "application": _rand(APPS),
            "endpoint": _rand(API_ENDPOINTS),
            "method": _rand(["GET", "POST", "PUT", "DELETE"]),
            "exposure_score": round(self.rng.uniform(0, 100), 1),
            "is_shadow": self.rng.random() < 0.15,
            "issue_type": self.rng.choice(["shadow_api", "rate_limit", "auth_missing", "data_overexposure"]),
            "exposure_notes": "Synthetic API Security endpoint for pipeline testing.",
            "discovered_at": _iso(dt),
            "last_active": _iso(self.now - timedelta(hours=self.rng.randint(0, 72))),
        }

    def compliance_row(self) -> dict:
        framework = _rand(COMPLIANCE_FRAMEWORKS)
        control_id = (
            f"POPIA-{self.rng.randint(1, 99)}"
            if framework == "popia"
            else f"ISO-A.{self.rng.randint(5, 18)}.{self.rng.randint(1, 9)}"
        )
        return {
            "framework": framework,
            "control_id": control_id,
            "domain": _rand(["Data Inventory", "Consent", "Breach Response", "Access Control", "Operations"]),
            "description": "Synthetic compliance control record for pipeline testing.",
            "owner": _rand(["CISO", "DPO", "Legal", "IT Ops", "AppSec", "DB Sec"]),
            "severity": _rand(["low", "medium", "high", "critical"]),
            "due_date": _iso(self.now + timedelta(days=self.rng.randint(-20, 60)))[:10],
            "status": self.rng.choice(["open", "in_progress", "closed"]),
            "evidence_count": self.rng.randint(0, 10),
        }

    def _thales_severity(self, operation: str, failed_sqls: int) -> str:
        """Derive severity from operation type and failed SQL count."""
        if failed_sqls > 0:
            return "high"
        if operation in ("DELETE", "TRUNCATE", "DROP", "ALTER"):
            return "high"
        if operation in ("INSERT", "UPDATE"):
            return "medium"
        return "low"

    def thales_dam_event(self, branch_id: str | None = None) -> dict:
        """Generate a Thales/Imperva DAM SonarG format log matching the OEM sample."""
        dt = self.now - timedelta(minutes=self.rng.randint(0, 60 * 24))
        period_start = dt - timedelta(hours=self.rng.randint(1, 12))
        server_ip = THALES_SERVERS[0]
        server_host = f"ip-{server_ip.replace('.', '-')}.ec2.internal"
        client_ip = f"{self.rng.randint(1,255)}.{self.rng.randint(1,255)}.{self.rng.randint(1,255)}.{self.rng.randint(1,255)}"
        db_user = THALES_DB_USER
        keyspace = THALES_KEYSPACES[0]
        operation = _rand(THALES_OPERATIONS)
        category = _rand(THALES_CATEGORIES)
        
        # Use branch-specific Cassandra cluster if branch_id provided
        if branch_id and branch_id in DHA_BRANCH_CASSANDRA_CLUSTERS:
            cassandra_cluster = _rand(DHA_BRANCH_CASSANDRA_CLUSTERS[branch_id])
        elif branch_id and branch_id.startswith("dha-"):
            cassandra_cluster = _rand(DHA_CASSANDRA_FLAT)
        else:
            cassandra_cluster = THALES_CASSANDRA_CLUSTERS[0]
            
        sonar_source = THALES_SONAR_SOURCES[0]
        failed_sqls = self.rng.randint(0, 5)
        
        return {
            "_id": {"$oid": self.rng.choice([f"{self.rng.getrandbits(24):024x}" for _ in range(1)])},
            "Period Start": {"$date": _iso(period_start)},
            "dse node address": f"{server_ip}:7000",
            "asset_id": f"{server_host}:CASSANDRA::9042",
            "Analyzed Client IP": client_ip,
            "App User Name": None,
            "Client Host Name": f"{client_ip.replace('.', '-')}.bc.googleusercontent.com",
            "Client Port": self.rng.randint(10000, 65535),
            "Collection Platform": "Sonar",
            "DB Cluster ID": cassandra_cluster,
            "DB Cluster Name": cassandra_cluster,
            "DB User Name": db_user,
            "Database Name": None,
            "Failed Sqls": failed_sqls,
            "Gateway Event Time": {"$date": _iso(dt)},
            "Keyspace Name": keyspace,
            "OS User": None,
            "Objects and Verbs": f"{keyspace}.select_table {operation}",
            "Objects and Verbs Classifications": {
                "Audit Related": "NONE",
                "SQL Statement Type": "READ" if operation == "SELECT" else "WRITE"
            },
            "Original SQL": f"{operation} * from {keyspace}.select_table;",
            "Server Host Name": server_host,
            "Server IP": server_ip,
            "Server Port": 9042,
            "Server Type": "CASSANDRA",
            "Service Name": "",
            "SonarG Source": sonar_source,
            "Source Program": None,
            "Successful Sqls": self.rng.randint(1, 100),
            "Total Records Affected": -1 if operation == "SELECT" else self.rng.randint(1, 1000),
            "UTC Offset": 0,
            "vendor": "CASSANDRA",
            "Additional Fields": {
                "Logback Level": "INFO",
                "Logback Thread": f"Native-Transport-Requests-{self.rng.randint(1, 10)}",
                "Logback Date": period_start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "Logback Appender": "FileAuditLogger.java",
                "Logback Appender Line Number": str(self.rng.randint(40, 80)),
                "type": operation,
                "category": category,
                "scope": "select_table"
            },
            "severity": self._thales_severity(operation, failed_sqls),
            "__meta": {
                "input_line": f"INFO  [Native-Transport-Requests-{self.rng.randint(1,10)}] {period_start.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]} FileAuditLogger.java:{self.rng.randint(40,80)} - user:{db_user}|host:/{server_ip}:7000|source:/{client_ip}|port:{self.rng.randint(10000, 65535)}|timestamp:{int(period_start.timestamp()*1000)}|type:{operation}|category:{category}|ks:{keyspace}|scope:select_table|operation:{operation} * from {keyspace}.select_table; ",
                "instance_metadata": {
                    "cmd_line": "/data/jsonar/apps/4.11.0.0.0-rc5/bin/sonargateway --config remote://lmrmsonarg/gatewayetlservices?etl_service_id=cassandra  --default-log-file /data/jsonar/logs/gateway/syslog/cassandra.log --include-meta",
                    "id": f"gateway_{self.rng.randint(1000,9999)}_in{self.rng.randint(100,999)}",
                    "jsonar_uid": f"{self.rng.randint(10000000,99999999):08x}-{self.rng.randint(1000,9999):04x}-{self.rng.randint(1000,9999):04x}-{self.rng.randint(1000,9999):04x}-{self.rng.randint(100000000000,999999999999):012x}",
                    "jsonar_uid_display_name": "florencetlc-remote",
                    "gateway_build": "4.11.0-5",
                    "uts": {
                        "sysname": "Linux",
                        "nodename": f"ip-{server_ip.replace('.', '-')}.ec2.internal",
                        "release": "5.4.17-2136.309.5.el8uek.x86_64",
                        "machine": "x86_64",
                        "domainname": "(none)"
                    }
                }
            }
        }

    def batch(self, source: str, count: int, branch_id: str | None = None) -> list[dict]:
        # For DHA demo: distribute findings across branches if no specific branch given
        dha_branches = list(DHA_BRANCH_APPS.keys())
        
        if source == "appscan":
            if branch_id:
                return [self.appscan_finding(branch_id=branch_id) for _ in range(count)]
            # Distribute across DHA branches
            return [self.appscan_finding(branch_id=self.rng.choice(dha_branches)) for _ in range(count)]
        if source in ("imperva_dam", "imperva"):
            return [self.imperva_dam_event() for _ in range(count)]
        if source == "imperva_waf":
            return [self.imperva_waf_event() for _ in range(count)]
        if source == "apisec":
            return [self.apisec_endpoint() for _ in range(count)]
        if source == "thales":
            if branch_id:
                return [self.thales_dam_event(branch_id=branch_id) for _ in range(count)]
            # Distribute across DHA branches
            return [self.thales_dam_event(branch_id=self.rng.choice(dha_branches)) for _ in range(count)]
        if source == "compliance":
            return [self.compliance_row() for _ in range(count)]
        raise ValueError(f"unknown source: {source}")

    def sample(self, source: str, count: int = 3) -> list[dict]:
        """Small deterministic sample — used by fixtures/tests."""
        saved = self.rng.getstate()
        self.rng.seed(42)
        out = self.batch(source, count)
        self.rng.setstate(saved)
        return out
