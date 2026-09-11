# AppScan Cloud Log Ingestion Pipeline

## Overview

This pipeline pulls vulnerability findings from **AppScan Cloud API** and ingests them into the SITA Unified Intelligence Platform database for unified risk scoring, alerting, and dashboarding.

## Architecture

```
AppScan Cloud API → AppScanConnector → Lake Writer → PostgreSQL (warehouse.findings)
                                      ↓
                              Risk Engine → Alert Processor → Dispatch
```

## Components

| File | Purpose |
|------|---------|
| `app/connectors/appscan.py` | AppScan Cloud API connector (auth, poll, parse, validate) |
| `scripts/ingest_appscan_logs.py` | Standalone ingestion script (CLI) |
| `configs/appscan.yaml` | Configuration template |
| `app/ingestion/scheduler.py` | Scheduled polling (APScheduler) |

## Quick Start

### 1. Get AppScan Credentials

1. Log into [AppScan Cloud](https://cloud.appscan.com)
2. Go to **Account** → **API Keys**
3. Generate or copy your **Key ID** and **Key Secret**
4. Note your **Account/Org ID** (from URL or Account settings)
5. For per-application polling, get the **Application ID** from **Applications** → click app → check URL

**Authentication Format**: AppScan Cloud uses `KeyId` + `KeySecret` pair. Provide as:
- `--api-key "key_id:key_secret"` (single string)
- OR `--key-id KEY_ID --key-secret KEY_SECRET` (separate)
- OR env vars: `APPSCAN_API_KEY="key_id:key_secret"` or `APPSCAN_KEY_ID` + `APPSCAN_KEY_SECRET`

### 2. Configure

```bash
# Option A: Environment variables
export APPSCAN_API_KEY="your-api-key"
export APPSCAN_ACCOUNT_ID="your-account-id"
export APPSCAN_APPLICATION_ID="your-app-id"  # optional, for application scope

# Option B: Config file (copy template)
cp configs/appscan.yaml configs/appscan.local.yaml
# Edit configs/appscan.local.yaml with your credentials

# Option C: CLI arguments
```

### 3. Run Ingestion

```bash
# Dry run (fetch & validate, no DB write)
python -m scripts.ingest_appscan_logs --dry-run -v

# Production run
python -m scripts.ingest_appscan_logs

# With config file
python -m scripts.ingest_appscan_logs --config configs/appscan.local.yaml

# With CLI args
python -m scripts.ingest_appscan_logs \
  --api-key $APPSCAN_API_KEY \
  --account-id $APPSCAN_ACCOUNT_ID \
  --application-id $APPSCAN_APPLICATION_ID
```

### 4. Scheduled Polling (Production)

The connector is integrated into the APScheduler in `app/ingestion/scheduler.py`:

```python
CONNECTOR_CONFIGS = {
    "appscan": {
        "poll_interval": 300,      # 5 minutes
        "rate_limit": 500,         # req/min
        "base_url": "https://cloud.appscan.com",
        "api_key": "",             # Set via env or config
        "account_id": "",
        "application_id": "",
        "page_size": 200,
        "scope": "application",
    },
}
```

Start the scheduler:
```bash
cd backend
python -m app.ingestion.scheduler
```

## API Endpoints Used

| Operation | AppScan Cloud Endpoint | Method |
|-----------|------------------------|--------|
| Authenticate | `/api/v4/Account/ApiKeyLogin` | POST (x-api-key header) |
| Get Issues | `/api/v4/Issues/{scope}/{scopeId}` | GET (Bearer token, pagination) |

### Scope Options

| Scope | scopeId | Use Case |
|-------|---------|----------|
| `application` | Application ID | Single app findings |
| `org` | Account/Org ID | All apps in organization |

## Data Mapping

AppScan fields → SITA Platform `warehouse.findings`:

| AppScan Field | SITA Field | Notes |
|---------------|------------|-------|
| `id` / `IssueId` | `external_id` | Unique identifier |
| `application_name` | `app_name` | Application name |
| `vulnerability_name` | `title` | Finding title |
| `description` | `description` | Full description |
| `severity` (1-4 / Critical-High-Medium-Low) | `severity` | Normalized to 1-4 |
| `status` | `status` | Open/In Progress/Fixed |
| `first_found_date` | `first_seen` | First detection |
| `last_found_date` | `last_seen` | Latest detection |
| `cve` | `cve` | CVE identifier |
| `cvss` | `cvss_score` | CVSS score |
| `owasp_category` | `category` | OWASP category |
| All raw fields | `raw_data` | JSON blob for audit |

## Severity Normalization

| AppScan | SITA (1-4) |
|---------|------------|
| "1 - Low" / "Low" / "Informational" | 1 (info) |
| "2 - Medium" / "Medium" | 2 (low) |
| "3 - High" / "High" | 3 (high) |
| "4 - Critical" / "Critical" | 4 (critical) |

## Database Schema

Findings are stored in `warehouse.findings` with:
- **Unique constraint**: `(source, external_id)` — prevents duplicates
- **Upsert logic**: Updates `last_seen`, `status`, `version++` on conflict
- **Tenancy**: Auto-assigned via `department_for_app()`, `branch_for_app()`, etc.

## Monitoring

Check connector health:
```sql
SELECT * FROM warehouse.connector_health WHERE name = 'appscan';
```

Check recent findings:
```sql
SELECT * FROM warehouse.findings
WHERE source = 'appscan'
ORDER BY first_seen DESC
LIMIT 20;
```

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `401 Unauthorized` | Check API key is valid and not expired. Regenerate in AppScan Cloud. |
| `403 Forbidden` | API key may lack permissions. Ensure it has "View Issues" scope. |
| `404 Not Found` | Verify `application_id` or `account_id` is correct for the scope. |
| `0 issues returned` | Check date range filters, application has scans, issues exist. |
| `Rate limited` | Reduce `page_size` or increase `poll_interval`. AppScan allows 500 req/min. |
| `Token expired` | Connector auto-refreshes token. Check clock sync on server. |

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APPSCAN_API_KEY` | Yes | API Key from AppScan Cloud |
| `APPSCAN_ACCOUNT_ID` | Yes* | Org/Account ID (for org scope) |
| `APPSCAN_APPLICATION_ID` | Yes* | Application ID (for application scope) |
| `APPSCAN_BASE_URL` | No | Default: `https://cloud.appscan.com` |
| `APPSCAN_SCOPE` | No | `application` or `org` (default: application) |
| `APPSCAN_PAGE_SIZE` | No | Default: 200 |

*At least one of `account_id` or `application_id` required based on scope.

### CLI Arguments

```bash
python -m scripts.ingest_appscan_logs --help
```

```
usage: ingest_appscan_logs.py [-h] [--config CONFIG] [--base-url BASE_URL]
                              [--api-key API_KEY] [--account-id ACCOUNT_ID]
                              [--application-id APPLICATION_ID]
                              [--page-size PAGE_SIZE] [--scope {application,org}]
                              [--dry-run] [-v]

AppScan Cloud Log Ingestion Pipeline

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to YAML config file
  --base-url BASE_URL   AppScan Cloud base URL (default: https://cloud.appscan.com)
  --api-key API_KEY     AppScan API key
  --account-id ACCOUNT_ID
                        AppScan account/org ID
  --application-id APPLICATION_ID
                        AppScan application ID
  --page-size PAGE_SIZE Page size for pagination (default: 200)
  --scope {application,org}
                        Scope for issues query (default: application)
  --dry-run             Fetch and validate but don't write to DB
  -v, --verbose         Verbose logging
```

## Security Notes

- **Never commit** `configs/appscan.local.yaml` or credentials to git
- Use environment variables or secret manager in production
- API keys should be rotated periodically (AppScan supports expiration)
- Run ingestion from secured network (VPN/private subnet)
- Database connections use SSL in production

## Testing

```bash
# Unit tests
cd backend
python -m pytest tests/test_appscan_connector.py -v

# Integration test (requires credentials)
python -m scripts.ingest_appscan_logs --dry-run -v
```

## Flight Plan References

- **Phase 2** (Week 2): BaseConnector abstract class, AppScan connector implementation
- **Phase 3** (Week 3): Scheduler integration, circuit breaker, rate limiting
- **Phase 5** (Week 5): Normaliser severity mapping for AppScan
- **Phase 11** (Week 11): Alert dispatch for critical AppScan findings

---

**Maintainer**: Takawira Mazando (Bantu InfoTech)  
**Last Updated**: August 2026