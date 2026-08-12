"""Synthetic OEM feed generator.

Produces realistic OEM-shaped payloads (matching each connector's poll()
output) so the M2/M3 pipeline, dashboards, tests and REST-served reports can
be developed and exercised while live OEM connectivity is pending.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.tenant import APP_DEPARTMENTS, DB_TO_DEPARTMENT

APPS = list(APP_DEPARTMENTS)
DB_NAMES = list(DB_TO_DEPARTMENT)

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
    return random.choice(seq)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class SyntheticOEMFeed:
    """Deterministic-seeded generator (set `seed` for reproducible fixtures)."""

    def __init__(self, seed: int | None = 42, now: datetime | None = None):
        self.rng = random.Random(seed)
        self.now = now or datetime.now(timezone.utc)

    def _id(self, prefix: str) -> str:
        return f"{prefix}-2026-{self.rng.randint(1000, 9999)}"

    def appscan_finding(self, days_ago: int | None = None) -> dict:
        dt = self.now - timedelta(
            days=self.rng.randint(0, days_ago or 30),
            hours=self.rng.randint(0, 23),
        )
        return {
            "id": self._id("ASC"),
            "application_name": _rand(APPS),
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

    def batch(self, source: str, count: int) -> list[dict]:
        if source == "appscan":
            return [self.appscan_finding() for _ in range(count)]
        if source in ("imperva_dam", "imperva"):
            return [self.imperva_dam_event() for _ in range(count)]
        if source == "imperva_waf":
            return [self.imperva_waf_event() for _ in range(count)]
        if source == "apisec":
            return [self.apisec_endpoint() for _ in range(count)]
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
