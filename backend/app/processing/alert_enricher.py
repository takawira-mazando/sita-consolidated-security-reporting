"""Enrich alerts with application ownership, priority and navigation links.

Complements the AlertRuleEngine: after a rule fires, the enricher attaches
operational context (owner, team, priority, URLs) that the dispatch layer
(Teams/Email/PagerDuty) renders. Ownership is config-driven so it stays
maintainable as apps are onboarded.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import yaml

from app.tenant import APP_DEPARTMENTS, DB_TO_DEPARTMENT, DEPARTMENTS

SEVERITY_PRIORITY = {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5}

DEFAULT_APP_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "app_catalog.yaml")

DEFAULT_APPS = {
    "legacy-api": {"owner": "AppSec Engineer", "team": "AppSec", "tier": "P1"},
    "payment-gateway": {"owner": "Payment Ops", "team": "Payments", "tier": "P1"},
    "customer-portal": {"owner": "Web Platform", "team": "Digital", "tier": "P2"},
    "document-svc": {"owner": "Content Platform", "team": "Digital", "tier": "P2"},
    "internal-hr": {"owner": "HR Systems", "team": "Internal", "tier": "P3"},
}


class AlertEnricher:
    def __init__(self, app_catalog_path: str = DEFAULT_APP_CATALOG_PATH):
        self.app_owners = dict(DEFAULT_APPS)
        self._load_catalog(app_catalog_path)

    def _load_catalog(self, path: str) -> None:
        try:
            with open(path) as f:
                catalog = yaml.safe_load(f) or {}
            for app, info in (catalog.get("apps") or {}).items():
                entry = {k: v for k, v in (info or {}).items()}
                self.app_owners.setdefault(app, {}).update(entry)
        except FileNotFoundError:
            pass

    def _owner_for(self, app_name: str) -> dict:
        if app_name in self.app_owners:
            return self.app_owners[app_name]
        dept_id = APP_DEPARTMENTS.get(str(app_name).lower()) or DB_TO_DEPARTMENT.get(str(app_name).upper())
        if dept_id:
            return {
                "owner": DEPARTMENTS.get(dept_id, dept_id),
                "team": "SITA SOC",
                "tier": "P2",
            }
        return {"owner": "Unassigned", "team": "Unassigned", "tier": "P3"}

    def enrich(self, alert: dict) -> dict:
        enriched = dict(alert)
        app_name = alert.get("target_id") or alert.get("app_name") or ""
        info = self._owner_for(app_name)
        severity = str(alert.get("severity") or "info").lower()
        alert_id = alert.get("id") or ""
        external_id = alert.get("external_id") or alert.get("target_id") or ""
        enriched_data = {
            "owner": info.get("owner", "Unassigned"),
            "team": info.get("team", "Unassigned"),
            "tier": info.get("tier", "P3"),
            "priority": SEVERITY_PRIORITY.get(severity, 5),
            "external_id": external_id,
            "dashboard_link": f"/alerts/{alert_id}",
            "enriched_at": datetime.now(timezone.utc).isoformat(),
        }
        enriched["enriched_data"] = enriched_data
        enriched.update(enriched_data)
        return enriched
