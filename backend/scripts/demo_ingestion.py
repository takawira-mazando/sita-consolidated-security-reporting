#!/usr/bin/env python3
"""
SITA Platform - Demo Ingestion Pipeline

Runs ingestion against OEM test accounts (AppScan, Imperva, APISec, Compliance)
and tags all data with demo tenant scope for frontend demo mode.

Usage:
    python -m scripts.demo_ingestion --all
    python -m scripts.demo_ingestion --connector appscan
    python -m scripts.demo_ingestion --connector imperva_waf --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import yaml

from app.connectors.appscan import AppScanConnector
from app.connectors.imperva import ImpervaConnector
from app.connectors.apisec import ApiSecurityConnector
from app.connectors.compliance import ComplianceConnector
from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch, update_connector_health
from app.config import settings

# Structured JSON logging
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

logger = logging.getLogger("demo_ingestion")

# Demo tenant configuration - all demo data tagged with this
DEMO_TENANT = {
    "department_id": "00000000-0000-0000-0000-000000000001",
    "branch_id": "00000000-0000-0000-0000-000000000001",
    "ministry_id": "00000000-0000-0000-0000-000000000001",
    "cluster_id": "00000000-0000-0000-0000-000000000001",
    "app_name_prefix": "DEMO-",
}

CONNECTOR_CONFIGS = {
    "appscan": {
        "class": AppScanConnector,
        "env_prefix": "DEMO_APPSCAN",
        "required": ["KEY_ID", "KEY_SECRET", "ACCOUNT_ID"],
        "optional": ["BASE_URL", "APPLICATION_ID", "PAGE_SIZE", "SCOPE"],
        "defaults": {
            "BASE_URL": "https://cloud.appscan.com",
            "PAGE_SIZE": "200",
            "SCOPE": "application",
        },
    },
    "imperva_dam": {
        "class": ImpervaConnector,
        "env_prefix": "DEMO_IMPERVA_DAM",
        "required": ["BASE_URL", "API_KEY", "SOURCE_TYPE"],
        "optional": [],
        "defaults": {"SOURCE_TYPE": "dam"},
    },
    "imperva_waf": {
        "class": ImpervaConnector,
        "env_prefix": "DEMO_IMPERVA_WAF",
        "required": ["BASE_URL", "API_KEY", "SOURCE_TYPE"],
        "optional": [],
        "defaults": {"SOURCE_TYPE": "waf"},
    },
    "apisec": {
        "class": ApiSecurityConnector,
        "env_prefix": "DEMO_APISEC",
        "required": ["BASE_URL", "API_KEY"],
        "optional": [],
        "defaults": {},
    },
    "compliance": {
        "class": ComplianceConnector,
        "env_prefix": "DEMO_COMPLIANCE",
        "required": ["SOURCE_TYPE"],
        "optional": ["CSV_PATH"],
        "defaults": {"SOURCE_TYPE": "csv", "CSV_PATH": "/app/data/demo_compliance.csv"},
    },
}


def load_demo_config(connector_name: str) -> dict:
    """Load connector config from environment variables with DEMO_ prefix."""
    cfg = CONNECTOR_CONFIGS[connector_name]
    prefix = cfg["env_prefix"]
    
    config = {}
    # Required fields
    for field in cfg["required"]:
        env_key = f"{prefix}_{field}"
        value = os.getenv(env_key)
        if not value:
            raise ValueError(f"Missing required env var: {env_key}")
        config[field.lower()] = value
    
    # Optional fields with defaults
    for field in cfg["optional"]:
        env_key = f"{prefix}_{field}"
        value = os.getenv(env_key)
        if value:
            config[field.lower()] = value
        elif field in cfg["defaults"]:
            config[field.lower()] = cfg["defaults"][field]
    
    return config


async def run_connector_ingestion(
    connector_name: str, 
    config: dict, 
    dry_run: bool = False,
    demo_tenant: bool = True
) -> dict:
    """Run ingestion for a single connector with demo tenant tagging."""
    logger.info(f"Starting {connector_name} demo ingestion")
    start_time = datetime.now(timezone.utc)
    
    try:
        connector = config["class"](config)
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
                "fetched": 0,
                "ingested": 0,
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        logger.info(f"Parsing and validating {connector_name} data...")
        df = connector.parse(raw_data)
        df = connector.validate(df)
        logger.info(f"Validated {len(df)} records from {connector_name}")
        
        # Tag all records with demo tenant info
        if demo_tenant:
            for _, row in df.iterrows():
                row["department_id"] = DEMO_TENANT["department_id"]
                row["branch_id"] = DEMO_TENANT["branch_id"]
                row["ministry_id"] = DEMO_TENANT["ministry_id"]
                row["cluster_id"] = DEMO_TENANT["cluster_id"]
                # Prefix app_name for easy identification
                if "app_name" in row and row["app_name"]:
                    row["app_name"] = f"{DEMO_TENANT['app_name_prefix']}{row['app_name']}"
                elif "application_name" in row and row["application_name"]:
                    row["application_name"] = f"{DEMO_TENANT['app_name_prefix']}{row['application_name']}"
        
        records = df.to_dict(orient="records")
        
        if dry_run:
            logger.info(f"DRY RUN - {connector_name} would ingest {len(records)} records")
            for i, r in enumerate(records[:3]):
                app_name = r.get("app_name") or r.get("application_name") or "N/A"
                logger.info(f"  Sample {i+1}: {app_name} - {r.get('title', r.get('vulnerability_name', 'N/A'))} [{r.get('severity', 'N/A')}]")
            return {
                "status": "dry_run",
                "connector": connector_name,
                "fetched": len(raw_data),
                "validated": len(df),
                "would_ingest": len(records),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        
        logger.info(f"Ingesting {connector_name} data into database...")
        source_name = connector_name.replace("_", "-")  # e.g., imperva-dam
        async with SessionFactory() as session:
            count = await upsert_lake_batch(session, records, source=source_name)
            await update_connector_health(
                session, f"demo-{connector_name}", "healthy",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=count
            )
        
        logger.info(f"Successfully ingested {count} records from {connector_name}")
        return {
            "status": "success",
            "connector": connector_name,
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
                    session, f"demo-{connector_name}", "degraded",
                    latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                    records=0
                )
            return {
                "status": "error",
                "connector": connector_name,
                "error": str(e),
                "error_type": "authentication",
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        raise
    except Exception as e:
        logger.exception(f"{connector_name} ingestion failed: {e}")
        async with SessionFactory() as session:
            await update_connector_health(
                session, f"demo-{connector_name}", "degraded",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=0
            )
        return {
            "status": "error",
            "connector": connector_name,
            "error": str(e),
            "error_type": "ingestion",
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }


async def run_all_connectors(selected: Optional[list] = None, dry_run: bool = False) -> dict:
    """Run ingestion for all or selected connectors."""
    connectors_to_run = selected or list(CONNECTOR_CONFIGS.keys())
    results = {}
    
    for name in connectors_to_run:
        if name not in CONNECTOR_CONFIGS:
            logger.error(f"Unknown connector: {name}")
            results[name] = {"status": "error", "error": f"Unknown connector: {name}"}
            continue
        
        try:
            config = load_demo_config(name)
            result = await run_connector_ingestion(name, config, dry_run=dry_run)
            results[name] = result
        except ValueError as e:
            logger.error(f"Config error for {name}: {e}")
            results[name] = {"status": "error", "connector": name, "error": str(e), "error_type": "config"}
        except Exception as e:
            logger.exception(f"Unexpected error for {name}: {e}")
            results[name] = {"status": "error", "connector": name, "error": str(e), "error_type": "unexpected"}
    
    return results


def main():
    parser = argparse.ArgumentParser(description="SITA Demo Ingestion Pipeline - OEM Test Accounts")
    parser.add_argument("--connector", choices=list(CONNECTOR_CONFIGS.keys()) + ["all"], 
                        default="all", help="Connector to run (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate but don't write to DB")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--json-logs", action="store_true", help="Output structured JSON logs")
    parser.add_argument("--no-demo-tenant", action="store_true", help="Don't tag with demo tenant (use real org hierarchy)")
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(json_format=args.json_logs, level=log_level)
    
    selected = None if args.connector == "all" else [args.connector]
    demo_tenant = not args.no_demo_tenant
    
    logger.info(f"Starting demo ingestion for: {selected or 'all connectors'}")
    logger.info(f"Demo tenant tagging: {'enabled' if demo_tenant else 'disabled'}")
    logger.info(f"Dry run: {args.dry_run}")
    
    results = asyncio.run(run_all_connectors(selected, dry_run=args.dry_run))
    
    print("\n=== DEMO INGESTION RESULTS ===")
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