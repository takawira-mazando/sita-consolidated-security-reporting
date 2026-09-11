# SITA Platform Demo Plan: AppScan Ingestion → Dashboard

## Overview
End-to-end demo showing: **AppScan Cloud** → **Ingestion Pipeline** → **PostgreSQL** → **FastAPI** → **React Dashboard**

---

## Prerequisites

| Component | Status | Notes |
|-----------|--------|-------|
| AppScan Cloud Test Account | ⏳ Need credentials | Need Key ID, Key Secret, Account ID |
| Test Application with Findings | ⏳ Need populated | Must have vulnerabilities in AppScan |
| Backend (FastAPI + PostgreSQL) | ✅ Ready | `docker-compose up` or local |
| Frontend (React + Vite) | ✅ Ready | `npm run dev` in `/frontend` |
| Kubernetes (optional) | ✅ CronJob YAML created | `k8s/appscan-ingestion-cronjob.yaml` |

---

## Demo Data Requirements

### AppScan Test Account Setup
```
Required in AppScan Cloud:
├── Organization/Account (with API access enabled)
├── At least 1 Application with completed scans
│   ├── DAST scan (web app)
│   ├── SAST scan (source code)
│   └── SCA scan (dependencies)
├── Findings across severities:
│   ├── 3-5 Critical (SQLi, RCE, Auth bypass)
│   ├── 5-10 High (XSS, IDOR, SSRF)
│   ├── 10-20 Medium (Info disclosure, Crypto)
│   └── 20+ Low/Info
├── Categories mapped to OWASP Top 10:
│   ├── A01: Broken Access Control
│   ├── A02: Cryptographic Failures
│   ├── A03: Injection
│   └── ... etc
└── CVE references on findings (for critical table)
```

### Sample App Names for Demo
| App Name | Type | Expected Findings |
|----------|------|-------------------|
| `sita-portal` | DAST | 15 findings (3C, 5H, 4M, 3L) |
| `sita-api-gateway` | SAST | 22 findings (2C, 6H, 8M, 6L) |
| `sita-hr-system` | SCA | 18 findings (1C, 4H, 7M, 6L) |
| `sita-finance` | DAST+SAST | 30 findings (4C, 8H, 10M, 8L) |

---

## Demo Flow (5-7 minutes)

### 1. Show AppScan Cloud UI (1 min)
- Log into test AppScan Cloud account
- Show Applications list with scan status
- Open one app → show Findings tab
- Highlight: severity distribution, CVE links, scan history

### 2. Run Ingestion Pipeline (1 min)
```bash
# Option A: Local one-off
cd backend
python -m scripts.ingest_appscan_logs \
  --key-id $APPSCAN_KEY_ID \
  --key-secret $APPSCAN_KEY_SECRET \
  --account-id $APPSCAN_ACCOUNT_ID \
  --json-logs

# Option B: Show CronJob (if K8s available)
kubectl -n sita-platform create job --from=cronjob/appscan-ingestion appscan-demo-$(date +%s)
kubectl -n sita-platform logs -l job-name=appscan-demo --tail=50
```

**Expected Output:**
```json
{
  "status": "success",
  "fetched": 85,
  "validated": 82,
  "ingested": 82,
  "duration_seconds": 12.3
}
```

### 3. Verify Database (30 sec)
```sql
-- Quick checks
SELECT source, count(*) FROM warehouse.findings GROUP BY source;
-- appscan | 82

SELECT app_name, severity, count(*) 
FROM warehouse.findings 
WHERE source='appscan' 
GROUP BY app_name, severity 
ORDER BY app_name, severity;
```

### 4. Show API Response (30 sec)
```bash
# Get findings via API
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/findings?source=appscan&size=10"
```

### 5. Frontend Dashboard Walkthrough (3-4 min)

| Dashboard | Key Widgets to Highlight |
|-----------|--------------------------|
| **AppSec Dashboard** (`/appsec`) | • Total Findings stat card<br>• Vulnerability by Application table<br>• OWASP Category distribution bars<br>• Critical Findings table (CVE, CVSS, App, Discovered)<br>• Fix Rate (30d) |
| **Executive Dashboard** (`/exec`) | • Risk posture summary<br>• Top 5 applications by risk<br>• Compliance overview |
| **SOC Dashboard** (`/soc`) | • Alert feed (if alerts generated)<br>• MTTD/MTTR metrics |

**AppSec Dashboard Data Flow:**
```
useAppSecData hook
  ├─ fetchFindings({size: 200}) → GET /api/v1/findings
  ├─ fetchFixRate() → GET /api/v1/metrics/fix-rate
  ├─ fetchWafSummary() → GET /api/v1/metrics/waf-summary
  └─ fetchApiExposure() → GET /api/v1/metrics/api-exposure
        │
        ▼
Client-side aggregation:
  • severityCounts() → {critical: 10, high: 23, ...}
  • findingsByAppSeverity() → per-app breakdown
  • OWASP category mapping via category field
  • Critical findings filter + CVE extraction
```

---

## Backend API Endpoints Used by Dashboard

| Endpoint | Purpose | Params |
|----------|---------|--------|
| `GET /api/v1/findings` | Paginated findings list | `source=appscan`, `severity`, `app`, `page`, `size` |
| `GET /api/v1/metrics/fix-rate` | 30-day fix rate % | — |
| `GET /api/v1/metrics/waf-summary` | WAF blocks by type | — |
| `GET /api/v1/metrics/api-exposure` | Shadow API endpoints | — |
| `GET /api/v1/public/summary` | Public stats (no auth) | — |

---

## Demo Script (Narrative)

> **"We're looking at the SITA Unified Intelligence Platform. This demo shows how AppScan vulnerability findings flow automatically into our security dashboards.**
>
> **Step 1:** Here's our test AppScan Cloud tenant with 4 applications. Each has completed DAST/SAST/SCA scans with real findings.
>
> **Step 2:** Our ingestion pipeline runs every 5 minutes via Kubernetes CronJob. It authenticates with API keys, pulls all findings via AppScan's REST API, validates them, and upserts into our PostgreSQL warehouse with full organizational hierarchy (department, branch, ministry, cluster).
>
> **Step 3:** The data is instantly available via FastAPI. The AppSec dashboard polls `/api/v1/findings` and aggregates client-side: severity counts, per-application breakdown, OWASP category mapping, and critical findings with CVEs.
>
> **Step 4:** Notice the consolidated view — we're not just showing AppScan. The same dashboard fuses API Security exposure data and Imperva WAF blocking telemetry for a complete application risk picture."
>
> **Step 5:** Click a critical finding → shows external ID, CVE, application, category, discovery date. Export to CSV for ticketing integration.

---

## Troubleshooting Checklist

| Issue | Resolution |
|-------|------------|
| `0 findings fetched` | Verify AppScan account has completed scans; check `application_id` vs `account_id` scope |
| `Authentication failed` | Verify Key ID/Secret are correct; check token expiry (25 min TTL) |
| `Dashboard shows "No findings yet"` | Check API response: `curl /api/v1/findings?source=appscan`; verify tenant filter matches `app_name` |
| `Fix Rate shows —` | Need findings with `status=Fixed` and `last_seen` within 30 days |
| `CVE column empty` | AppScan findings must have `cve` field populated |

---

## Quick Seed Data (If No AppScan Access)

If test AppScan account unavailable, seed synthetic data directly:

```python
# backend/scripts/seed_demo_findings.py
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch

apps = ["sita-portal", "sita-api-gateway", "sita-hr-system", "sita-finance"]
categories = ["Injection", "Broken Access Control", "Cryptographic Failures", "Insecure Design", "Security Misconfiguration"]
severities = ["critical", "high", "medium", "low"]

async def seed():
    records = []
    for app in apps:
        for i in range(20):
            sev = severities[i % 4]
            records.append({
                "external_id": f"APPSCAN-{app.upper()}-{i:04d}",
                "source": "appscan",
                "application_name": app,
                "vulnerability_name": f"{categories[i % 5]} in {app}",
                "description": f"AppScan finding #{i} for {app}",
                "severity": {"critical":4,"high":3,"medium":2,"low":1}[sev],
                "severity_raw": sev,
                "status": "Open" if i % 3 else "Fixed",
                "first_found_date": (datetime.now(timezone.utc) - timedelta(days=i*2)).isoformat(),
                "last_found_date": datetime.now(timezone.utc).isoformat(),
                "cve": f"CVE-2026-{1000+i}" if sev in ("critical","high") else None,
                "cvss_score": 9.0 if sev=="critical" else 7.5 if sev=="high" else 5.0 if sev=="medium" else 2.0,
                "owasp_category": categories[i % 5],
            })
    async with SessionFactory() as session:
        count = await upsert_lake_batch(session, records, source="appscan")
        print(f"Seeded {count} demo findings")

asyncio.run(seed())
```

Run: `python -m scripts.seed_demo_findings`

---

## Dashboard Screenshots Checklist

For demo recording/documentation, capture:

- [ ] AppSec Dashboard - Full view (stats bar + 4 panels)
- [ ] AppSec Dashboard - Critical Findings table expanded
- [ ] Executive Dashboard - Risk posture
- [ ] Findings list page (if exists) - filtered by `source=appscan`
- [ ] API response JSON for `/findings?source=appscan`
- [ ] CronJob logs showing successful ingestion

---

## Environment Variables for Demo

```bash
# .env.demo
APPSCAN_KEY_ID=demo-key-id
APPSCAN_KEY_SECRET=demo-key-secret
APPSCAN_ACCOUNT_ID=demo-account-uuid
APPSCAN_BASE_URL=https://cloud.appscan.com
APPSCAN_PAGE_SIZE=200
APPSCAN_SCOPE=application

DATABASE_URL=postgresql+asyncpg://sita:password@localhost:5432/sita
REDIS_URL=redis://:password@localhost:6379/0
JWT_SECRET=demo-secret-change-me
```

---

## Success Criteria

✅ Ingestion completes with `status: success` and `ingested > 0`  
✅ Dashboard loads without "No findings yet" empty states  
✅ Severity counts match AppScan Cloud UI  
✅ Critical findings table shows CVE references  
✅ Per-application breakdown matches scan results  
✅ OWASP category distribution reflects finding categories  
✅ Fix Rate calculates (if fixed findings exist)  

---

## Next Steps After Demo

1. **Production hardening**: Add incremental sync (`since_date`), report generation (SARIF), alert rules
2. **Multi-connector demo**: Add Imperva WAF + API Security connectors
3. **Compliance mapping**: Show POPIA/ISO27001 control coverage from findings
4. **Risk scoring**: Demonstrate fused risk score per application