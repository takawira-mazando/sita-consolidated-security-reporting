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
    upsert_agents,
    upsert_alerts,
    upsert_api_endpoints,
    upsert_compliance_gaps,
    upsert_compliance_snapshots,
    upsert_database_inventory,
    upsert_findings,
    upsert_risk_scores,
    upsert_slo_metrics,
    upsert_system_metrics,
    upsert_waf_blocks,
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

DB_NAMES = ["DB-CUST-01", "DB-PAY-01", "DB-DOC-01", "DB-HR-01", "DB-CUST-02"]

WAF_ATTACKS = ["sqli", "xss", "rce", "lfi", "shellshock", "scanner-probe", "brute-force"]

AGENTS = [
    {"name": "dam-agent-01", "role": "dam", "version": "9.5.1", "status": "online", "host": "db-cust-01"},
    {"name": "dam-agent-02", "role": "dam", "version": "9.5.1", "status": "online", "host": "db-pay-01"},
    {"name": "dam-agent-03", "role": "dam", "version": "9.4.2", "status": "online", "host": "db-doc-01"},
    {"name": "dam-agent-04", "role": "dam", "version": "9.4.2", "status": "degraded", "host": "db-hr-01"},
    {"name": "waf-agent-01", "role": "waf", "version": "14.2.0", "status": "online", "host": "edge-waf-01"},
    {"name": "waf-agent-02", "role": "waf", "version": "14.2.0", "status": "online", "host": "edge-waf-02"},
    {"name": "apisec-agent-01", "role": "apisec", "version": "3.1.4", "status": "online", "host": "api-gw-01"},
    {"name": "ingestion-worker-01", "role": "ingestion", "version": "1.8.0", "status": "online", "host": "worker-01"},
    {"name": "ingestion-worker-02", "role": "ingestion", "version": "1.8.0", "status": "offline", "host": "worker-02"},
]


def _normalise_records(records: list[dict], source: str, normaliser: Normaliser) -> list[dict]:
    """Normalise OEM-shaped records into canonical warehouse rows."""
    import json

    import pandas as pd

    df = normaliser.normalise(pd.DataFrame(records), source)
    if df is None or df.empty:
        return []
    rows = df.to_dict(orient="records")
    for row in rows:
        row["source"] = source
    return json.loads(json.dumps(rows, default=str))


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


async def compute_and_store_risks(session, findings: list[dict], days: int = 30) -> int:
    """Compute fused risk scores per app across the last `days` days."""
    from collections import defaultdict

    by_app: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_app[f.get("app_name", "unknown")].append(f)

    weights = {"appscan": 0.35, "imperva": 0.25, "exposure": 0.20, "compliance": 0.20}
    rows: list[dict] = []
    today = datetime.now(timezone.utc).date()
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
        base_score = fused_risk(inputs, weights)
        # walk back `days` days, adding mild noise so the 30-day trend chart has shape
        import random

        rng = random.Random(42)
        for offset in range(days):
            noise = rng.uniform(-6, 6)
            score = max(5.0, min(98.0, base_score + noise + offset * 0.2))
            rows.append(
                {
                    "app_name": app,
                    "score_date": today - timedelta(days=offset),
                    "fused_score": round(score, 1),
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


async def seed_metric_tables(session, feed: SyntheticOEMFeed) -> None:
    """Seed all derived metric tables the RBAC dashboards render.

    Covers WAF blocks, API exposure inventory, compliance snapshots + gaps,
    system health, agent inventory, SLO (MTTD/MTTR) and database inventory.
    """
    now = datetime.now(timezone.utc)
    rng = feed.rng

    # ---- WAF blocks (AppSec: WAF Blocks stat + WAF Block Summary) ----
    waf_rows = []
    for i in range(120):
        app = rng.choice(APPS)
        ts = now - timedelta(minutes=rng.randint(0, 60 * 24 * 3))
        waf_rows.append({
            "app_name": app,
            "attack_type": rng.choice(WAF_ATTACKS),
            "request_uri": rng.choice(["/api/v1/pay", "/api/v2/admin", "/api/v3/export", "/soap/login", "/api/v1/orders"]),
            "action": rng.choice(["block", "block", "block", "log"]),
            "src_ip": f"198.51.100.{rng.randint(1, 254)}",
            "block_time": ts.isoformat(),
        })
    upserted_waf = await upsert_waf_blocks(session, waf_rows)
    logger.info("seeded %d WAF block records", upserted_waf)

    # ---- API exposure inventory (AppSec: API Exposure table) ----
    api_rows = []
    endpoints = [
        ("customer-portal", "/api/v3/export", "GET", True, 85.0),
        ("customer-portal", "/api/v2/admin", "POST", True, 70.0),
        ("payment-gateway", "/api/v1/pay", "POST", False, 45.0),
        ("payment-gateway", "/api/v1/refunds", "POST", False, 30.0),
        ("document-svc", "/api/v1/export", "GET", False, 20.0),
        ("legacy-api", "/soap/login", "POST", False, 60.0),
        ("internal-hr", "/api/v1/employees", "GET", False, 12.0),
        ("internal-hr", "/api/v1/payroll", "POST", True, 55.0),
    ]
    for app, endpoint, method, shadow, exposure in endpoints:
        api_rows.append({
            "app_name": app,
            "endpoint": endpoint,
            "method": method,
            "is_shadow": shadow,
            "exposure_score": exposure,
            "discovered_at": (now - timedelta(days=rng.randint(1, 90))).isoformat(),
            "last_seen": (now - timedelta(hours=rng.randint(1, 72))).isoformat(),
        })
    upserted_api = await upsert_api_endpoints(session, api_rows)
    logger.info("seeded %d API endpoint records", upserted_api)

    # ---- Compliance snapshots (trend) + gaps (Compliance dashboard) ----
    snapshots = []
    for framework, base, spread in (("popia", 84.0, 2.0), ("iso_27001", 72.0, 2.5)):
        for offset in range(12):
            snap_date = (now - timedelta(weeks=11 - offset)).date()
            score = max(30.0, min(99.0, base + (offset - 11) * spread + rng.uniform(-1.5, 1.5)))
            snapshots.append({
                "framework": framework,
                "snapshot_date": snap_date,
                "overall_score": round(score, 1),
                "details": {
                    "data_inventory": 88, "consent": 76, "breach_response": 65,
                    "subject_rights": 70, "cross_border": 45,
                } if framework == "popia" else {
                    "A5_policies": 80, "A6_org": 75, "A8_asset": 70,
                    "A9_access": 65, "A12_ops": 60, "A16_incident": 78,
                },
                "total_controls": 117 if framework == "popia" else 130,
                "passed_controls": int(117 * score / 100) if framework == "popia" else int(130 * score / 100),
            })
    upserted_snap = await upsert_compliance_snapshots(session, snapshots)
    logger.info("seeded %d compliance snapshots", upserted_snap)

    gap_rows = [
        {"framework": "popia", "control_id": "POPIA-72", "domain": "Cross-Border",
         "description": "Cross-border data transfer not documented or covered by lawful basis.",
         "owner": "Legal", "severity": "critical", "due_date": (now + timedelta(days=3)).date(), "status": "open", "evidence_count": 2},
        {"framework": "popia", "control_id": "POPIA-22", "domain": "Breach Response",
         "description": "Breach notification procedure untested; notification timelines unverified.",
         "owner": "CISO", "severity": "high", "due_date": (now + timedelta(days=12)).date(), "status": "open", "evidence_count": 5},
        {"framework": "popia", "control_id": "POPIA-19", "domain": "Consent",
         "description": "Consent records for marketing data incomplete for 2019 cohort.",
         "owner": "DPO", "severity": "high", "due_date": (now + timedelta(days=20)).date(), "status": "in_progress", "evidence_count": 8},
        {"framework": "popia", "control_id": "POPIA-57", "domain": "Data Subject Rights",
         "description": "Subject access request SLA not instrumented end-to-end.",
         "owner": "DPO", "severity": "medium", "due_date": (now + timedelta(days=25)).date(), "status": "open", "evidence_count": 3},
        {"framework": "popia", "control_id": "POPIA-63", "domain": "Data Inventory",
         "description": "Data inventory missing classification for 12 new apps.",
         "owner": "Data Ops", "severity": "medium", "due_date": (now + timedelta(days=30)).date(), "status": "in_progress", "evidence_count": 4},
        {"framework": "popia", "control_id": "POPIA-11", "domain": "Data Inventory",
         "description": "Data flow map for payment data incomplete.",
         "owner": "Data Ops", "severity": "medium", "due_date": (now - timedelta(days=10)).date(), "status": "open", "evidence_count": 2},
        {"framework": "iso_27001", "control_id": "ISO-A.12.6", "domain": "Operations",
         "description": "Vulnerability scan frequency inadequate for production estate.",
         "owner": "AppSec", "severity": "high", "due_date": (now + timedelta(days=10)).date(), "status": "in_progress", "evidence_count": 6},
        {"framework": "iso_27001", "control_id": "ISO-A.9.2", "domain": "Access Control",
         "description": "Access review for Q2 not performed for privileged accounts.",
         "owner": "IT Ops", "severity": "medium", "due_date": (now + timedelta(days=5)).date(), "status": "open", "evidence_count": 1},
        {"framework": "iso_27001", "control_id": "ISO-A.8.2", "domain": "Asset Management",
         "description": "Asset register missing ownership for 4 shared services.",
         "owner": "IT Ops", "severity": "medium", "due_date": (now + timedelta(days=18)).date(), "status": "open", "evidence_count": 2},
        {"framework": "iso_27001", "control_id": "ISO-A.16.1", "domain": "Incident Management",
         "description": "Incident response playbook not tested in last 12 months.",
         "owner": "CISO", "severity": "high", "due_date": (now + timedelta(days=35)).date(), "status": "open", "evidence_count": 0},
        {"framework": "iso_27001", "control_id": "ISO-A.5.1", "domain": "Policies",
         "description": "Information security policy review cycle overdue by 60 days.",
         "owner": "CISO", "severity": "medium", "due_date": (now - timedelta(days=20)).date(), "status": "open", "evidence_count": 3},
        {"framework": "iso_27001", "control_id": "ISO-A.9.4", "domain": "Access Control",
         "description": "Privileged session monitoring not enabled on DB-CUST-01.",
         "owner": "DB Sec", "severity": "high", "due_date": (now + timedelta(days=15)).date(), "status": "open", "evidence_count": 1},
    ]
    upserted_gaps = await upsert_compliance_gaps(session, gap_rows)
    logger.info("seeded %d compliance gaps", upserted_gaps)

    # ---- System health metrics (SRE: System Health panel) ----
    sys_rows = []
    base_metrics = {"cpu": 42, "memory": 61, "disk_io": 34, "queue_depth": 12, "uptime": 99}
    for metric, base in base_metrics.items():
        sys_rows.append({
            "metric": metric,
            "value": int(max(0, min(100, base + rng.randint(-6, 6)))),
            "unit": "%",
            "recorded_at": now.isoformat(),
        })
    upserted_sys = await upsert_system_metrics(session, sys_rows)
    logger.info("seeded %d system metrics", upserted_sys)

    # ---- Agent inventory (SRE: DAM Agents + Agent Versions) ----
    agent_rows = []
    for i, a in enumerate(AGENTS):
        agent_rows.append({
            "name": a["name"],
            "role": a["role"],
            "version": a["version"],
            "status": a["status"],
            "host": a["host"],
            "last_seen": (now - timedelta(minutes=rng.randint(0, 60 * 6))).isoformat(),
        })
    upserted_agents = await upsert_agents(session, agent_rows)
    logger.info("seeded %d agents", upserted_agents)

    # ---- SLO metrics (SOC: MTTD/MTTR trend) ----
    slo_rows = []
    for week in range(7):
        week_start = (now - timedelta(weeks=6 - week)).date()
        slo_rows.append({"metric": "mttd", "week_start": week_start.isoformat(),
                         "value_hours": int(max(1, 5 - week * 0.5 + rng.uniform(-0.8, 0.8)))})
        slo_rows.append({"metric": "mttr", "week_start": week_start.isoformat(),
                         "value_hours": int(max(2, 26 - week * 2.2 + rng.uniform(-2, 2)))})
    upserted_slo = await upsert_slo_metrics(session, slo_rows)
    logger.info("seeded %d SLO metric rows", upserted_slo)

    # ---- Database inventory (DBSec: Databases Monitored + Coverage) ----
    db_rows = []
    for db in DB_NAMES:
        db_rows.append({
            "name": db,
            "engine": rng.choice(["PostgreSQL 15", "PostgreSQL 14", "Oracle 19c"]),
            "monitored": True,
            "agent_version": "9.5.1",
            "last_heartbeat": (now - timedelta(minutes=rng.randint(0, 5))).isoformat(),
        })
    upserted_dbs = await upsert_database_inventory(session, db_rows)
    logger.info("seeded %d database inventory rows", upserted_dbs)


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
        return len(records), [], 0

    await upsert_findings(session, rows, source=source)
    logger.info("upserted %d findings for %s", len(rows), source)

    alerts: list[dict] = []
    # severity-based alerts; vary status so the SOC timeline/queue look alive
    status_cycle = ["new", "new", "acknowledged", "investigating", "resolved"]
    for row in rows:
        sev = str(row.get("severity") or "info").lower()
        if sev in ("critical", "high"):
            fired = now - timedelta(hours=feed.rng.randint(1, 72))
            status = feed.rng.choice(status_cycle)
            alerts.append(
                {
                    "id": str(uuid.uuid4()),
                    "rule_id": f"{sev}_record",
                    "title": f"{sev.title()} {source} finding ingested",
                    "description": row.get("title"),
                    "severity": sev,
                    "source": source,
                    "target_id": row.get("app_name"),
                    "status": status,
                    "dedup_key": f"{sev}_record:{source}:{row.get('app_name')}",
                    "first_triggered": fired.isoformat(),
                    "last_triggered": fired.isoformat(),
                }
            )
    if alerts:
        await upsert_alerts(session, alerts, commit=False)
        logger.info("created %d alerts for %s", len(alerts), source)

    await update_connector_health(
        session,
        source,
        "healthy",
        latency_ms=feed.rng.randint(20, 200),
        records=count,
    )
    await session.commit()
    return len(records), rows, len(alerts)


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
            total_rows += len(rows)
            total_alerts += alerts
            findings_sink.extend(rows)
        risk_rows = await compute_and_store_risks(session, findings_sink, days=30)
        await seed_metric_tables(session, feed)
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
