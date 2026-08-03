class AlertEnricher:
    def __init__(self):
        self.app_owners = {}

    def enrich(self, alert: dict) -> dict:
        enriched = dict(alert)
        app_name = alert.get("target_id", "")
        if app_name in self.app_owners:
            enriched["owner"] = self.app_owners[app_name]
        enriched["dashboard_link"] = f"/alerts/{alert.get('id', '')}"
        enriched["enriched_at"] = "now"
        return enriched
