from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceSnapshot
from app.models.finding import Finding, Severity
from app.processing.risk_engine import (
    RiskInputs,
    compute_signal_appscan,
    compute_signal_compliance,
    compute_signal_exposure,
    compute_signal_imperva,
    fused_risk,
    risk_bucket,
)


async def compute_risk_for_app(session: AsyncSession, app_name: str) -> dict | None:
    rows = (
        await session.execute(
            select(
                Finding.severity,
                Finding.source,
                Finding.raw_data,
            ).where(Finding.app_name == app_name)
        )
    ).all()

    appscan_counts: dict[str, int] = {}
    imperva_count = 0
    exposure_scores: list[float] = []

    for severity, source, raw in rows:
        sev = severity.value if isinstance(severity, Severity) else str(severity)
        if source == "appscan":
            appscan_counts[sev] = appscan_counts.get(sev, 0) + 1
        elif source in ("imperva_dam", "imperva_waf"):
            imperva_count += 1
        elif source == "apisec":
            if isinstance(raw, dict):
                score = raw.get("exposure_score")
                try:
                    exposure_scores.append(float(score))
                except (TypeError, ValueError):
                    pass

    compliance_pct = 0.0
    snap = (
        await session.execute(
            select(ComplianceSnapshot.overall_score)
            .where(ComplianceSnapshot.framework == "popia")
            .order_by(ComplianceSnapshot.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if snap is not None:
        compliance_pct = float(snap)

    inputs = RiskInputs(
        appscan_severity_counts=appscan_counts,
        imperva_violation_count=imperva_count,
        api_exposure_scores=exposure_scores,
        compliance_pct=compliance_pct,
    )
    score = fused_risk(inputs)
    bucket = risk_bucket(score)

    return {
        "app_name": app_name,
        "score_date": date.today(),
        "fused_score": score,
        "signal_appscan": round(compute_signal_appscan(appscan_counts), 1),
        "signal_imperva": round(compute_signal_imperva(imperva_count), 1),
        "signal_api_exposure": round(compute_signal_exposure(exposure_scores), 1),
        "signal_compliance_penalty": round(compute_signal_compliance(compliance_pct), 1),
        "bucket": bucket,
    }


async def compute_all_risk_scores(session: AsyncSession) -> list[dict]:
    apps = (
        await session.execute(select(Finding.app_name).distinct())
    ).scalars().all()
    results = []
    for app in apps:
        row = await compute_risk_for_app(session, app)
        if row is not None:
            results.append(row)
    return results
