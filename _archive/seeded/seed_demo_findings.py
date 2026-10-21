#!/usr/bin/env python3
"""
Seed demo AppScan findings directly into the database.
Use when no test AppScan Cloud account is available.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import secrets

rng = secrets.SystemRandom()

from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch


APPS = [
    ("sita-portal", "Web Portal", "DAST"),
    ("sita-api-gateway", "API Gateway", "SAST"),
    ("sita-hr-system", "HR System", "SCA"),
    ("sita-finance", "Finance App", "DAST+SAST"),
    ("sita-procurement", "Procurement", "DAST"),
    ("sita-reporting", "Reporting", "SAST"),
]

CATEGORIES = [
    "Injection",
    "Broken Access Control",
    "Cryptographic Failures",
    "Insecure Design",
    "Security Misconfiguration",
    "Vulnerable Components",
    "Authentication Failures",
    "Software Integrity Failures",
    "Logging Failures",
    "SSRF",
]

SEVERITIES = [
    ("critical", 4, 9.0),
    ("high", 3, 7.5),
    ("medium", 2, 5.0),
    ("low", 1, 2.5),
]

STATUSES = ["Open", "Open", "Open", "Fixed", "In Progress", "Not a Finding"]


def generate_findings(count_per_app: int = 15) -> list[dict]:
    records = []
    base_date = datetime.now(timezone.utc) - timedelta(days=60)

    for app_name, app_desc, scan_type in APPS:
        for i in range(count_per_app):
            sev_name, sev_num, cvss = rng.choices(
                SEVERITIES, weights=[5, 15, 35, 45], k=1
            )[0]

            status = rng.choice(STATUSES)
            days_ago = rng.randint(0, 60)
            first_seen = base_date + timedelta(days=days_ago)
            last_seen = first_seen + timedelta(days=rng.randint(0, 5))

            # Critical/High get CVEs
            cve = None
            if sev_name in ("critical", "high") and rng.random() < 0.7:
                cve = f"CVE-2026-{rng.randint(1000, 9999)}"

            category = rng.choice(CATEGORIES)

            records.append({
                "external_id": f"APPSCAN-{app_name.upper().replace('-', '')}-{i:04d}",
                "source": "appscan",
                "application_name": app_name,
                "vulnerability_name": f"{category} in {app_desc}",
                "description": f"[{scan_type}] {category} vulnerability discovered in {app_desc}. "
                               f"Allows attacker to {'execute arbitrary code' if sev_name=='critical' else 'access sensitive data' if sev_name=='high' else 'bypass controls' if sev_name=='medium' else 'enumerate information'}.",
                "severity": sev_num,
                "severity_raw": sev_name,
                "status": status,
                "first_found_date": first_seen.isoformat(),
                "last_found_date": last_seen.isoformat(),
                "cve": cve,
                "cvss_score": cvss + rng.uniform(-0.5, 0.5),
                "owasp_category": category,
                "scan_type": scan_type,
            })

    return records


async def main():
    print("Generating demo AppScan findings...")
    records = generate_findings(count_per_app=18)  # ~108 total

    print(f"Generated {len(records)} records across {len(APPS)} applications")

    # Summary stats
    by_sev = {}
    by_app = {}
    by_status = {}
    for r in records:
        by_sev[r["severity_raw"]] = by_sev.get(r["severity_raw"], 0) + 1
        by_app[r["application_name"]] = by_app.get(r["application_name"], 0) + 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    print("\nDistribution:")
    print(f"  By Severity: {by_sev}")
    print(f"  By App: {by_app}")
    print(f"  By Status: {by_status}")
    print(f"  With CVE: {sum(1 for r in records if r['cve'])}")

    print("\nIngesting into database...")
    async with SessionFactory() as session:
        count = await upsert_lake_batch(session, records, source="appscan")

    print(f"\n✅ Successfully ingested {count} demo findings")
    print("\nDashboard should now show data at:")
    print("  http://localhost:3000/appsec")
    print("  http://localhost:3000/exec")
    print("  http://localhost:3000/soc")


if __name__ == "__main__":
    asyncio.run(main())