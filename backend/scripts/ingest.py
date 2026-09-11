#!/usr/bin/env python3
"""
Unified Ingestion Pipeline — Demo & Production

Runs all OEM connectors (AppScan, Imperva DAM/WAF, APISec, Compliance)
using the EXACT same code path for both demo and production.

Usage:
    # Production (uses APPSCAN_*, IMPERVA_*, APISEC_* env vars)
    python -m scripts.ingest --connector appscan

    # Demo mode (uses DEMO_APPSCAN_*, DEMO_IMPERVA_*, DEMO_APISEC_* env vars)
    python -m scripts.ingest --demo --connector appscan

    # Run all connectors
    python -m scripts.ingest --all
    python -m scripts.ingest --demo --all

    # Dry run
    python -m scripts.ingest --demo --all --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Literal

import yaml

from app.connectors.appscan import AppScanConnector
from app.connectors.imperva import ImpervaConnector
from app.connectors.apisec import ApiSecurityConnector
from app.connectors.compliance import ComplianceConnector
from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch, update_connector_health
from app.tenant import DEPARTMENTS

# Structured JSON logging for k8s log aggregation
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in {"name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "exc_info", "exc_text", "stack_info",
                          "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName"}:
                log_obj[key] = value
        return json.dumps(log_obj)

def setup_logging(json_format: bool = False, level: int = logging.INFO):
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

logger = logging.getLogger("sita_ingest")

# Demo tenant configuration - uses a REAL department from the tenancy model
DEMO_DEPARTMENT_ID = "treasury"  # National Treasury - real department in tenancy model
DEMO_APP_PREFIX = "DEMO-"

CONNECTOR_SPECS = {
    "appscan": {
        "class": AppScanConnector,
        "prod_prefix": "APPSCAN",
        "demo_prefix": "DEMO_APPSCAN",
        "required": ["KEY_ID", "KEY_SECRET", "ACCOUNT_ID"],
        "optional": ["BASE_URL", "APPLICATION_ID", "PAGE_SIZE", "SCOPE"],
        "defaults": {
            "BASE_URL": "https://cloud.appscan.com",
            "PAGE_SIZE": "200",
            "SCOPE": "application",
        },
        "source_name": "appscan",
    },
    "imperva_dam": {
        "class": ImpervaConnector,
        "prod_prefix": "IMPERVA_DAM",
        "demo_prefix": "DEMO_IMPERVA_DAM",
        "required": ["BASE_URL", "API_KEY", "SOURCE_TYPE"],
        "optional": [],
        "defaults": {"SOURCE_TYPE": "dam"},
        "source_name": "imperva-dam",
    },
    "imperva_waf": {
        "class": ImpervaConnector,
        "prod_prefix": "IMPERVA_WAF",
        "demo_prefix": "DEMO_IMPERVA_WAF",
        "required": ["BASE_URL", "API_KEY", "SOURCE_TYPE"],
        "optional": [],
        "defaults": {"SOURCE_TYPE": "waf"},
        "source_name": "imperva-waf",
    },
    "apisec": {
        "class": ApiSecurityConnector,
        "prod_prefix": "APISEC",
        "demo_prefix": "DEMO_APISEC",
        "required": ["BASE_URL", "API_KEY"],
        "optional": [],
        "defaults": {},
        "source_name": "apisec",
    },
    "compliance": {
        "class": ComplianceConnector,
        "prod_prefix": "COMPLIANCE",
        "demo_prefix": "DEMO_COMPLIANCE",
        "required": ["SOURCE_TYPE"],
        "optional": ["CSV_PATH"],
        "defaults": {"SOURCE_TYPE": "csv", "CSV_PATH": "/app/data/compliance.csv"},
        "source_name": "compliance",
    },
}


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def build_connector_config(spec: dict, args, demo: bool) -> dict:
    """Build connector config from CLI args, env vars, and config file."""
    prefix = spec["demo_prefix"] if demo else spec["prod_prefix"]
    
    config = {}
    # Required fields
    for field in spec["required"]:
        env_key = f"{prefix}_{field}"
        cli_key = field.lower().replace("_", "-")
        value = getattr(args, cli_key, None) or os.getenv(env_key, "")
        if not value:
            raise ValueError(f"Missing required config: {env_key} (or --{cli_key})")
        config[field.lower()] = value
    
    # Optional fields with defaults
    for field in spec["optional"]:
        env_key = f"{prefix}_{field}"
        cli_key = field.lower().replace("_", "-")
        value = getattr(args, cli_key, None) or os.getenv(env_key)
        if value:
            config[field.lower()] = value
        elif field in spec["defaults"]:
            config[field.lower()] = spec["defaults"][field]
    
    # Add source name for lake writer
    config["source_name"] = spec["source_name"]
    config["demo"] = demo
    
    return config


def apply_demo_tenant_tagging(df, demo: bool):
    """Apply demo tenant tagging to DataFrame records.
    
    Uses a REAL department from the tenancy model so that:
    - Frontend demo mode can query with department_id=treasury
    - Existing tenant_filter works without changes
    - Data appears in the correct tenancy scope
    """
    if not demo or df.empty:
        return df
    
    # Use a real department from the tenancy model
    if DEMO_DEPARTMENT_ID not in DEPARTMENTS:
        logger.warning(f"Demo department {DEMO_DEPARTMENT_ID} not in tenancy model, using treasury")
        demo_dept = "treasury"
    else:
        demo_dept = DEMO_DEPARTMENT_ID
    
    # Get branch for this department (prefer ICT/digital branch)
    from app.tenant import BRANCHES, _representative_branch
    try:
        demo_branch = _representative_branch(demo_dept)
    except ValueError:
        demo_branch = list(BRANCHES.keys())[0]
    
    # Get ministry/cluster from department
    from app.tenant import DEPARTMENT_TO_MINISTRY, MINISTRY_TO_CLUSTER
    demo_ministry = DEPARTMENT_TO_MINISTRY.get(demo_dept, "finance")
    demo_cluster = MINISTRY_TO_CLUSTER.get(demo_ministry, "finance-admin")
    
    logger.info(f"Tagging demo records with tenant: dept={demo_dept}, branch={demo_branch}, "
                f"ministry={demo_ministry}, cluster={demo_cluster}")
    
    for _, row in df.iterrows():
        # Prefix app_name for easy identification in UI
        for field in ("app_name", "application_name", "database_name", "endpoint"):
            if field in row and row[field]:
                row[field] = f"{DEMO_APP_PREFIX}{row[field]}"
        
        # Set tenancy fields
        row["department_id"] = demo_dept
        row["branch_id"] = demo_branch
        row["ministry_id"] = demo_ministry
        row["cluster_id"] = demo_cluster
    
    return df


async def run_connector_ingestion(
    connector_name: str,
    config: dict,
    demo: bool,
    dry_run: bool = False
) -> dict:
    """Run ingestion for a single connector using the EXACT same connector class."""
    logger.info(f"Starting {connector_name} ingestion (demo={demo})")
    start_time = datetime.now(timezone.utc)
    
    spec = CONNECTOR_SPECS[connector_name]
    
    try:
        connector = spec["class"](config)
        connector.logger = logger
        
        logger.info(f"Authenticating {connector_name}...")
        authenticated = await connector.authenticate()
        if not authenticated:
            raise RuntimeError(f"{connector_name} authentication failed")
        
        logger.info(f"Fetching data from {connector_name}...")
        raw_data = await connector.poll()
        logger.info(f"Fetched {len(raw_data)} raw records from {connector_name}")
        
        if not raw_data:
            logger.warning(f"No data returned from {connector_name}")
            return {
                "status": "success",
                "connector": connector_name,
                "demo": demo,
                "fetched": 0,
                "ingested": 0,
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        logger.info(f"Parsing and validating {connector_name} data...")
        df = connector.parse(raw_data)
        df = connector.validate(df)
        logger.info(f"Validated {len(df)} records from {connector_name}")
        
        # Apply demo tenant tagging (uses real tenancy model)
        if demo:
            df = apply_demo_tenant_tagging(df, demo=True)
        
        records = df.to_dict(orient="records")
        
        if dry_run:
            logger.info(f"DRY RUN - {connector_name} would ingest {len(records)} records")
            for i, r in enumerate(records[:3]):
                app_name = r.get("app_name") or r.get("application_name") or r.get("database_name") or "N/A"
                logger.info(f"  Sample {i+1}: {app_name} - {r.get('title', r.get('vulnerability_name', 'N/A'))} [{r.get('severity', 'N/A')}]")
            return {
                "status": "dry_run",
                "connector": connector_name,
                "demo": demo,
                "fetched": len(raw_data),
                "validated": len(df),
                "would_ingest": len(records),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        logger.info(f"Ingesting {connector_name} data into database...")
        source_name = spec["source_name"]
        if demo:
            source_name = f"demo-{source_name}"
        
        async with SessionFactory() as session:
            count = await upsert_lake_batch(session, records, source=source_name)
            await update_connector_health(
                session, f"{'demo-' if demo else ''}{connector_name}", "healthy",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=count
            )
        
        logger.info(f"Successfully ingested {count} records from {connector_name} (demo={demo})")
        return {
            "status": "success",
            "connector": connector_name,
            "demo": demo,
            "fetched": len(raw_data),
            "validated": len(df),
            "ingested": count,
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }
        
    except RuntimeError as e:
        if "authentication" in str(e).lower():
            logger.exception(f"{connector_name} authentication failed")
            async with SessionFactory() as session:
                await update_connector_health(
                    session, f"{'demo-' if demo else ''}{connector_name}", "degraded",
                    latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                    records=0
                )
            return {
                "status": "error",
                "connector": connector_name,
                "demo": demo,
                "error": str(e),
                "error_type": "authentication",
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        raise
    except Exception as e:
        logger.exception(f"{connector_name} ingestion failed: {e}")
        async with SessionFactory() as session:
            await update_connector_health(
                session, f"{'demo-' if demo else ''}{connector_name}", "degraded",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=0
            )
        return {
            "status": "error",
            "connector": connector_name,
            "demo": demo,
            "error": str(e),
            "error_type": "ingestion",
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }


async def run_all_connectors(selected: Optional[list] = None, demo: bool = False, dry_run: bool = False) -> dict:
    """Run ingestion for all or selected connectors."""
    connectors_to_run = selected or list(CONNECTOR_SPECS.keys())
    results = {}
    
    for name in connectors_to_run:
        if name not in CONNECTOR_SPECS:
            logger.error(f"Unknown connector: {name}")
            results[name] = {"status": "error", "connector": name, "error": f"Unknown connector: {name}", "demo": demo}
            continue
        
        try:
            config = build_connector_config(CONNECTOR_SPECS[name], argparse.Namespace(), demo)
            result = await run_connector_ingestion(name, config, demo, dry_run)
            results[name] = result
        except ValueError as e:
            logger.error(f"Config error for {name}: {e}")
            results[name] = {"status": "error", "connector": name, "demo": demo, "error": str(e), "error_type": "config"}
        except Exception as e:
            logger.exception(f"Unexpected error for {name}: {e}")
            results[name] = {"status": "error", "connector": name, "demo": demo, "error": str(e), "error_type": "unexpected"}
    
    return results


def main():
    parser = argparse.ArgumentParser(description="SITA Unified Ingestion Pipeline — Demo & Production")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode (uses DEMO_* env vars, tags with demo tenant)")
    parser.add_argument("--connector", choices=list(CONNECTOR_SPECS.keys()) + ["all"], default="all", help="Connector to run")
    parser.add_argument("--config", help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate but don't write to DB")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--json-logs", action="store_true", help="Output structured JSON logs (for k8s)")
    
    # Common connector args (work for both demo and prod)
    parser.add_argument("--base-url", help="Base URL for connector API")
    parser.add_argument("--api-key", help="API key (format varies by connector)")
    parser.add_argument("--key-id", help="Key ID (AppScan)")
    parser.add_argument("--key-secret", help="Key Secret (AppScan)")
    parser.add_argument("--account-id", help="Account/Org ID (AppScan)")
    parser.add_argument("--application-id", help="Application ID (AppScan)")
    parser.add_argument("--page-size", type=int, help="Page size for pagination")
    parser.add_argument("--scope", choices=["application", "org"], help="Scope for issues query (AppScan)")
    parser.add_argument("--source-type", choices=["dam", "waf", "csv"], help="Source type (Imperva/Compliance)")
    parser.add_argument("--csv-path", help="CSV file path (Compliance)")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(json_format=args.json_logs, level=log_level)
    
    # Load config from file if provided
    if args.config:
        file_config = load_config(args.config)
        for key, value in file_config.items():
            if not getattr(args, key.replace("-", "_"), None):
                setattr(args, key.replace("-", "_"), value)
    
    selected = None if args.connector == "all" else [args.connector]
    
    logger.info(f"Starting unified ingestion (demo={args.demo}) for: {selected or 'all connectors'}")
    logger.info(f"Dry run: {args.dry_run}")
    
    results = asyncio.run(run_all_connectors(selected, demo=args.demo, dry_run=args.dry_run))
    
    print("\n=== INGESTION RESULTS ===")
    print(yaml.dump(results, default_flow_style=False))
    
    # Exit codes
    has_errors = any(r.get("status") == "error" for r in results.values())
    has_auth_errors = any(r.get("error_type") == "authentication" for r in results.values())
    
    if has_auth_errors:
        sys.exit(2)
    elif has_errors:
        sys.exit(3)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()