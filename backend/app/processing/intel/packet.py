"""Dispute-ready evidence packets. No model.

Backs AVP-12. The platform already signs, hashes and verifies offline for the
Auditor-General attestation. This applies those same primitives to a different
selection of rows, producing an artefact that answers a specific audit question
rather than one fixed snapshot.

Reuses rather than reimplements
-------------------------------
``canonical_json``, ``sha256_hex``, ``sign_canonical_payload``, ``get_key_id``
and ``key_fingerprint`` all come from the existing modules. A packet is
therefore verifiable by exactly the same ``openssl`` procedure already published
at ``/api/v1/exports/ag-compliance/public-key`` — no new verification story, no
second key, no second policy version.

Determinism
-----------
``generated_at`` is excluded from the signed body, as it is for the attestation.
Two packets over the same facts are byte-identical, so a reviewer can re-derive
one and compare rather than trust it.

A stated limit
--------------
``warehouse.findings`` is upserted on ``(source, external_id)`` with
``version = Finding.version + 1`` on conflict (``lake/writer.py:107-126``), so
``status`` is overwritten in place. **A packet can show what the platform asserts
now, and when each finding first and last appeared. It cannot prove what a
finding's status was on a past date.** Every packet carries that limitation in
its own body rather than in documentation, because an auditor reads the artefact
and not the docs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.audit import ActionAudit
from app.models.finding import Finding
from app.security_pki import get_key_id, sign_canonical_payload

#: Bumped when the packet body shape changes, so old packets remain interpretable.
PACKET_POLICY_VERSION = "evidence-packet-v1"

#: The limitation travels inside the signed body.
HISTORY_LIMITATION = (
    "warehouse.findings is upserted on (source, external_id); status is "
    "overwritten in place and no per-state history is retained. This packet "
    "establishes current state and first/last observation dates. It cannot "
    "establish what a finding's status was on a past date."
)


def canonical_json(payload: dict) -> str:
    """Sorted, tight-separator JSON. Mirrors exports_ag.canonical_json exactly."""
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(payload: dict) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


async def _alert_chain(session: AsyncSession, claims, alert_id: str) -> dict:
    """The audit rows for one alert's lifecycle, plus the alert itself."""
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Alert)
    stmt = select(Alert).where(Alert.id == alert_id)
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()
    if not rows:
        return {"found": False, "reason": "alert not found in caller scope"}
    alert = rows[0]

    audit = (
        await session.execute(
            select(ActionAudit)
            .where(ActionAudit.target == alert_id)
            .order_by(ActionAudit.created_at)
        )
    ).all()

    return {
        "found": True,
        "alert": {
            "id": alert.id,
            "rule_id": alert.rule_id,
            "title": alert.title,
            "severity": alert.severity,
            "status": alert.status,
            "target_id": alert.target_id,
            "first_triggered": _iso(alert.first_triggered),
            "last_triggered": _iso(alert.last_triggered),
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": _iso(alert.acknowledged_at),
            "resolved_at": _iso(alert.resolved_at),
        },
        "lifecycle": [
            {
                "action": r.action,
                "actor": r.actor,
                "actor_role": r.actor_role,
                "created_at": _iso(r.created_at),
                "payload_hash": r.payload_hash,
                "signature_present": bool(r.signature),
                "key_id": r.key_id,
            }
            for r in audit
        ],
    }


async def _related_findings(session: AsyncSession, claims, app_name: str, limit: int = 50) -> list[dict]:
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Finding)
    stmt = (
        select(Finding)
        .where(Finding.app_name == app_name)
        .order_by(Finding.last_seen.desc())
        .limit(limit)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": f.id,
            "source": f.source,
            "external_id": f.external_id,
            "severity": f.severity,
            "title": f.title,
            "owasp_id": f.owasp_id,
            "cwe_id": f.cwe_id,
            "owasp_status": f.owasp_status,
            "taxonomy_version": f.taxonomy_version,
            "status": f.status,
            "version": f.version,
            "first_seen": _iso(f.first_seen),
            "last_seen": _iso(f.last_seen),
        }
        for f in rows
    ]


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _scope_of(claims) -> dict:
    return {
        "department_ids": sorted(getattr(claims, "department_ids", None) or []),
        "branch_ids": sorted(getattr(claims, "branch_ids", None) or []),
        "province_ids": sorted(getattr(claims, "province_ids", None) or []),
        "roles": sorted(getattr(claims, "roles", None) or []),
    }


async def build(
    session: AsyncSession,
    claims,
    alert_id: str | None = None,
    app_name: str | None = None,
) -> dict:
    """Assemble and sign one evidence packet.

    Requires at least one anchor. With neither, the packet would be the AG
    attestation again, which already exists at ``/api/v1/exports/ag-compliance``.
    """
    if not alert_id and not app_name:
        return {
            "error": "an_anchor_required",
            "message": (
                "Supply alert_id or app_name. A packet with neither anchor is the "
                "AG attestation, which already exists at "
                "/api/v1/exports/ag-compliance."
            ),
        }

    scope = _scope_of(claims)
    body: dict = {
        "policy_version": PACKET_POLICY_VERSION,
        "anchor": {"alert_id": alert_id, "app_name": app_name},
        "scope": scope,
        "limitation": HISTORY_LIMITATION,
    }
    if alert_id:
        body["alert_chain"] = await _alert_chain(session, claims, alert_id)
        if app_name is None and body["alert_chain"].get("found"):
            app_name = body["alert_chain"]["alert"].get("target_id")
    if app_name:
        body["findings"] = await _related_findings(session, claims, app_name)

    canonical = canonical_json(body)
    signature = None
    signing_note = None
    try:
        signature = sign_canonical_payload(canonical.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - degrade, never fail the request
        signing_note = f"unsigned: {exc}"

    return {
        "packet_id": str(uuid.uuid4()),
        "policy_version": PACKET_POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "limitation": HISTORY_LIMITATION,
        "body": body,
        "payload_hash": _digest(body),
        "signature": signature,
        "key_id": get_key_id() if signature else None,
        "signed": bool(signature),
        "signing_note": signing_note,
        "verify_with": (
            "Same procedure as /api/v1/exports/ag-compliance/public-key: fetch the "
            "PEM public key, then verify sha256 of the canonical body against "
            "signature."
        ),
        "requires_model": False,
        "note": (
            "generated_at is excluded from the signed body, so two packets over the "
            "same facts are byte-identical and a reviewer can re-derive one."
        ),
    }