import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles, tenant_filter
from app.db import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.risk_score import RiskScore
from app.monitoring.access_audit import (
    record_access,
    request_context,
    scope_digest,
)

router = APIRouter(tags=["exports"])


async def _audit_export(session, request, claims, dataset: str, row_count: int) -> None:
    """Record a bulk data egress.

    CSV exports are the highest-volume way personal and security data leaves the
    platform, so each one is recorded with the dataset and the number of rows
    released. Without the row count a reviewer cannot tell a routine 12-row
    extract from a full-estate dump.
    """
    depts = list(getattr(claims, "department_ids", None) or [])
    branches = list(getattr(claims, "branch_ids", None) or [])
    provinces = list(getattr(claims, "province_ids", None) or [])
    roles = list(getattr(claims, "roles", None) or [])
    await record_access(
        session,
        action="export.csv",
        actor=getattr(claims, "email", None) or claims.sub,
        target=dataset,
        tenant_scope={
            "department_ids": depts,
            "branch_ids": branches,
            "province_ids": provinces,
        },
        actor_role=",".join(sorted(roles)) or None,
        scope_hash=scope_digest(depts, branches, provinces, roles),
        detail={"dataset": dataset, "row_count": row_count, **request_context(request)},
    )


def _csv_response(columns, rows, filename):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _val(value):
    if value is None:
        return ""
    return value.value if hasattr(value, "value") else value


@router.get("/exports/findings.csv")
async def export_findings(
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("findings")),
):
    q = select(Finding).order_by(Finding.last_seen.desc())
    scope = tenant_filter(claims, Finding)
    if scope is not None:
        q = q.where(scope)
    rows = (await session.execute(q)).scalars().all()
    await _audit_export(session, request, claims, "findings", len(rows))
    return _csv_response(
        ["id", "source", "external_id", "app_name", "severity", "title", "category", "status", "first_seen", "last_seen"],
        [
            [
                r.id, r.source, r.external_id, r.app_name, _val(r.severity), r.title,
                r.category, r.status, r.first_seen, r.last_seen,
            ]
            for r in rows
        ],
        "findings.csv",
    )


@router.get("/exports/risk-scores.csv")
async def export_risk_scores(
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("risks")),
):
    q = select(RiskScore).order_by(RiskScore.score_date.desc())
    scope = tenant_filter(claims, RiskScore)
    if scope is not None:
        q = q.where(scope)
    rows = (await session.execute(q)).scalars().all()
    await _audit_export(session, request, claims, "risk-scores", len(rows))
    return _csv_response(
        ["id", "app_name", "score_date", "fused_score", "signal_appscan", "signal_imperva", "signal_api_exposure", "signal_compliance_penalty", "bucket"],
        [
            [
                r.id, r.app_name, r.score_date, r.fused_score, r.signal_appscan, r.signal_imperva,
                r.signal_api_exposure, r.signal_compliance_penalty, _val(r.bucket),
            ]
            for r in rows
        ],
        "risk-scores.csv",
    )


@router.get("/exports/alerts.csv")
async def export_alerts(
    request: Request,
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("alerts_read")),
):
    q = select(Alert).order_by(Alert.last_triggered.desc())
    scope = tenant_filter(claims, Alert)
    if scope is not None:
        q = q.where(scope)
    rows = (await session.execute(q)).scalars().all()
    await _audit_export(session, request, claims, "alerts", len(rows))
    return _csv_response(
        ["id", "rule_id", "title", "severity", "source", "target_id", "status", "first_triggered", "last_triggered"],
        [
            [
                r.id, r.rule_id, r.title, _val(r.severity), r.source, r.target_id,
                _val(r.status), r.first_triggered, r.last_triggered,
            ]
            for r in rows
        ],
        "alerts.csv",
    )
