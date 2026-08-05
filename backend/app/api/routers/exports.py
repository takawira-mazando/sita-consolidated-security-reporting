import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_roles
from app.db import get_session
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.risk_score import RiskScore

router = APIRouter(tags=["exports"])


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
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("findings")),
):
    rows = (await session.execute(select(Finding).order_by(Finding.last_seen.desc()))).scalars().all()
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
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("risks")),
):
    rows = (await session.execute(select(RiskScore).order_by(RiskScore.score_date.desc()))).scalars().all()
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
    session: AsyncSession = Depends(get_session),
    claims=Depends(require_roles("alerts_read")),
):
    rows = (await session.execute(select(Alert).order_by(Alert.last_triggered.desc()))).scalars().all()
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
