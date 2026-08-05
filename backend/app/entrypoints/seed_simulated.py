"""Seed the SITA platform with simulated OEM data.

Injects realistic synthetic payloads into `staging`, runs them through the
normaliser + lake writer into the warehouse (findings, alerts, connector
health, risk scores), so the M2/M3 dashboards, tests and REST-served reports
can be developed before live OEM connectivity is available.

Usage:
    python -m app.entrypoints.seed_simulated --sources appscan,imperva_dam --count 200
    python -m app.entrypoints.seed_simulated --sources all --count 500
    python -m app.entrypoints.seed_simulated --sources apisec --count 50 --days 30

Flags:
    --sources   comma-separated list or "all" (default: all)
    --count     records per source per simulated poll (default: 200)
    --days      generate records spread over the last N days (default: 7)
    --publish   also publish raw payloads to the Redis stream (full pipeline)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db import SessionFactory
from app.lake.writer import (
    update_connector_health,
    upsert_findings,
    upsert_lake_batch,
    upsert_risk_scores,
)
from app.processing.normaliser import Normaliser
from app.processing.risk_engine import RiskInputs, fused_risk, risk_bucket
from app.synthetic.generator import SyntheticOEMFeed

logger = logging.getLogger(__name__)

ALL_SOURCES = ["appscan", "imperva_dam", "imperva_waf", "apisec", "compliance"]

APPS = ["legacy-api", "payment-gateway", "customer-portal", "document-svc", "internal-hr"]

SOURCE_OWNER = {
    "appscan": "AppSec Engineer",
    "imperva_dam": "DB Security Engineer",
    "imperva_waf": "AppSec Engineer",
    "apisec": "AppSec Engineer",
    "compliance": "Compliance Officer",
}


def _normalise_records(records: list[dict], source: str, normaliser: Normaliser) -> list[dict]:
    """Normalise OEM-shaped records into canonical warehouse rows."""
    import pandas as pd

    df = normaliser.normalise(pd.DataFrame(records), source)
    if df is None or df.empty:
        return []
    rows = df.to_dict(orient="records")
    for row in rows:
        row["source"] = source
    return rows


async def write_staging_batch(session, source: str, records: list[dict]) -> uuid.UUID:
    batch_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO staging.batch_runs (id, connector, source, started_at, finished_at,
                                            records_fetched, records_valid, records_rejected, status)
            VALUES (:id, :connector, :source, now(), now(), :fetched, :valid, :rejected, 'completed')
            """
        ),
        {
            "id": batch_id,
            "connector": source,
            "source": SOURCE_OWNER.get(source, source),
            "fetched": len(records),
            "valid": len(records),
            "rejected": 0,
        },
    )
    for record in records:
        await session.execute(
            text(
                """
                INSERT INTO staging.raw_records (batch_id, source, external_id, raw_payload, received_at)
                VALUES (:batch_id, :source, :external_id, CAST(:payload AS jsonb), now())
                """
            ),
            {
                "batch_id": batch_id,
                "source": source,
                "external_id": str(record.get("id") or record.get("event_id") or record.get("api_id")
                                   or record.get("control_id") or uuid.uuid4()),
                "payload": __import__("json").dumps(record),
            },
        )
    return batch_id


async def compute_and_store_risks(session, findings: list[dict]) -> int:
    """Compute fused risk scores per app from seeded findings."""
    from collections import defaultdict

    by_app: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_app[f.get("app_name", "unknown")].append(f)

    weights = {"appscan": 0.35, "imperva": 0.25, "exposure": 0.20, "compliance": 0.20}
    rows = []
    for app, recs in by_app.items():
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in recs:
            sev = str(r.get("severity") or "info").lower()
            if sev in counts:
                counts[sev] += 1
        imperva_count = sum(
            1 for r in recs if r.get("source") in ("imperva_dam", "imperva_waf")
        )
        exposures = [
            float(r.get("exposure_score") or 0)
            for r in recs
            if r.get("source") == "apisec" and r.get("exposure_score") is not None
        ]
        compliance_pct = 84.0  # consistent with seed-demo.sql baseline
        inputs = RiskInputs(
            appscan_severity_counts=counts,
            imperva_violation_count=imperva_count,
            api_exposure_scores=exposures,
            compliance_pct=compliance_pct,
        )
        score = fused_risk(inputs, weights)
        rows.append(
            {
                "app_name": app,
                "score_date": datetime.now(timezone.utc).date(),
                "fused_score": score,
                "signal_appscan": round(weights["appscan"] * min(sum(counts.values()), 100), 1),
                "signal_imperva": round(weights["imperva"] * min(imperva_count * 5, 100), 1),
                "signal_api_exposure": round(weights["exposure"] * (sum(exposures) / len(exposures) if exposures else 0), 1),
                "signal_compliance_penalty": round(weights["compliance"] * (100 - compliance_pct), 1),
                "bucket": risk_bucket(score),
            }
        )
    if rows:
        return await upsert_risk_scores(session, rows)
    return 0


async def seed_source(
    session,
    source: str,
    count: int,
    days: int,
    feed: SyntheticOEMFeed,
    normaliser: Normaliser,
) -> tuple[int, int, int]:
    logger.info("seeding %s (%d records over %d days)", source, count, days)
    if source == "imperva":
        source = "imperva_dam"

    records = feed.batch(source, count)
    # spread timestamps over the requested window to make trend charts meaningful
    now = datetime.now(timezone.utc)

    for i, rec in enumerate(records):
        ts = now - timedelta(days=days * (i / max(count, 1)))
        ts_iso = ts.isoformat()
        ts_col = "timestamp"
        if source == "appscan":
            ts_col = "last_found_date"
        elif source == "imperva_waf":
            ts_col = "block_time"
        elif source == "apisec":
            ts_col = "discovered_at"
        elif source == "compliance":
            ts_col = "due_date"
        rec[ts_col] = ts_iso
        rec["app_name"] = rec.get("application_name") or rec.get("database_name") or rec.get("application") or rec.get("endpoint")

    batch_id = await write_staging_batch(session, source, records)
    logger.info("wrote staging batch %s (%d raw records)", batch_id, len(records))

    rows = _normalise_records(records, source, normaliser)
    if not rows:
        logger.warning("normaliser produced no rows for %s", source)
        await session.commit()
        return len(records), 0, 0

    await upsert_findings(session, rows, source=source)
    logger.info("upserted %d findings for %s", len(rows), source)

    alerts: list[dict] = []
    # severity-based alerts only; aggregate rules run via analytics scheduler
    for row in rows:
        sev = str(row.get("severity") or "info").lower()
        if sev == "critical":
            alerts.append(
                {
                    "id": str(uuid.uuid4()),
                    "rule_id": "critical_record",
                    "title": f"Critical {source} finding ingested",
                    "description": row.get("title"),
                    "severity": "critical",
                    "source": source,
                    "target_id": row.get("app_name"),
                    "status": "new",
                    "dedup_key": f"critical_record:{source}:{row.get('app_name')}",
                }
            )
    if alerts:
        await upsert_lake_batch(session, rows, source=source, alerts=alerts)
        logger.info("created %d alerts for %s", len(alerts), source)

    await update_connector_health(
        session,
        source,
        "healthy",
        latency_ms=feed.rng.randint(20, 200),
        records=count,
    )
    await session.commit()
    return len(records), len(rows), len(alerts)


async def run(sources: list[str], count: int, days: int, publish: bool) -> None:
    feed = SyntheticOEMFeed(seed=42)
    normaliser = Normaliser()
    logger.info("seeding sources=%s count=%d days=%d publish=%s", sources, count, days, publish)
    total_fetched = total_rows = total_alerts = 0
    findings_sink: list[dict] = []
    async with SessionFactory() as session:
        for source in sources:
            fetched, rows, alerts = await seed_source(session, source, count, days, feed, normaliser)
            total_fetched += fetched
            total_rows += rows
            total_alerts += alerts
            findings_sink.extend(rows)
        risk_rows = await compute_and_store_risks(session, findings_sink)
    logger.info(
        "seed complete: fetched=%d normalised=%d alerts=%d risk_scores=%d",
        total_fetched,
        total_rows,
        total_alerts,
        risk_rows,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed SITA platform with simulated OEM data")
    parser.add_argument("--sources", default="all", help="comma-separated sources or 'all'")
    parser.add_argument("--count", type=int, default=200, help="records per source")
    parser.add_argument("--days", type=int, default=7, help="spread records over last N days")
    parser.add_argument("--publish", action="store_true", help="publish to Redis stream (full pipeline)")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    sources = ALL_SOURCES if args.sources == "all" else [s.strip() for s in args.sources.split(",")]
    if args.publish:
        raise NotImplementedError("--publish requires a running Redis + processing consumer; use default staging path")
    asyncio.run(run(sources, args.count, args.days, args.publish))


if __name__ == "__main__":
    main()
