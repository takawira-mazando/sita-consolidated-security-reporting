"""Seed REAL AppScan findings from HCL AppScan Cloud into warehouse with Thales tenancy."""
import asyncio
import json
from datetime import datetime, timezone

from app.db import SessionFactory
from app.lake.writer import upsert_findings
from app.processing.normaliser import Normaliser
from app.tenant import department_for_app, branch_for_app

def _serialize_for_json(obj):
    """Convert pandas Timestamps and other non-JSON types to strings."""
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    elif hasattr(obj, 'isoformat'):  # datetime, Timestamp
        return obj.isoformat()
    elif hasattr(obj, '__str__') and type(obj).__name__ == 'Timestamp':
        return str(obj)
    return obj

async def seed_real_appscan():
    # Load real issues
    with open('C:/sita-platform/backend/appscan_real_issues.json', 'r') as f:
        real_issues = json.load(f)
    
    print(f'Loaded {len(real_issues)} real AppScan issues')
    
    # Convert to format expected by normalizer (matches field_mapper.yaml appscan mapping)
    records = []
    for issue in real_issues:
        # Map AppScan Cloud fields to connector's expected fields
        raw_issue = _serialize_for_json(issue)
        record = {
            "source": "appscan",
            "external_id": str(issue.get("Id")),
            "application_name": "XYZ Application",  # Maps to home-affairs-digital / dha-digital
            "vulnerability_name": issue.get("IssueType"),
            "description": f"{issue.get('IssueType')} found at {issue.get('Location')}",
            "owasp_category": f"CWE-{issue.get('Cwe')}" if issue.get('Cwe') else None,
            "severity": issue.get("Severity"),  # "Critical", "High", "Medium", "Low", "Informational"
            "status": issue.get("Status", "Open"),
            "first_found_date": issue.get("DateCreated"),
            "last_found_date": issue.get("LastFound") or issue.get("LastUpdated"),
            "cve": issue.get("Cve"),
            "cvss": issue.get("Cvss"),
            "raw_data": raw_issue,
        }
        records.append(record)
    
    print(f'Converted {len(records)} records')
    
    # Normalize
    normaliser = Normaliser()
    import pandas as pd
    df = normaliser.normalise(pd.DataFrame(records), 'appscan')
    if df is None or df.empty:
        print('Normaliser produced no rows')
        return
    
    rows = df.to_dict(orient='records')
    for row in rows:
        row["source"] = "appscan"
        row["department_id"] = department_for_app(row.get("app_name", "XYZ Application")) or "home-affairs-digital"
        row["branch_id"] = branch_for_app(row.get("app_name", "XYZ Application")) or "dha-digital"
        # Serialize any Timestamp objects in the row
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()
    
    print(f'Normalized {len(rows)} rows')
    
    # Check tenancy
    for row in rows[:3]:
        print(f'  app_name={row["app_name"]}, dept={row.get("department_id")}, branch={row.get("branch_id")}, severity={row["severity"]}')
    
    # Upsert to warehouse
    async with SessionFactory() as session:
        count = await upsert_findings(session, rows, source="appscan_real")
        print(f'Upserted {count} findings to warehouse')
        
        # Also create alerts for high/critical
        from app.lake.writer import upsert_alerts
        from app.processing.alert_enricher import AlertEnricher
        import uuid
        
        alerts = []
        enricher = AlertEnricher()
        now = datetime.now(timezone.utc)
        
        for row in rows:
            sev = str(row.get("severity") or "info").lower()
            if sev in ("critical", "high"):
                fired = now
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "rule_id": f"{sev}_record",
                    "title": f"{sev.title()} appscan_real finding ingested",
                    "description": row.get("title"),
                    "severity": sev,
                    "source": "appscan_real",
                    "target_id": row.get("app_name"),
                    "status": "new",
                    "channels": ["email", "teams"] if sev == "critical" else ["teams"],
                    "dedup_key": f"{sev}_record:appscan_real:{row.get('app_name')}:{row.get('external_id')}",
                    "first_triggered": fired.isoformat(),
                    "last_triggered": fired.isoformat(),
                })
        
        if alerts:
            alerts = [enricher.enrich(a) for a in alerts]
            await upsert_alerts(session, alerts, commit=True)
            print(f'Created {len(alerts)} alerts')

if __name__ == "__main__":
    asyncio.run(seed_real_appscan())