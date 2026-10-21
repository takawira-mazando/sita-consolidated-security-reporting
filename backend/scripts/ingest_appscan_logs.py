#!/usr/bin/env python3
"""
AppScan Cloud Log Ingestion Pipeline

Pulls vulnerability findings from AppScan Cloud API and ingests them into
the SITA Unified Intelligence Platform database.

Usage:
    python -m scripts.ingest_appscan_logs --config /etc/appscan/config.yaml
    python -m scripts.ingest_appscan_logs --api-key $APPSCAN_API_KEY --account-id $ACCOUNT_ID --app-id $APP_ID

Exit codes:
    0  - Success (ingested or dry-run)
    1  - Configuration error
    2  - Authentication failed
    3  - Fetch/parse/validate failed
    4  - Database ingest failed
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

import yaml

from app.connectors.appscan import AppScanConnector
from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch, update_connector_health
from app.config import settings

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

logger = logging.getLogger("appscan_ingest")


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def build_connector_config(args) -> dict:
    """Build connector config from CLI args or config file."""
    api_key = args.api_key or os.getenv("APPSCAN_API_KEY", "")
    key_id = args.key_id or os.getenv("APPSCAN_KEY_ID") or settings.appscan_key_id or ""
    key_secret = args.key_secret or os.getenv("APPSCAN_KEY_SECRET") or settings.appscan_key_secret or ""
    if ":" in api_key and not key_id and not key_secret:
        key_id, key_secret = api_key.split(":", 1)

    config = {
        "base_url": args.base_url or os.getenv("APPSCAN_BASE_URL") or settings.appscan_base_url or "https://cloud.appscan.com",
        "api_key": api_key,
        "key_id": key_id,
        "key_secret": key_secret,
        "account_id": args.account_id or os.getenv("APPSCAN_ACCOUNT_ID") or settings.appscan_account_id or "",
        "application_id": args.application_id or os.getenv("APPSCAN_APPLICATION_ID") or settings.appscan_application_id or "",
        "page_size": args.page_size or int(os.getenv("APPSCAN_PAGE_SIZE", str(settings.appscan_page_size or 200))),
        "scope": args.scope or os.getenv("APPSCAN_SCOPE") or settings.appscan_scope or "application",
    }
    return config


async def run_ingestion(config: dict, dry_run: bool = False) -> dict:
    """Run the AppScan ingestion pipeline."""
    logger.info("Starting AppScan ingestion pipeline", extra={"config_keys": list(config.keys())})
    start_time = datetime.now(timezone.utc)

    connector = AppScanConnector(config)
    connector.logger = logger

    try:
        logger.info("Authenticating with AppScan Cloud...")
        authenticated = await connector.authenticate()
        if not authenticated:
            raise RuntimeError("AppScan authentication failed")

        logger.info("Fetching issues from AppScan...")
        raw_issues = await connector.poll()
        logger.info(f"Fetched {len(raw_issues)} raw issues")

        if not raw_issues:
            logger.warning("No issues returned from AppScan")
            return {
                "status": "success",
                "fetched": 0,
                "ingested": 0,
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }

        logger.info("Parsing and validating issues...")
        df = connector.parse(raw_issues)
        df = connector.validate(df)
        logger.info(f"Validated {len(df)} issues")

        records = df.to_dict(orient="records")

        if dry_run:
            logger.info("DRY RUN - would ingest %d records", len(records))
            for i, r in enumerate(records[:3]):
                logger.info(f"  Sample {i+1}: {r.get('external_id')} - {r.get('vulnerability_name')} [{r.get('severity')}]")
            return {
                "status": "dry_run",
                "fetched": len(raw_issues),
                "validated": len(df),
                "would_ingest": len(records),
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }

        logger.info("Ingesting into database...")
        async with SessionFactory() as session:
            count = await upsert_lake_batch(session, records, source="appscan")
            await update_connector_health(
                session, "appscan", "healthy",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=count
            )

        logger.info(f"Successfully ingested {count} AppScan findings", extra={"ingested_count": count})
        return {
            "status": "success",
            "fetched": len(raw_issues),
            "validated": len(df),
            "ingested": count,
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }

    except RuntimeError as e:
        if "authentication" in str(e).lower():
            logger.exception("Authentication failed")
            async with SessionFactory() as session:
                await update_connector_health(
                    session, "appscan", "degraded",
                    latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                    records=0
                )
            return {
                "status": "error",
                "error": str(e),
                "error_type": "authentication",
                "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            }
        raise
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        async with SessionFactory() as session:
            await update_connector_health(
                session, "appscan", "degraded",
                latency_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                records=0
            )
        return {
            "status": "error",
            "error": str(e),
            "error_type": "ingestion",
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }


def main():
    parser = argparse.ArgumentParser(description="AppScan Cloud Log Ingestion Pipeline")
    parser.add_argument("--config", help="Path to YAML config file")
    parser.add_argument("--base-url", default="https://cloud.appscan.com", help="AppScan Cloud base URL")
    parser.add_argument("--api-key", help="AppScan API key (or set APPSCAN_API_KEY env), format: key_id:key_secret")
    parser.add_argument("--key-id", help="AppScan Key ID (or set APPSCAN_KEY_ID env)")
    parser.add_argument("--key-secret", help="AppScan Key Secret (or set APPSCAN_KEY_SECRET env)")
    parser.add_argument("--account-id", help="AppScan account/org ID")
    parser.add_argument("--application-id", help="AppScan application ID")
    parser.add_argument("--page-size", type=int, default=200, help="Page size for pagination")
    parser.add_argument("--scope", choices=["application", "org"], default="application", help="Scope for issues query")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate but don't write to DB")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--json-logs", action="store_true", help="Output structured JSON logs (for k8s)")

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

    # Validate required fields
    config = build_connector_config(args)
    missing = []
    if not config.get("key_id") or not config.get("key_secret"):
        missing.append("key_id and key_secret (--key-id/--key-secret or APPSCAN_KEY_ID/APPSCAN_KEY_SECRET, or --api-key with 'key_id:key_secret' format)")
    if not config["account_id"] and not config["application_id"]:
        missing.append("account_id or application_id (--account-id/--application-id or APPSCAN_ACCOUNT_ID/APPSCAN_APPLICATION_ID)")

    if missing:
        logger.error("Missing required configuration: %s", ", ".join(missing))
        parser.print_help()
        sys.exit(1)  # Config error

    logger.info("Configuration loaded:")
    logger.info(f"  Base URL: {config['base_url']}")
    logger.info(f"  Key ID: {config.get('key_id', 'N/A')}")
    logger.info(f"  Account ID: {config['account_id'] or 'N/A'}")
    logger.info(f"  Application ID: {config['application_id'] or 'N/A'}")
    logger.info(f"  Scope: {config['scope']}")
    logger.info(f"  Page Size: {config['page_size']}")
    logger.info(f"  Dry Run: {args.dry_run}")

    result = asyncio.run(run_ingestion(config, dry_run=args.dry_run))

    print("\n=== INGESTION RESULT ===")
    print(yaml.dump(result, default_flow_style=False))

    # Exit codes for k8s
    if result["status"] == "success" or result["status"] == "dry_run":
        sys.exit(0)
    elif result.get("error_type") == "authentication":
        sys.exit(2)  # Auth failed
    else:
        sys.exit(3)  # Ingestion failed


if __name__ == "__main__":
    main()