import aiohttp

from app.monitoring.egress import EgressNotPermitted, check


class PagerDutyAdapter:
    def __init__(self, routing_key: str = ""):
        self.routing_key = routing_key or ""

    async def send(self, alert: dict) -> bool:
        if not self.routing_key:
            return False
        # Egress gate: PagerDuty is a cross-border push of SA government
        # security-event content to a US SaaS endpoint. Returning False rather
        # than raising keeps an unregistered destination from breaking the
        # dispatch worker, while refusing to send.
        try:
            check("pagerduty")
        except EgressNotPermitted:
            return False
        severity_map = {"critical": "critical", "high": "error", "medium": "warning", "low": "info"}
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.get("id", ""),
            "payload": {
                "summary": alert.get("title", ""),
                "severity": severity_map.get(alert.get("severity", ""), "info"),
                "source": alert.get("source", "sita-platform"),
                "component": alert.get("rule_id", ""),
                "custom_details": {
                    "description": alert.get("description", ""),
                    "target": alert.get("target_id", ""),
                },
            },
        }
        async with aiohttp.ClientSession() as session, session.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload,
        ) as resp:
            return resp.status == 202
