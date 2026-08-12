import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus, DispatchLog
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
from app.tenant import (
    branch_for_app,
    branch_for_db,
    cluster_for_app,
    cluster_for_db,
    department_for_app,
    department_for_db,
    ministry_for_app,
    ministry_for_db,
)


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
    app_name = str(_first(record, "app_name", "application_name", "database_name", "endpoint") or "unknown")
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "external_id": str(_first(record, "external_id", "event_id", "id", "control_id") or uuid.uuid4()),
        "app_name": app_name,
        "department_id": department_for_app(app_name) or department_for_db(app_name),
        "branch_id": branch_for_app(app_name) or branch_for_db(app_name),
        "ministry_id": ministry_for_app(app_name) or ministry_for_db(app_name),
        "cluster_id": cluster_for_app(app_name) or cluster_for_db(app_name),
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
            "app_name": stmt.excluded.app_name,
            "department_id": stmt.excluded.department_id,
            "branch_id": stmt.excluded.branch_id,
            "ministry_id": stmt.excluded.ministry_id,
            "cluster_id": stmt.excluded.cluster_id,
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
            "app_name": stmt.excluded.app_name,
            "department_id": stmt.excluded.department_id,
            "branch_id": stmt.excluded.branch_id,
            "ministry_id": stmt.excluded.ministry_id,
            "cluster_id": stmt.excluded.cluster_id,
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


def _chunked(seq: list, size: int = 500):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


async def upsert_risk_scores(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    values = []
    for row in rows:
        bucket_raw = str(row.get("bucket") or "monitored").lower()
        if bucket_raw not in {b.value for b in RiskBucket}:
            bucket_raw = "monitored"
        app_name = row.get("app_name", "unknown")
        values.append({
            "id": str(uuid.uuid4()),
            "app_name": app_name,
            "department_id": department_for_app(app_name) or department_for_db(app_name),
            "branch_id": branch_for_app(app_name) or branch_for_db(app_name),
            "ministry_id": ministry_for_app(app_name) or ministry_for_db(app_name),
            "cluster_id": cluster_for_app(app_name) or cluster_for_db(app_name),
            "score_date": row.get("score_date") or datetime.now(timezone.utc).date(),
            "fused_score": float(row.get("fused_score", 0.0)),
            "signal_appscan": row.get("signal_appscan"),
            "signal_imperva": row.get("signal_imperva"),
            "signal_api_exposure": row.get("signal_api_exposure"),
            "signal_compliance_penalty": row.get("signal_compliance_penalty"),
            "bucket": bucket_raw,
        })
    for chunk in _chunked(values):
        stmt = pg_insert(RiskScore).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[RiskScore.app_name, RiskScore.score_date],
            set_={
                "department_id": stmt.excluded.department_id,
                "branch_id": stmt.excluded.branch_id,
                "ministry_id": stmt.excluded.ministry_id,
                "cluster_id": stmt.excluded.cluster_id,
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
        target_id = alert.get("target_id")
        values.append({
            "id": str(alert.get("id") or uuid.uuid4()),
            "rule_id": str(alert.get("rule_id") or "unknown"),
            "title": str(alert.get("title") or "Alert"),
            "description": alert.get("description"),
            "severity": severity_raw,
            "source": alert.get("source"),
            "target_id": target_id,
            "department_id": department_for_app(target_id) or department_for_db(target_id),
            "branch_id": branch_for_app(target_id) or branch_for_db(target_id),
            "ministry_id": ministry_for_app(target_id) or ministry_for_db(target_id),
            "cluster_id": cluster_for_app(target_id) or cluster_for_db(target_id),
            "status": status_raw,
            "enriched_data": alert.get("enriched_data"),
            "channels": alert.get("channels") if alert.get("channels") else None,
            "dedup_key": alert.get("dedup_key"),
            "dedup_count": int(alert.get("dedup_count") or 1),
            "first_triggered": triggered,
            "last_triggered": _as_datetime(alert.get("last_triggered"), triggered),
            "last_dispatched_at": _as_datetime(alert.get("last_dispatched_at")) if alert.get("last_dispatched_at") else None,
        })
    stmt = pg_insert(Alert).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Alert.id],
        set_={
            "status": stmt.excluded.status,
            "severity": stmt.excluded.severity,
            "enriched_data": stmt.excluded.enriched_data,
            "channels": stmt.excluded.channels,
            "dedup_count": stmt.excluded.dedup_count,
            "last_triggered": stmt.excluded.last_triggered,
            "last_dispatched_at": stmt.excluded.last_dispatched_at,
        },
    )
    await session.execute(stmt)
    if commit:
        await session.commit()
    return len(values)


async def record_dispatch(
    session: AsyncSession,
    alert_id: str,
    results: list[dict],
    commit: bool = True,
) -> int:
    """Persist per-channel delivery outcomes for an alert (dispatch audit trail)."""
    if not results:
        return 0
    now = datetime.now(timezone.utc)
    from sqlalchemy import select
    alert = (
        await session.execute(select(Alert).where(Alert.id == alert_id))
    ).scalar_one_or_none()
    department_id = alert.department_id if alert is not None else department_for_app(alert_id)
    branch_id = alert.branch_id if alert is not None else branch_for_app(alert_id)
    ministry_id = alert.ministry_id if alert is not None else ministry_for_app(alert_id)
    cluster_id = alert.cluster_id if alert is not None else cluster_for_app(alert_id)
    values = []
    for result in results:
        values.append({
            "id": str(uuid.uuid4()),
            "alert_id": str(alert_id or ""),
            "channel": str(result.get("channel") or "unknown"),
            "department_id": department_id,
            "branch_id": branch_id,
            "ministry_id": ministry_id,
            "cluster_id": cluster_id,
            "status": str(result.get("status") or "failed"),
            "error": result.get("error"),
            "attempted_at": _as_datetime(result.get("attempted_at"), now),
        })
    stmt = pg_insert(DispatchLog).values(values)
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
        "department_id": department_for_app(row.get("app_name")),
        "branch_id": branch_for_app(row.get("app_name")),
        "ministry_id": ministry_for_app(row.get("app_name")),
        "cluster_id": cluster_for_app(row.get("app_name")),
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
        "department_id": department_for_app(row.get("app_name")),
        "branch_id": branch_for_app(row.get("app_name")),
        "ministry_id": ministry_for_app(row.get("app_name")),
        "cluster_id": cluster_for_app(row.get("app_name")),
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
        "department_id": department_for_db(row.get("name")),
        "branch_id": branch_for_db(row.get("name")),
        "ministry_id": ministry_for_db(row.get("name")),
        "cluster_id": cluster_for_db(row.get("name")),
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
