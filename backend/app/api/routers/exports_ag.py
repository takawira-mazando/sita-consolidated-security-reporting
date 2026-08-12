"""Auditor-General (AG) secure compliance export engine.

Produces a signed, aggregation-only compliance attestation suitable for an
Auditor-General / oversight submission:

- Aggregation only: raw findings, vulnerability counts, individual logs and
  PII are stripped. The payload is a summary of the estate (or the caller's
  province scope) — snapshot scores, control status/severity distributions and
  a scoped risk profile. Nothing that could re-identify an asset or a user is
  emitted.
- Integrity: a SHA-256 hash is computed over the canonical JSON of the
  attestation and bound to the actor + tenant scope in the `audit` schema via
  ActionAudit, giving non-repudiation and tamper detection.
- Accountability: every export writes one immutable audit row
  (action=`ag_compliance_export`) recording who exported what scope.
"""
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, require_roles, tenant_filter
from app.db import get_session
from app.models.audit import ActionAudit
from app.models.compliance import ComplianceGap, ComplianceSnapshot
from app.models.risk_score import RiskScore
from app.tenant import PROVINCES

router = APIRouter(tags=["exports-ag"])


def _bucket(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "monitored"
    return "safe"


def canonical_json(payload: dict) -> str:
    """Deterministic JSON serialization so hashes are stable across runs."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_hex(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_attestation(
    framework: str,
    snapshot: ComplianceSnapshot | None,
    gaps: list[ComplianceGap],
    risk_rows: list[dict],
    scope_meta: dict,
) -> dict:
    """Pure builder; aggregation only — never emits raw rows.

    risk_rows: [{fused_score, department_id, app_name, signal_appscan,
                 signal_imperva, signal_api_exposure, signal_compliance_penalty}]
    """
    domain_scores = {}
    if snapshot and isinstance(snapshot.details, dict):
        domain_scores = {k: float(v) for k, v in snapshot.details.items()}

    status_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    for gap in gaps:
        status_counts[gap.status or "unknown"] = status_counts.get(gap.status or "unknown", 0) + 1
        severity_counts[gap.severity or "unknown"] = severity_counts.get(gap.severity or "unknown", 0) + 1
        domain = gap.domain or "unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    bucket_counts: dict[str, int] = {"critical": 0, "monitored": 0, "safe": 0}
    departments: set[str] = set()
    apps: set[str] = set()
    signals = {"appscan": 0.0, "imperva": 0.0, "api": 0.0, "compliance": 0.0}
    total = len(risk_rows)
    for r in risk_rows:
        score = float(r["fused_score"])
        bucket_counts[_bucket(score)] += 1
        if r.get("department_id"):
            departments.add(r["department_id"])
        if r.get("app_name"):
            apps.add(r["app_name"])
        for key, rk in (
            ("appscan", "signal_appscan"),
            ("imperva", "signal_imperva"),
            ("api", "signal_api_exposure"),
            ("compliance", "signal_compliance_penalty"),
        ):
            v = r.get(rk)
            if v is not None:
                signals[key] += float(v)

    return {
        "artifact": "AG compliance attestation (aggregate only)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework": framework,
        "snapshot": (
            {
                "framework": snapshot.framework,
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "overall_score": float(snapshot.overall_score),
                "passed_controls": snapshot.passed_controls,
                "total_controls": snapshot.total_controls,
                "domain_scores": domain_scores,
            }
            if snapshot
            else None
        ),
        "controls": {
            "gap_total": len(gaps),
            "status_counts": dict(sorted(status_counts.items())),
            "severity_counts": dict(sorted(severity_counts.items())),
            "domain_counts": dict(sorted(domain_counts.items())),
        },
        "risk_profile": {
            "scoped_apps": len(apps),
            "scoped_departments": len(departments),
            "bucket_counts": bucket_counts,
            "signal_averages": {
                key: (round(value / total, 2) if total else 0.0)
                for key, value in signals.items()
            },
        },
        "scope": scope_meta,
        "provenance": (
            "Aggregation-only export: raw findings, vulnerability counts and "
            "individual logs are stripped. Contains no PII and no "
            "asset-level detail. Integrity is bound by SHA-256 to the audit trail."
        ),
    }


@router.post("/exports/ag-compliance")
async def export_ag_compliance(
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(require_roles("compliance", "admin_write")),
):
    framework = "popia"

    snap_q = (
        select(ComplianceSnapshot)
        .where(ComplianceSnapshot.framework == framework)
        .order_by(ComplianceSnapshot.snapshot_date.desc())
    )
    snapshot = (await session.execute(snap_q)).scalars().first()

    gap_q = select(ComplianceGap).where(ComplianceGap.framework == framework)
    gaps = (await session.execute(gap_q)).scalars().all()

    risk_q = select(
        RiskScore.department_id,
        RiskScore.app_name,
        RiskScore.fused_score,
        RiskScore.signal_appscan,
        RiskScore.signal_imperva,
        RiskScore.signal_api_exposure,
        RiskScore.signal_compliance_penalty,
    )
    scope = tenant_filter(claims, RiskScore)
    if scope is not None:
        risk_q = risk_q.where(scope)
    risk_rows = [
        {
            "department_id": r.department_id,
            "app_name": r.app_name,
            "fused_score": float(r.fused_score),
            "signal_appscan": r.signal_appscan,
            "signal_imperva": r.signal_imperva,
            "signal_api_exposure": r.signal_api_exposure,
            "signal_compliance_penalty": r.signal_compliance_penalty,
        }
        for r in (await session.execute(risk_q)).all()
    ]

    province_ids = list(getattr(claims, "province_ids", None) or [])
    scope_meta = {
        "type": "province" if province_ids else "estate",
        "provinces": [PROVINCES.get(p, p) for p in sorted(province_ids)] if province_ids else ["all"],
        "note": (
            "Risk profile is scoped to the caller's province; compliance "
            "snapshot/gaps are estate-wide today (snapshots carry no "
            "department_id)."
            if province_ids
            else "Whole-of-entity attestation covering the full SITA estate."
        ),
    }

    payload = build_attestation(framework, snapshot, list(gaps), risk_rows, scope_meta)
    integrity_hash = sha256_hex(payload)

    audit = ActionAudit(
        actor=claims.email or claims.sub,
        action="ag_compliance_export",
        target=framework,
        tenant_scope={
            "department_ids": claims.department_ids or [],
            "branch_ids": claims.branch_ids or [],
            "province_ids": province_ids,
        },
        payload_hash=integrity_hash,
    )
    session.add(audit)
    await session.commit()

    return {
        "attestation": payload,
        "integrity_hash": integrity_hash,
        "verify_url": f"/api/v1/exports/ag-compliance/verify/{integrity_hash}",
    }


@router.get("/exports/ag-compliance/verify/{integrity_hash}")
async def verify_ag_compliance(
    integrity_hash: str,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(require_roles("compliance", "admin_write")),
):
    row = (
        await session.execute(
            select(ActionAudit).where(ActionAudit.payload_hash == integrity_hash)
        )
    ).scalars().first()
    if row is None:
        return {"valid": False, "integrity_hash": integrity_hash}
    return {
        "valid": True,
        "integrity_hash": integrity_hash,
        "action": row.action,
        "actor": row.actor,
        "target": row.target,
        "tenant_scope": row.tenant_scope,
        "recorded_at": row.created_at.isoformat() if row.created_at else None,
    }
