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
- Accountability: every export writes one append-only audit row
  (action=`ag_compliance_export`) recording who exported what scope, under which
  role and policy version.
- Reproducibility: the signed body contains no wall-clock value. Two exports over
  identical data produce byte-identical signed bytes and therefore an identical
  `integrity_hash`. The generation timestamp travels in the transport envelope so
  a verifier can still tell when an attestation was produced without the
  signature covering a non-deterministic field.
- Verifiability: the signed bytes and the signature are persisted alongside the
  hash, so `/verify/{hash}` performs a real ECDSA check against the published
  public key instead of treating the presence of an audit row as proof.
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
from app.security_pki import (
    SIGNING_ALGORITHM,
    get_ec_public_key,
    get_ec_public_key_pem,
    get_key_id,
    sign_canonical_payload,
    verify_canonical_payload,
)
from app.tenant import PROVINCES

router = APIRouter(tags=["exports-ag"])

# Bumped when the authorisation or aggregation logic changes, so an auditor can
# tell which control state produced an attestation.
POLICY_VERSION = "ag-export-v2"


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


def _build_attestation_body(
    framework: str,
    snapshot: ComplianceSnapshot | None,
    gaps: list[ComplianceGap],
    risk_rows: list[dict],
    scope_meta: dict,
) -> dict:
    """Pure builder; aggregation only — never emits raw rows.

    Deliberately free of wall-clock values so the output is reproducible.

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


def build_attestation(
    framework: str,
    snapshot: ComplianceSnapshot | None,
    gaps: list[ComplianceGap],
    risk_rows: list[dict],
    scope_meta: dict,
) -> dict:
    """Public builder retained for callers and tests.

    The returned mapping is the signed body. ``generated_at`` is deliberately not
    part of it so that the signature is reproducible over identical inputs.
    """
    return _build_attestation_body(framework, snapshot, gaps, risk_rows, scope_meta)


def scope_digest(claims: JWTClaims, province_ids: list[str]) -> str:
    """Stable digest of the authorisation scope resolved for this export."""
    return sha256_hex(
        {
            "department_ids": sorted(claims.department_ids or []),
            "branch_ids": sorted(claims.branch_ids or []),
            "province_ids": sorted(province_ids or []),
            "roles": sorted(getattr(claims, "roles", None) or []),
            "policy_version": POLICY_VERSION,
        }
    )


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
    canon_bytes = canonical_json(payload).encode("utf-8")
    integrity_hash = hashlib.sha256(canon_bytes).hexdigest()
    digital_signature = sign_canonical_payload(canon_bytes)
    key_id = get_key_id()

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
        signed_payload=canon_bytes.decode("utf-8"),
        signature=digital_signature,
        key_id=key_id,
        signing_algorithm=SIGNING_ALGORITHM,
        actor_role=",".join(sorted(getattr(claims, "roles", None) or [])) or None,
        policy_version=POLICY_VERSION,
        scope_hash=scope_digest(claims, province_ids),
        verification_status="unverified",
        attestation_size_bytes=len(canon_bytes),
    )
    session.add(audit)
    await session.commit()

    return {
        "attestation": payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "integrity_hash": integrity_hash,
        "signature": digital_signature,
        "signing_algorithm": SIGNING_ALGORITHM,
        "key_id": key_id,
        "policy_version": POLICY_VERSION,
        "scope_hash": scope_digest(claims, province_ids),
        "public_key_url": "/api/v1/exports/ag-compliance/public-key",
        "verify_url": f"/api/v1/exports/ag-compliance/verify/{integrity_hash}",
        "reproducibility_note": (
            "generated_at is excluded from the signed bytes, so identical data "
            "yields an identical integrity_hash and signature."
        ),
    }


@router.get("/exports/ag-compliance/public-key")
async def get_ag_compliance_public_key():
    """Public key for offline Auditor-General cryptographic verification."""
    return {
        "algorithm": SIGNING_ALGORITHM,
        "curve": "secp256r1 (NIST P-256)",
        "key_format": "X.509 SubjectPublicKeyInfo (PEM)",
        "key_id": get_key_id(),
        "public_key_pem": get_ec_public_key_pem(),
        "offline_verification_instructions": {
            "openssl": "openssl dgst -sha256 -verify ag_public_key.pem -signature attestation.sig canonical_attestation.json",
            "python": "from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.primitives import hashes, serialization; pub = serialization.load_pem_public_key(open('ag_public_key.pem','rb').read()); pub.verify(base64.b64decode(sig_b64), data, ec.ECDSA(hashes.SHA256()))",
        },
    }


def _verify_record(row: ActionAudit, public_key) -> dict:
    """Cryptographically verify a stored attestation record.

    Three independent checks, all required:

    1. the stored signed bytes are present and parseable;
    2. re-hashing them reproduces the recorded ``payload_hash`` (the hash is not
       a free-floating label);
    3. the ECDSA signature validates over exactly those bytes.

    Any failure yields ``valid: False`` with a reason. A missing signature is a
    failure, not a pass — otherwise a forged audit row would verify.
    """
    # Stored as a stable machine-readable code. Human-readable detail is returned
    # in the response; only the bounded code is persisted.
    result = {
        "valid": False,
        "reason_code": "unverified",
        "integrity_hash": row.payload_hash,
        "action": row.action,
        "actor": row.actor,
        "target": row.target,
        "tenant_scope": row.tenant_scope,
        "actor_role": row.actor_role,
        "policy_version": row.policy_version,
        "scope_hash": row.scope_hash,
        "key_id": row.key_id,
        "signing_algorithm": row.signing_algorithm or SIGNING_ALGORITHM,
        "recorded_at": row.created_at.isoformat() if row.created_at else None,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "public_key_url": "/api/v1/exports/ag-compliance/public-key",
    }

    if not row.signed_payload or not row.signature:
        result["reason_code"] = "no_signature"
        result["reason"] = (
            "no_signature: this record carries no signed payload, so it cannot be "
            "verified. Attestations issued before signed evidence was persisted are "
            "not cryptographically verifiable."
        )
        return result

    canon_bytes = row.signed_payload.encode("utf-8")

    recomputed = hashlib.sha256(canon_bytes).hexdigest()
    if recomputed != row.payload_hash:
        result["reason_code"] = "hash_mismatch"
        result["reason"] = "hash_mismatch: signed payload does not reproduce the recorded hash"
        result["recomputed_hash"] = recomputed
        return result

    if not verify_canonical_payload(canon_bytes, row.signature, public_key):
        result["reason_code"] = "signature_invalid"
        result["reason"] = "signature_invalid: signature does not validate over the recorded payload"
        return result

    result["valid"] = True
    result["reason_code"] = "signature_valid"
    result["reason"] = "signature_valid"
    return result


@router.get("/exports/ag-compliance/verify/{integrity_hash}")
async def verify_ag_compliance(
    integrity_hash: str,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(require_roles("compliance", "admin_write")),
):
    """Verify an attestation against its stored signed evidence.

    Verification is cryptographic, not a database-existence check: an audit row is
    not proof that the bytes it names were ever signed. The response distinguishes
    ``no_record`` (nothing was issued under this hash) from ``invalid`` (something
    was issued but the evidence does not hold).
    """
    rows = (
        await session.execute(
            select(ActionAudit).where(ActionAudit.payload_hash == integrity_hash)
        )
    ).scalars().all()
    if not rows:
        return {
            "valid": False,
            "reason_code": "no_record",
            "integrity_hash": integrity_hash,
            "reason": "no_record: no attestation was issued under this hash",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        public_key = get_ec_public_key()
    except Exception as exc:  # noqa: BLE001 - reported, never silently passed
        return {
            "valid": False,
            "reason_code": "public_key_unavailable",
            "integrity_hash": integrity_hash,
            "reason": f"public_key_unavailable: {exc}",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    # More than one row can carry the same hash: repeating an export of unchanged
    # data legitimately re-issues the same attestation, and an attacker with
    # insert rights can append a forged row under that hash. Verification is
    # therefore all-or-nothing across every row: one bad record fails the whole
    # hash rather than being skipped by an arbitrary first-match.
    results = [_verify_record(row, public_key) for row in rows]

    for row, outcome in zip(rows, results):
        if row.verification_status != outcome["reason_code"] or row.verified_at is None:
            row.verification_status = outcome["reason_code"]
            row.verified_at = datetime.now(timezone.utc)
            row.verified_by = claims.email or claims.sub
            session.add(row)
    if session.new or session.dirty:
        await session.commit()

    failed = [r for r in results if not r["valid"]]
    result = dict(results[0])
    result["records_checked"] = len(results)

    if failed:
        result["valid"] = False
        result["reason_code"] = failed[0]["reason_code"]
        result["reason"] = failed[0]["reason"]
        result["failed_records"] = len(failed)
        if len(results) > 1:
            result["reason"] += (
                f" ({len(failed)} of {len(results)} records carrying this hash "
                "failed cryptographic verification)"
            )
        return result

    if len(results) > 1:
        result["reason"] = f"signature_valid ({len(results)} records agree)"
    return result
