from prometheus_client import Counter, Histogram, Gauge

connector_polls_total = Counter("connector_polls_total", "Total polls per connector", ["connector"])
connector_poll_duration = Histogram("connector_poll_duration_seconds", "Poll latency per connector", ["connector"], buckets=[1, 5, 10, 30, 60])
connector_errors_total = Counter("connector_errors_total", "Connector errors per source", ["connector", "error_type"])
records_ingested = Counter("records_ingested_total", "Records ingested per source", ["source"])
records_normalised = Counter("records_normalised_total", "Normalised records per outcome", ["outcome"])
risk_scores_computed = Gauge("risk_scores_computed_total", "Risk scores computed per app", ["app_name"])
alert_rules_fired = Counter("alert_rules_fired_total", "Alerts triggered per rule", ["rule_id", "severity"])
api_requests = Counter("api_requests_total", "API requests per route", ["method", "path", "status"])
api_duration = Histogram("api_duration_seconds", "API request duration", ["method", "path"], buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5])
active_alerts = Gauge("active_alerts_count", "Active alerts by severity", ["severity"])

def setup_metrics():
    pass
