import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.compliance import ComplianceGap, ComplianceSnapshot
from app.models.connector_status import ConnectorHealth
from app.models.finding import Finding, Severity
from app.models.metrics import (
    Agent,
    ApiEndpoint,
    DatabaseInventory,
    SloMetric,
    SystemMetric,
    WafBlock,
)
from app.models.risk_score import RiskBucket, RiskScore


def _first(record: dict, *keys: str, default=None):
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).lower() not in ("", "nan", "nat", "none"):
            return value
    return default


def _as_datetime(value, default=None):
    if value is None:
        return default or datetime.now(timezone.utc)
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return default or datetime.now(timezone.utc)
    return parsed.to_pydatetime()


def _as_date(value, default=None):
    if value is None:
        return (default or datetime.now(timezone.utc)).date()
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return (default or datetime.now(timezone.utc)).date()
    return parsed.date()


def record_to_finding(record: dict, source: str = "") -> dict:
    now = datetime.now(timezone.utc)
    source = record.get("source") or source or "unknown"
    severity_raw = str(_first(record, "severity", "risk_level", "priority") or "info").lower()
    if severity_raw not in {s.value for s in Severity}:
        severity_raw = "info"
    first_seen = _as_datetime(_first(record, "first_seen", "timestamp", "discovered_at", "last_seen"), now)
    last_seen = _as_datetime(_first(record, "last_seen", "timestamp", "first_seen", "discovered_at"), now)
    status_raw = str(_first(record, "status", "state") or "open").lower()
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "external_id": str(_first(record, "external_id", "event_id", "id", "control_id") or uuid.uuid4()),
        "app_name": str(_first(record, "app_name", "application_name", "database_name", "endpoint") or "unknown"),
        "severity": severity_raw,
        "title": str(_first(record, "title", "vulnerability_name", "rule_name", "attack_name", "name", "description") or "Finding"),
        "description": _first(record, "description", "details", "summary"),
        "category": _first(record, "category", "domain", "attack_type"),
        "raw_data": record,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "status": status_raw,
        "version": 1,
    }


async def upsert_findings(session: AsyncSession, records: list[dict], source: str = "") -> int:
    if not records:
        return 0
    values = [record_to_finding(record, source) for record in records]
    stmt = pg_insert(Finding).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Finding.source, Finding.external_id],
        set_={
            "severity": stmt.excluded.severity,
            "title": stmt.excluded.title,
            "description": stmt.excluded.description,
            "category": stmt.excluded.category,
            "raw_data": stmt.excluded.raw_data,
            "last_seen": stmt.excluded.last_seen,
            "status": stmt.excluded.status,
            "version": Finding.version + 1,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_lake_batch(
    session: AsyncSession,
    records: list[dict],
    source: str = "",
    alerts: list[dict] | None = None,
) -> int:
    """Persist findings and alerts in a single transaction."""
    if not records:
        return 0
    findings = [record_to_finding(record, source) for record in records]
    stmt = pg_insert(Finding).values(findings)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Finding.source, Finding.external_id],
        set_={
            "severity": stmt.excluded.severity,
            "title": stmt.excluded.title,
            "description": stmt.excluded.description,
            "category": stmt.excluded.category,
            "raw_data": stmt.excluded.raw_data,
            "last_seen": stmt.excluded.last_seen,
            "status": stmt.excluded.status,
            "version": Finding.version + 1,
        },
    )
    await session.execute(stmt)
    if alerts:
        await upsert_alerts(session, alerts, commit=False)
    await session.commit()
    return len(findings)


async def upsert_risk_scores(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = []
    for row in rows:
        bucket_raw = str(row.get("bucket") or "monitored").lower()
        if bucket_raw not in {b.value for b in RiskBucket}:
            bucket_raw = "monitored"
        values.append({
            "id": str(uuid.uuid4()),
            "app_name": row.get("app_name", "unknown"),
            "score_date": row.get("score_date") or datetime.now(timezone.utc).date(),
            "fused_score": float(row.get("fused_score", 0.0)),
            "signal_appscan": row.get("signal_appscan"),
            "signal_imperva": row.get("signal_imperva"),
            "signal_api_exposure": row.get("signal_api_exposure"),
            "signal_compliance_penalty": row.get("signal_compliance_penalty"),
            "bucket": bucket_raw,
        })
    stmt = pg_insert(RiskScore).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[RiskScore.app_name, RiskScore.score_date],
        set_={
            "fused_score": stmt.excluded.fused_score,
            "signal_appscan": stmt.excluded.signal_appscan,
            "signal_imperva": stmt.excluded.signal_imperva,
            "signal_api_exposure": stmt.excluded.signal_api_exposure,
            "signal_compliance_penalty": stmt.excluded.signal_compliance_penalty,
            "bucket": stmt.excluded.bucket,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_alerts(session: AsyncSession, alerts: list[dict], commit: bool = True) -> int:
    if not alerts:
        return 0
    now = datetime.now(timezone.utc)
    values = []
    for alert in alerts:
        severity_raw = str(alert.get("severity") or "info").lower()
        if severity_raw not in {s.value for s in Severity}:
            severity_raw = "info"
        status_raw = str(alert.get("status") or "new").lower()
        if status_raw not in {s.value for s in AlertStatus}:
            status_raw = "new"
        triggered = _as_datetime(alert.get("first_triggered"), now)
        values.append({
            "id": str(alert.get("id") or uuid.uuid4()),
            "rule_id": str(alert.get("rule_id") or "unknown"),
            "title": str(alert.get("title") or "Alert"),
            "description": alert.get("description"),
            "severity": severity_raw,
            "source": alert.get("source"),
            "target_id": alert.get("target_id"),
            "status": status_raw,
            "enriched_data": alert.get("enriched_data"),
            "dedup_key": alert.get("dedup_key"),
            "dedup_count": int(alert.get("dedup_count") or 1),
            "first_triggered": triggered,
            "last_triggered": _as_datetime(alert.get("last_triggered"), triggered),
        })
    stmt = pg_insert(Alert).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Alert.id],
        set_={
            "status": stmt.excluded.status,
            "severity": stmt.excluded.severity,
            "enriched_data": stmt.excluded.enriched_data,
            "dedup_count": stmt.excluded.dedup_count,
            "last_triggered": stmt.excluded.last_triggered,
        },
    )
    await session.execute(stmt)
    if commit:
        await session.commit()
    return len(values)


async def update_connector_health(
    session: AsyncSession,
    name: str,
    status: str,
    latency_ms: int | None = None,
    records: int | None = None,
) -> None:
    row = {
        "name": name,
        "source": name.split("_")[0],
        "status": status,
        "last_poll_at": datetime.now(timezone.utc),
        "last_success_at": datetime.now(timezone.utc) if status == "healthy" else None,
        "latency_ms": latency_ms,
        "events_per_hour": records,
        "error_count": 0 if status == "healthy" else 1,
        "circuit_state": "closed" if status == "healthy" else "open",
    }
    stmt = pg_insert(ConnectorHealth).values(**row)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ConnectorHealth.name],
        set_={
            "status": stmt.excluded.status,
            "last_poll_at": stmt.excluded.last_poll_at,
            "last_success_at": stmt.excluded.last_success_at,
            "latency_ms": stmt.excluded.latency_ms,
            "events_per_hour": stmt.excluded.events_per_hour,
            "error_count": ConnectorHealth.error_count + stmt.excluded.error_count,
            "circuit_state": stmt.excluded.circuit_state,
        },
    )
    await session.execute(stmt)
    await session.commit()


async def upsert_compliance_snapshots(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = []
    for row in rows:
        values.append({
            "id": str(row.get("id") or uuid.uuid4()),
            "framework": row.get("framework", "popia"),
            "snapshot_date": row.get("snapshot_date") or datetime.now(timezone.utc).date(),
            "overall_score": float(row.get("overall_score", 0)),
            "details": row.get("details"),
            "total_controls": int(row.get("total_controls", 0)),
            "passed_controls": int(row.get("passed_controls", 0)),
        })
    stmt = pg_insert(ComplianceSnapshot).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ComplianceSnapshot.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_compliance_gaps(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = []
    for row in rows:
        values.append({
            "id": str(row.get("id") or uuid.uuid4()),
            "framework": row.get("framework", "popia"),
            "control_id": row.get("control_id", ""),
            "domain": row.get("domain"),
            "description": row.get("description", ""),
            "owner": row.get("owner"),
            "severity": row.get("severity"),
            "due_date": row.get("due_date"),
            "status": row.get("status", "open"),
            "evidence_count": int(row.get("evidence_count") or 0),
        })
    stmt = pg_insert(ComplianceGap).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ComplianceGap.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_waf_blocks(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "app_name": row.get("app_name", "unknown"),
        "attack_type": row.get("attack_type"),
        "request_uri": row.get("request_uri"),
        "action": row.get("action", "block"),
        "src_ip": row.get("src_ip"),
        "block_time": _as_datetime(row.get("block_time"), datetime.now(timezone.utc)),
    } for row in rows]
    stmt = pg_insert(WafBlock).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[WafBlock.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_api_endpoints(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "app_name": row.get("app_name", "unknown"),
        "endpoint": row.get("endpoint", ""),
        "method": row.get("method", "GET"),
        "is_shadow": bool(row.get("is_shadow", False)),
        "exposure_score": float(row.get("exposure_score", 0)),
        "discovered_at": _as_datetime(row.get("discovered_at"), datetime.now(timezone.utc)),
        "last_seen": _as_datetime(row.get("last_seen"), datetime.now(timezone.utc)),
    } for row in rows]
    stmt = pg_insert(ApiEndpoint).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ApiEndpoint.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_system_metrics(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "metric": row.get("metric", ""),
        "value": float(row.get("value", 0)),
        "unit": row.get("unit", "%"),
        "recorded_at": _as_datetime(row.get("recorded_at"), datetime.now(timezone.utc)),
    } for row in rows]
    stmt = pg_insert(SystemMetric).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[SystemMetric.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_agents(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "name": row.get("name", ""),
        "role": row.get("role", ""),
        "version": row.get("version", ""),
        "status": row.get("status", "online"),
        "host": row.get("host"),
        "last_seen": _as_datetime(row.get("last_seen"), datetime.now(timezone.utc)),
    } for row in rows]
    stmt = pg_insert(Agent).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[Agent.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_slo_metrics(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "metric": row.get("metric", "mttd"),
        "week_start": _as_date(row.get("week_start"), datetime.now(timezone.utc)),
        "value_hours": float(row.get("value_hours", 0)),
    } for row in rows]
    stmt = pg_insert(SloMetric).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[SloMetric.metric, SloMetric.week_start],
        set_={"value_hours": stmt.excluded.value_hours},
    )
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_database_inventory(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = [{
        "id": str(row.get("id") or uuid.uuid4()),
        "name": row.get("name", ""),
        "engine": row.get("engine"),
        "monitored": bool(row.get("monitored", True)),
        "agent_version": row.get("agent_version"),
        "last_heartbeat": _as_datetime(row.get("last_heartbeat"), datetime.now(timezone.utc)),
    } for row in rows]
    stmt = pg_insert(DatabaseInventory).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[DatabaseInventory.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)
