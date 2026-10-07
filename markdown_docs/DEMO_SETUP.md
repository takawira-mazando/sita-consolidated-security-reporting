# SITA Platform - OEM Test Account Demo Setup

## Overview
This document describes how to set up and run the **Demo Ingestion Pipeline** that pulls real test data from OEM test accounts (AppScan, Imperva, APISec) and displays it in the SITA Platform dashboards via the **Demo Mode** toggle.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OEM Test       │     │  Demo Ingestion  │     │  SITA Platform  │
│  Accounts       │────▶│  Pipeline        │────▶│  (PostgreSQL)   │
│  (AppScan,      │     │  (K8s CronJob)   │     │  + Frontend     │
│   Imperva,      │     │  • Every 15 min  │     │  • Demo Mode    │
│   APISec)       │     │  • Demo tenant   │     │    toggle       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  Demo Tenant     │
                        │  department_id:  │
                        │  00000000-...001 │
                        └──────────────────┘
```

---

## Prerequisites

| Component | Required |
|-----------|----------|
| OEM Test Accounts | ✅ AppScan Cloud, Imperva, APISec test tenants with API access |
| Kubernetes Cluster | ✅ For CronJob deployment |
| PostgreSQL | ✅ SITA database |
| Docker Registry | ✅ For backend image |

---

## OEM Test Account Credentials Needed

### AppScan Cloud
```
DEMO_APPSCAN_KEY_ID=your-demo-key-id
DEMO_APPSCAN_KEY_SECRET=your-demo-key-secret
DEMO_APPSCAN_ACCOUNT_ID=your-demo-account-uuid
# Optional: specific application
DEMO_APPSCAN_APPLICATION_ID=your-demo-app-uuid
```

### Imperva DAM
```
DEMO_IMPERVA_DAM_BASE_URL=https://your-demo.imperva.com
DEMO_IMPERVA_DAM_API_KEY=your-demo-api-key
```

### Imperva WAF
```
DEMO_IMPERVA_WAF_BASE_URL=https://your-demo.imperva.com
DEMO_IMPERVA_WAF_API_KEY=your-demo-api-key
```

### APISec
```
DEMO_APISEC_BASE_URL=https://api.demo.apisec.ai
DEMO_APISEC_API_KEY=your-demo-api-key
```

---

## Deployment

### 1. Create Demo Secrets
```bash
kubectl create secret generic demo-oem-secrets \
  -n sita-platform \
  --from-literal=DEMO_APPSCAN_KEY_ID="your-key-id" \
  --from-literal=DEMO_APPSCAN_KEY_SECRET="your-key-secret" \
  --from-literal=DEMO_APPSCAN_ACCOUNT_ID="your-account-uuid" \
  --from-literal=DEMO_IMPERVA_DAM_BASE_URL="https://your-demo.imperva.com" \
  --from-literal=DEMO_IMPERVA_DAM_API_KEY="your-api-key" \
  --from-literal=DEMO_IMPERVA_WAF_BASE_URL="https://your-demo.imperva.com" \
  --from-literal=DEMO_IMPERVA_WAF_API_KEY="your-api-key" \
  --from-literal=DEMO_APISEC_BASE_URL="https://api.demo.apisec.ai" \
  --from-literal=DEMO_APISEC_API_KEY="your-api-key"
```

### 2. Apply ConfigMaps and CronJob
```bash
kubectl apply -f backend/k8s/demo-ingestion-cronjob.yaml
```

### 3. Verify Deployment
```bash
# Check CronJob
kubectl -n sita-platform get cronjob demo-ingestion

# Trigger manual run
kubectl -n sita-platform create job --from=cronjob/demo-ingestion demo-ingestion-manual-$(date +%s)

# View logs
kubectl -n sita-platform logs -l job-name=demo-ingestion --tail=100
```

---

## Demo Data Flow

### Backend Ingestion (Every 15 min)
1. **CronJob triggers** `demo_ingestion.py --all`
2. **Each connector authenticates** with OEM test account
3. **Data fetched** from AppScan, Imperva DAM/WAF, APISec
4. **Records tagged** with demo tenant IDs:
   - `department_id: 00000000-0000-0000-0000-000000000001`
   - `branch_id: 00000000-0000-0000-0000-000000000001`
   - `ministry_id: 00000000-0000-0000-0000-000000000001`
   - `cluster_id: 00000000-0000-0000-0000-000000000001`
   - `app_name` prefixed with `DEMO-`
5. **Upserted** into `warehouse.findings` and metrics tables

### Frontend Demo Mode
1. **User clicks 🧪 Demo button** in header
2. **Demo mode enabled** → stored in localStorage, synced across tabs
3. **All dashboard hooks** switch to demo-aware fetchers
4. **API calls include** `department_id=00000000-...001` filter
5. **Backend tenant_filter** returns only demo-tagged data
6. **Dashboards display** real OEM test data

---

## Running Locally (Development)

### Backend
```bash
cd backend
# Set demo credentials in .env.demo
cp .env.demo .env
# Edit .env with test account credentials

# Run demo ingestion once
python -m scripts.demo_ingestion --all --json-logs

# Or run individual connector
python -m scripts.demo_ingestion --connector appscan --dry-run
```

### Frontend
```bash
cd frontend
npm run dev
# Open http://localhost:3000
# Login → Click 🧪 Demo button
```

---

## Dashboard Data Sources (Demo Mode)

| Dashboard | Data Source | Demo Endpoint |
|-----------|-------------|---------------|
| **AppSec** | Findings, Fix Rate, WAF, API Exposure | `/findings`, `/metrics/*` with demo tenant |
| **Executive** | Summary, Findings, Risks, Compliance | `/public/summary`, `/findings`, `/risks`, `/compliance` |
| **SOC** | Alerts, Findings, SLO | `/alerts`, `/findings`, `/metrics/slo` |
| **Compliance** | POPIA, ISO27001, Gaps, Evidence | `/compliance`, `/compliance/gaps` |
| **DB Security** | Findings, Alerts, Inventory | `/findings`, `/alerts`, `/metrics/db-inventory` |
| **SRE** | Connectors, System Metrics, Agents | `/admin/connectors`, `/metrics/system`, `/metrics/agents` |

---

## Demo Tenant Filtering

The backend uses `tenant_filter` in API routers. When demo mode is active:
- Frontend sends `department_id=00000000-...001` 
- Backend `tenant_filter` matches user's department_ids
- Only demo-tagged records returned

### Backend Filter Logic (in `app/api/auth.py`)
```python
def tenant_filter(claims, model):
    dept_ids = claims.get("department_ids", [])
    if dept_ids:
        return model.department_id.in_(dept_ids)
    return None
```

---

## Verification Checklist

### Ingestion
- [ ] CronJob runs successfully every 15 min
- [ ] AppScan: findings ingested with `DEMO-` prefix
- [ ] Imperva DAM: data ingested
- [ ] Imperva WAF: blocks ingested
- [ ] APISec: endpoints ingested
- [ ] Compliance: CSV loaded
- [ ] Connector health shows "healthy" for demo-* connectors

### Frontend
- [ ] 🧪 Demo button appears in header
- [ ] Clicking enables demo mode (badge shows "DEMO")
- [ ] Demo banner appears at top of dashboard
- [ ] AppSec dashboard shows DEMO- prefixed apps
- [ ] Findings table shows real OEM test data
- [ ] Critical findings show CVEs from test account
- [ ] Fix Rate calculates from demo data
- [ ] WAF blocks show demo data
- [ ] API Exposure shows demo endpoints
- [ ] Executive dashboard shows demo risk scores
- [ ] Compliance shows demo gaps
- [ ] Clicking 🧪 Demo again returns to real data

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `Authentication failed` | Verify OEM test credentials are correct and not expired |
| `0 findings fetched` | Check test account has completed scans; verify account_id vs application_id |
| `Demo mode shows no data` | Verify ingestion ran; check `warehouse.findings` for `DEMO-` prefix |
| `Connector health degraded` | Check CronJob logs; verify network egress to OEM APIs |
| `Frontend demo toggle not working` | Check localStorage for `sita_demo_mode`; clear and retry |

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/scripts/demo_ingestion.py` | Main demo ingestion orchestrator |
| `backend/.env.demo` | Demo credentials template |
| `backend/k8s/demo-ingestion-cronjob.yaml` | K8s CronJob + ConfigMaps + Secrets |
| `frontend/src/context/DemoContext.tsx` | Global demo mode state |
| `frontend/src/api/demoApi.ts` | Demo-aware API fetchers |
| `frontend/src/api/demoInterceptor.ts` | Axios interceptor for demo mode |
| `frontend/src/components/layout/RoleNav.tsx` | Demo toggle button in header |
| `frontend/src/App.tsx` | Demo banner component |
| `frontend/src/hooks/useAppSecData.ts` | Demo-aware data hooks |
| `frontend/src/hooks/useExecData.ts` | Demo-aware data hooks |
| `frontend/src/hooks/useSocData.ts` | Demo-aware data hooks |
| `frontend/src/hooks/useComplianceData.ts` | Demo-aware data hooks |
| `frontend/src/hooks/useDbSecData.ts` | Demo-aware data hooks |

---

## Next Steps

1. **Obtain OEM test credentials** from AppScan, Imperva, APISec
2. **Deploy to staging Kubernetes** cluster
3. **Run manual ingestion** to populate demo data
4. **Verify frontend demo mode** shows all dashboards correctly
5. **Record demo video** for stakeholder presentation
6. **Document demo reset procedure** (clear demo data, re-ingest)