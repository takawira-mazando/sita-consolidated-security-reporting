import aiohttp

class TeamsAdapter:
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url or ""

    async def send(self, alert: dict) -> bool:
        if not self.webhook_url:
            return False
        severity_colors = {"critical": "FF0000", "high": "FFA500", "medium": "0088FF", "low": "00CC00"}
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": severity_colors.get(alert.get("severity", ""), "888888"),
            "title": f"[{alert.get('severity','').upper()}] {alert.get('title','')}",
            "text": alert.get("description", ""),
            "sections": [{
                "facts": [
                    {"name": "Rule", "value": alert.get("rule_id", "")},
                    {"name": "Source", "value": alert.get("source", "")},
                    {"name": "Target", "value": alert.get("target_id", "")},
                ]
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View in SITA",
                "targets": [{"os": "default", "uri": alert.get("dashboard_link", "")}],
            }],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=card) as resp:
                return resp.status == 200
