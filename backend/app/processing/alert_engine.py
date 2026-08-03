import os
import uuid
from datetime import datetime, timezone

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.processing.alert_dedup import AlertDeduplicator
from app.processing.alert_enricher import AlertEnricher

ALERT_RULES_PATH = os.path.join(os.path.dirname(__file__), "alert_rules.yaml")


def _normalise_severity(value) -> str:
    value = str(value or "info").lower()
    if value not in {"critical", "high", "medium", "low", "info"}:
        return "info"
    return value


class AlertRuleEngine:
    def __init__(self, redis=None):
        self.rules = self._load_rules()
        self.deduplicator = AlertDeduplicator(redis=redis)
        self.enricher = AlertEnricher()

    def _load_rules(self) -> list[dict]:
        try:
            with open(ALERT_RULES_PATH) as f:
                return yaml.safe_load(f).get("rules", [])
        except (FileNotFoundError, yaml.YAMLError):
            return []

    async def evaluate(self, context: dict) -> list[dict]:
        """Record-level evaluation: match rules against a single normalized record."""
        alerts = []
        for rule in self.rules:
            cond = rule.get("condition", {})
            if cond.get("type") not in (None, "record", "record_match"):
                continue
            triggered = await self._match_record_rule(rule, context)
            for alert in triggered:
                if not await self.deduplicator.is_suppressed(
                    rule["id"],
                    alert.get("source", ""),
                    alert.get("target_id", ""),
                    alert.get("severity", "info"),
                    rule.get("throttle", {}).get("window_minutes", 60),
                    rule.get("throttle", {}).get("max_alerts", 1),
                ):
                    alerts.append(self.enricher.enrich(alert))
        return alerts

    async def evaluate_aggregate(self, session: AsyncSession) -> list[dict]:
        """Aggregate evaluation: run SQL-based rules against the warehouse."""
        alerts = []
        for rule in self.rules:
            cond = rule.get("condition", {})
            if cond.get("type") not in ("sql_query", "delta_query"):
                continue
            try:
                rows = await self._run_query(session, rule)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "rule %s query failed: %s", rule.get("id"), exc
                )
                await session.rollback()
                continue
            for row in rows:
                alert = self._build_alert(rule, row)
                if not await self.deduplicator.is_suppressed(
                    rule["id"],
                    alert.get("source", ""),
                    alert.get("target_id", ""),
                    alert.get("severity", "info"),
                    rule.get("throttle", {}).get("window_minutes", 60),
                    rule.get("throttle", {}).get("max_alerts", 1),
                ):
                    alerts.append(self.enricher.enrich(alert))
        return alerts

    async def _run_query(self, session: AsyncSession, rule: dict) -> list[dict]:
        cond = rule.get("condition", {})
        if cond.get("type") == "delta_query":
            result = await session.execute(text(cond["base_query"]))
            rows = [dict(r) for r in result.mappings().all()]
            if len(rows) < cond.get("min_delta", 1):
                return []
            return rows
        result = await session.execute(text(cond["query"]))
        return [dict(r) for r in result.mappings().all()]

    async def _match_record_rule(self, rule: dict, context: dict) -> list[dict]:
        cond = rule.get("condition", {})
        fields = cond.get("fields", {})
        mode = cond.get("match", "all")

        def value_matches(actual, expected):
            if isinstance(expected, (list, tuple)):
                return str(actual).lower() in {str(e).lower() for e in expected}
            return str(actual).lower() == str(expected).lower()

        matches = []
        for field, expected in fields.items():
            matches.append(value_matches(context.get(field), expected))
        triggered = all(matches) if mode == "all" else any(matches)
        if not triggered:
            return []
        return [self._build_alert(rule, context)]

    def _build_alert(self, rule: dict, row: dict) -> dict:
        now = datetime.now(timezone.utc)
        alert_id = str(uuid.uuid4())
        severity = _normalise_severity(row.get("severity") or rule.get("severity"))
        return {
            "id": alert_id,
            "rule_id": rule.get("id", "unknown"),
            "title": row.get("title") or rule.get("name", "Alert"),
            "description": row.get("description") or row.get("details"),
            "severity": severity,
            "source": row.get("source") or rule.get("source"),
            "target_id": row.get("target_id") or row.get("app_name") or row.get("application_name"),
            "status": "new",
            "first_triggered": now,
            "last_triggered": now,
            "dedup_key": f"{rule.get('id')}:{row.get('source', '')}:{row.get('target_id', '') or row.get('app_name', '')}",
        }
