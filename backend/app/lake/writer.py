import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_workspace import ClientTenantWorkspace
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
from app.processing import owasp


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


def _as_text(value):
    """Coerce a value destined for a VARCHAR column to a string.

    Vendor feeds are inconsistent: AppScan returns a bare numeric CWE id, some
    WAF feeds return ints for rule identifiers. Writing one of those into a
    VARCHAR column fails at the driver with ``expected str, got int``, which
    aborted the whole ingest batch rather than the single offending field.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if value is pd.NaT or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _tenant_data_scope(record: dict) -> dict:
    workspace_id = _as_text(record.get("tenant_workspace_id"))
    level_key = _as_text(record.get("tenant_scope_level_key"))
    if bool(workspace_id) != bool(level_key):
        raise ValueError(
            "Tenant-scoped records must include both tenant_workspace_id and "
            "tenant_scope_level_key"
        )
    if level_key and (
        not level_key.replace("-", "").replace("_", "").isalnum()
        or level_key.lower() != level_key
    ):
        raise ValueError("tenant_scope_level_key must be a lowercase hierarchy key")
    return {
        "tenant_workspace_id": workspace_id,
        "tenant_scope_level_key": level_key,
    }


def _tenant_record_id(record: dict, category: str) -> str:
    record_id = _as_text(record.get("id"))
    scope = _tenant_data_scope(record)
    workspace_id = scope["tenant_workspace_id"]
    if not record_id:
        return str(uuid.uuid4())
    if workspace_id:
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"unified-data-security:{workspace_id}:{scope['tenant_scope_level_key']}:{category}:{record_id}",
            )
        )
    return record_id


async def _validate_tenant_data_scopes(
    session: AsyncSession,
    records: list[dict],
) -> None:
    scopes = {
        (
            _tenant_data_scope(record)["tenant_workspace_id"],
            _tenant_data_scope(record)["tenant_scope_level_key"],
        )
        for record in records
    }
    scoped = {(workspace_id, level_key) for workspace_id, level_key in scopes if workspace_id}
    if not scoped:
        return

    workspace_ids = {workspace_id for workspace_id, _ in scoped}
    result = await session.execute(
        select(ClientTenantWorkspace).where(
            ClientTenantWorkspace.id.in_(workspace_ids),
            ClientTenantWorkspace.status == "active",
        )
    )
    workspaces = {workspace.id: workspace for workspace in result.scalars().all()}
    for workspace_id, level_key in scoped:
        workspace = workspaces.get(workspace_id)
        allowed_levels = {
            "root",
            *(level.get("key") for level in (workspace.hierarchy_levels or [])),
        } if workspace else set()
        if workspace is None or level_key not in allowed_levels:
            raise ValueError(
                "Tenant-scoped records must reference an active workspace and "
                "one of its configured hierarchy tiers"
            )


def _json_safe(value):
    """Coerce a value into something ``json.dumps`` (and therefore JSONB) accepts.

    The normalised batch reaches this layer as a pandas DataFrame, so values
    arrive as ``pd.Timestamp``, ``numpy.int64`` and ``NaT``/``NaN`` rather than
    native Python types. Persisting the raw record then failed with
    ``TypeError: Object of type Timestamp is not JSON serializable``.

    NaN/NaT become ``None`` rather than being left to ``json.dumps``, which
    would emit bare ``NaN`` tokens that are not valid JSON and are rejected by
    the JSONB type. This was previously invisible because every source date
    failed to parse and arrived as ``None``.
    """
    if value is None:
        return None
    # NaT is a singleton whose bool() is False, so check it before anything else.
    if value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # numpy scalars expose .item(); bool must be handled first because
    # numpy.bool_ is not an int subclass in recent numpy.
    if isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "item") and callable(value.item):
        return _json_safe(value.item())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


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
    # Classification is derived here rather than read from the record, so a
    # caller that bypasses the Normaliser still cannot write an OWASP id the
    # registry does not recognise -- `classify` only ever returns an id that
    # exists in the registry, and any value it cannot place is reported as
    # unmapped rather than guessed. Mirrors the severity check above.
    category = _first(record, "category", "domain", "attack_type")
    classification = owasp.classify(category, source)
    return {
        "id": str(uuid.uuid4()),
        "source": source,
        "external_id": str(_first(record, "external_id", "event_id", "id", "control_id") or uuid.uuid4()),
        "app_name": app_name,
        "department_id": _as_text(record.get("department_id")),
        "branch_id": _as_text(record.get("branch_id")),
        **_tenant_data_scope(record),
        "ministry_id": _as_text(record.get("ministry_id")),
        "cluster_id": _as_text(record.get("cluster_id")),
        "severity": severity_raw,
        "title": str(_first(record, "title", "vulnerability_name", "rule_name", "attack_name", "name", "description") or "Finding"),
        "description": _first(record, "description", "details", "summary"),
        "category": _as_text(category),
        "owasp_id": classification.owasp_id,
        "cwe_id": classification.cwe_id,
        "owasp_status": classification.status,
        "taxonomy_version": classification.taxonomy_version,
        "raw_data": _json_safe(record),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "status": status_raw,
        "version": 1,
    }


def _finding_upsert_statement(values: list[dict], tenant_scoped: bool):
    statement = pg_insert(Finding).values(values)
    if tenant_scoped:
        conflict_columns = [
            Finding.tenant_workspace_id,
            Finding.tenant_scope_level_key,
            Finding.source,
            Finding.external_id,
        ]
        conflict_where = Finding.tenant_workspace_id.is_not(None)
    else:
        conflict_columns = [Finding.source, Finding.external_id]
        conflict_where = Finding.tenant_workspace_id.is_(None)
    return statement.on_conflict_do_update(
        index_elements=conflict_columns,
        index_where=conflict_where,
        set_={
            "app_name": statement.excluded.app_name,
            "department_id": statement.excluded.department_id,
            "branch_id": statement.excluded.branch_id,
            "tenant_workspace_id": statement.excluded.tenant_workspace_id,
            "tenant_scope_level_key": statement.excluded.tenant_scope_level_key,
            "ministry_id": statement.excluded.ministry_id,
            "cluster_id": statement.excluded.cluster_id,
            "severity": statement.excluded.severity,
            "title": statement.excluded.title,
            "description": statement.excluded.description,
            "category": statement.excluded.category,
            "owasp_id": statement.excluded.owasp_id,
            "cwe_id": statement.excluded.cwe_id,
            "owasp_status": statement.excluded.owasp_status,
            "taxonomy_version": statement.excluded.taxonomy_version,
            "raw_data": statement.excluded.raw_data,
            "last_seen": statement.excluded.last_seen,
            "status": statement.excluded.status,
            "version": Finding.version + 1,
        },
    )


async def _upsert_finding_values(session: AsyncSession, values: list[dict]) -> None:
    for tenant_scoped in (False, True):
        group = [
            value
            for value in values
            if bool(value["tenant_workspace_id"]) is tenant_scoped
        ]
        if group:
            await session.execute(_finding_upsert_statement(group, tenant_scoped))


async def upsert_findings(session: AsyncSession, records: list[dict], source: str = "") -> int:
    if not records:
        return 0
    await _validate_tenant_data_scopes(session, records)
    values = [record_to_finding(record, source) for record in records]
    await _upsert_finding_values(session, values)
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
    await _validate_tenant_data_scopes(session, records)
    findings = [record_to_finding(record, source) for record in records]
    await _upsert_finding_values(session, findings)
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
    await _validate_tenant_data_scopes(session, rows)
    values = []
    for row in rows:
        bucket_raw = str(row.get("bucket") or "monitored").lower()
        if bucket_raw not in {b.value for b in RiskBucket}:
            bucket_raw = "monitored"
        app_name = row.get("app_name", "unknown")
        values.append({
            "id": str(uuid.uuid4()),
            "app_name": app_name,
            "department_id": _as_text(row.get("department_id")),
            "branch_id": _as_text(row.get("branch_id")),
            **_tenant_data_scope(row),
            "ministry_id": _as_text(row.get("ministry_id")),
            "cluster_id": _as_text(row.get("cluster_id")),
            "score_date": row.get("score_date") or datetime.now(timezone.utc).date(),
            "fused_score": float(row.get("fused_score", 0.0)),
            "signal_appscan": row.get("signal_appscan"),
            "signal_imperva": row.get("signal_imperva"),
            "signal_api_exposure": row.get("signal_api_exposure"),
            "signal_compliance_penalty": row.get("signal_compliance_penalty"),
            "bucket": bucket_raw,
        })
    for chunk in _chunked(values):
        for tenant_scoped in (False, True):
            group = [
                value
                for value in chunk
                if bool(value["tenant_workspace_id"]) == tenant_scoped
            ]
            if not group:
                continue
            statement = pg_insert(RiskScore).values(group)
            if tenant_scoped:
                conflict_columns = [
                    RiskScore.tenant_workspace_id,
                    RiskScore.tenant_scope_level_key,
                    RiskScore.app_name,
                    RiskScore.score_date,
                ]
                conflict_where = RiskScore.tenant_workspace_id.is_not(None)
            else:
                conflict_columns = [RiskScore.app_name, RiskScore.score_date]
                conflict_where = RiskScore.tenant_workspace_id.is_(None)
            statement = statement.on_conflict_do_update(
                index_elements=conflict_columns,
                index_where=conflict_where,
                set_={
                    "department_id": statement.excluded.department_id,
                    "branch_id": statement.excluded.branch_id,
                    "tenant_workspace_id": statement.excluded.tenant_workspace_id,
                    "tenant_scope_level_key": statement.excluded.tenant_scope_level_key,
                    "ministry_id": statement.excluded.ministry_id,
                    "cluster_id": statement.excluded.cluster_id,
                    "fused_score": statement.excluded.fused_score,
                    "signal_appscan": statement.excluded.signal_appscan,
                    "signal_imperva": statement.excluded.signal_imperva,
                    "signal_api_exposure": statement.excluded.signal_api_exposure,
                    "signal_compliance_penalty": statement.excluded.signal_compliance_penalty,
                    "bucket": statement.excluded.bucket,
                },
            )
            await session.execute(statement)
    await session.commit()
    return len(values)


async def upsert_alerts(session: AsyncSession, alerts: list[dict], commit: bool = True) -> int:
    if not alerts:
        return 0
    await _validate_tenant_data_scopes(session, alerts)
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
            "id": _tenant_record_id(alert, "alert"),
            "rule_id": str(alert.get("rule_id") or "unknown"),
            "title": str(alert.get("title") or "Alert"),
            "description": alert.get("description"),
            "severity": severity_raw,
            "source": alert.get("source"),
            "target_id": target_id,
            "department_id": _as_text(alert.get("department_id")),
            "branch_id": _as_text(alert.get("branch_id")),
            **_tenant_data_scope(alert),
            "ministry_id": _as_text(alert.get("ministry_id")),
            "cluster_id": _as_text(alert.get("cluster_id")),
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
            "tenant_workspace_id": stmt.excluded.tenant_workspace_id,
            "tenant_scope_level_key": stmt.excluded.tenant_scope_level_key,
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
    department_id = alert.department_id if alert is not None else None
    branch_id = alert.branch_id if alert is not None else None
    ministry_id = alert.ministry_id if alert is not None else None
    cluster_id = alert.cluster_id if alert is not None else None
    values = []
    for result in results:
        values.append({
            "id": str(uuid.uuid4()),
            "alert_id": str(alert_id or ""),
            "channel": str(result.get("channel") or "unknown"),
            "department_id": department_id,
            "branch_id": branch_id,
            "tenant_workspace_id": alert.tenant_workspace_id if alert is not None else None,
            "tenant_scope_level_key": alert.tenant_scope_level_key if alert is not None else None,
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
    await _validate_tenant_data_scopes(session, rows)
    values = []
    for row in rows:
        values.append({
            "id": _tenant_record_id(row, "compliance-snapshot"),
            "framework": row.get("framework", "popia"),
            "snapshot_date": row.get("snapshot_date") or datetime.now(timezone.utc).date(),
            "overall_score": float(row.get("overall_score", 0)),
            "details": row.get("details"),
            "total_controls": int(row.get("total_controls", 0)),
            "passed_controls": int(row.get("passed_controls", 0)),
            **_tenant_data_scope(row),
        })
    stmt = pg_insert(ComplianceSnapshot).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ComplianceSnapshot.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_compliance_gaps(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    await _validate_tenant_data_scopes(session, rows)
    values = []
    for row in rows:
        values.append({
            "id": _tenant_record_id(row, "compliance-gap"),
            "framework": row.get("framework", "popia"),
            "control_id": row.get("control_id", ""),
            "domain": row.get("domain"),
            "description": row.get("description", ""),
            "owner": row.get("owner"),
            "severity": row.get("severity"),
            "due_date": row.get("due_date"),
            "status": row.get("status", "open"),
            "evidence_count": int(row.get("evidence_count") or 0),
            **_tenant_data_scope(row),
        })
    stmt = pg_insert(ComplianceGap).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[ComplianceGap.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_waf_blocks(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    await _validate_tenant_data_scopes(session, rows)
    values = [{
        "id": _tenant_record_id(row, "waf-block"),
        "app_name": row.get("app_name", "unknown"),
        "department_id": _as_text(row.get("department_id")),
        "branch_id": _as_text(row.get("branch_id")),
        **_tenant_data_scope(row),
        "ministry_id": _as_text(row.get("ministry_id")),
        "cluster_id": _as_text(row.get("cluster_id")),
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
    await _validate_tenant_data_scopes(session, rows)
    values = [{
        "id": _tenant_record_id(row, "api-endpoint"),
        "app_name": row.get("app_name", "unknown"),
        "department_id": _as_text(row.get("department_id")),
        "branch_id": _as_text(row.get("branch_id")),
        **_tenant_data_scope(row),
        "ministry_id": _as_text(row.get("ministry_id")),
        "cluster_id": _as_text(row.get("cluster_id")),
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
    await _validate_tenant_data_scopes(session, rows)
    values = [{
        "id": _tenant_record_id(row, "agent"),
        "name": row.get("name", ""),
        "role": row.get("role", ""),
        "version": row.get("version", ""),
        "status": row.get("status", "online"),
        "host": row.get("host"),
        "last_seen": _as_datetime(row.get("last_seen"), datetime.now(timezone.utc)),
        **_tenant_data_scope(row),
    } for row in rows]
    stmt = pg_insert(Agent).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[Agent.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)


async def upsert_slo_metrics(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    await _validate_tenant_data_scopes(session, rows)
    values = [{
        "id": _tenant_record_id(row, "slo-metric"),
        "metric": row.get("metric", "mttd"),
        "week_start": _as_date(row.get("week_start"), datetime.now(timezone.utc)),
        "value_hours": float(row.get("value_hours", 0)),
        **_tenant_data_scope(row),
    } for row in rows]
    for tenant_scoped in (False, True):
        group = [
            value
            for value in values
            if bool(value["tenant_workspace_id"]) == tenant_scoped
        ]
        if not group:
            continue
        statement = pg_insert(SloMetric).values(group)
        if tenant_scoped:
            conflict_columns = [
                SloMetric.tenant_workspace_id,
                SloMetric.tenant_scope_level_key,
                SloMetric.metric,
                SloMetric.week_start,
            ]
            conflict_where = SloMetric.tenant_workspace_id.is_not(None)
        else:
            conflict_columns = [SloMetric.metric, SloMetric.week_start]
            conflict_where = SloMetric.tenant_workspace_id.is_(None)
        statement = statement.on_conflict_do_update(
            index_elements=conflict_columns,
            index_where=conflict_where,
            set_={"value_hours": statement.excluded.value_hours},
        )
        await session.execute(statement)
    await session.commit()
    return len(values)


async def upsert_database_inventory(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    await _validate_tenant_data_scopes(session, rows)
    values = [{
        "id": _tenant_record_id(row, "database-inventory"),
        "name": row.get("name", ""),
        "department_id": _as_text(row.get("department_id")),
        "branch_id": _as_text(row.get("branch_id")),
        "ministry_id": _as_text(row.get("ministry_id")),
        "cluster_id": _as_text(row.get("cluster_id")),
        "engine": row.get("engine"),
        "monitored": bool(row.get("monitored", True)),
        "agent_version": row.get("agent_version"),
        "last_heartbeat": _as_datetime(row.get("last_heartbeat"), datetime.now(timezone.utc)),
        **_tenant_data_scope(row),
    } for row in rows]
    stmt = pg_insert(DatabaseInventory).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=[DatabaseInventory.id])
    await session.execute(stmt)
    await session.commit()
    return len(values)
