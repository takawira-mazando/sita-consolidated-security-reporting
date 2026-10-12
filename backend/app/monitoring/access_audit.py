"""Append-only audit of access to personal and security data.

Closes gap G-10 in ``docs/B5_ICASA_ECT_Gap_Analysis.md``: before this module
the only writer to ``audit.action_audit`` was the Auditor-General export engine,
so the platform could not answer the first question any Information Regulator
inspection or internal audit asks:

    who accessed what personal data, in which tenancy scope, and when

Every read of person or employee records, every authentication event, every
tenancy switch, every bulk export and every dispatch now appends a signed row to
the same trail. Reusing ``audit.action_audit`` rather than adding a parallel
table is deliberate: the four-layer database immutability guarantee in
``infrastructure/scripts/init-db.sql`` (append-only trigger, TRUNCATE guard,
fail-loud INSERT guard, REVOKE) already applies, and
``backend/tests/test_audit_immutability.py`` already proves it.

Design constraints:

- **Never lose the record.** A signing failure degrades the row to unsigned
  rather than dropping it. Losing a read-access record is the exact failure mode
  this control exists to prevent.
- **Never raise into the request path.** An audit defect must not deny a
  legitimate security operation. Failures are logged at ERROR.
- **Never record a secret.** ``detail`` is passed through a redaction filter so
  a future caller cannot accidentally sign a password or token into permanent
  storage.
"""
import hashlib
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ActionAudit
from app.security_pki import SIGNING_ALGORITHM, get_key_id, sign_canonical_payload

logger = logging.getLogger(__name__)

# Bumped when the shape or scope of recorded access events changes, so an
# auditor can tell which control state produced a given access record.
ACCESS_POLICY_VERSION = "access-audit-v1"

#: Detail keys whose values are replaced with a redaction marker before the
#: payload is signed and persisted. Matching is case-insensitive and substring
#: based so ``user_password`` and ``X-Auth-Token`` are both caught.
REDACTED_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "private_key",
    "routing_key",
    "credential",
)

REDACTION_MARKER = "[redacted]"


def canonical_json(payload: Any) -> str:
    """Deterministic serialization so the recorded hash is stable."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def scope_digest(
    department_ids: list[str] | None,
    branch_ids: list[str] | None,
    province_ids: list[str] | None,
    roles: list[str] | None,
    policy_version: str = ACCESS_POLICY_VERSION,
) -> str:
    """Stable digest of the authorisation scope in force for an access event."""
    return hashlib.sha256(
        canonical_json(
            {
                "department_ids": sorted(department_ids or []),
                "branch_ids": sorted(branch_ids or []),
                "province_ids": sorted(province_ids or []),
                "roles": sorted(roles or []),
                "policy_version": policy_version,
            }
        ).encode("utf-8")
    ).hexdigest()


def redact(detail: Any) -> Any:
    """Recursively replace secret-looking values before anything is persisted.

    Applied to every access record. An allowlist would be stronger but would
    break silently when a new field is added; a denylist fails loudly in
    review, which is the safer trade-off for an audit control.
    """
    if isinstance(detail, dict):
        out: dict[str, Any] = {}
        for key, value in detail.items():
            lowered = str(key).lower()
            if any(part in lowered for part in REDACTED_KEY_PARTS):
                out[key] = REDACTION_MARKER
            else:
                out[key] = redact(value)
        return out
    if isinstance(detail, list):
        return [redact(item) for item in detail]
    return detail


async def record_access(
    session: AsyncSession,
    *,
    action: str,
    actor: str,
    target: str | None = None,
    tenant_scope: dict | None = None,
    actor_role: str | None = None,
    scope_hash: str | None = None,
    detail: dict | None = None,
    commit: bool = True,
) -> None:
    """Append one signed access record. Never raises.

    ``action`` uses a dotted namespace so records are filterable without a
    schema change, e.g. ``auth.login``, ``auth.login_failed``,
    ``auth.switch_tenant``, ``data.read.persons``, ``export.csv``, ``alert.dispatch``.
    """
    safe_detail = redact(detail or {})
    payload = {
        "action": action,
        "actor": actor,
        "target": target,
        "tenant_scope": tenant_scope or {},
        "detail": safe_detail,
    }
    try:
        canonical = canonical_json(payload)
        canonical_bytes = canonical.encode("utf-8")
        payload_hash = hashlib.sha256(canonical_bytes).hexdigest()

        row = ActionAudit(
            actor=actor,
            action=action,
            target=target,
            tenant_scope=tenant_scope or {},
            payload_hash=payload_hash,
            signed_payload=canonical,
            actor_role=actor_role,
            policy_version=ACCESS_POLICY_VERSION,
            scope_hash=scope_hash,
            verification_status="unverified",
        )

        try:
            row.signature = sign_canonical_payload(canonical_bytes)
            row.key_id = get_key_id()
            row.signing_algorithm = SIGNING_ALGORITHM
        except Exception:  # noqa: BLE001 - degrade, never drop the record
            logger.exception(
                "Access audit signing failed for action=%s actor=%s; "
                "recording unsigned row",
                action,
                actor,
            )
            row.verification_status = "unsigned"

        session.add(row)
        if commit:
            await session.commit()
    except Exception:  # noqa: BLE001 - an audit defect must not deny the operation
        logger.exception(
            "Failed to record access event action=%s actor=%s", action, actor
        )
        if commit:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                logger.exception("Rollback after failed access audit also failed")


def request_context(request: Any) -> dict:
    """Client attribution for an access record.

    Records the originating address and user agent. Both are personal
    information under POPIA and are therefore themselves auditable — which is
    why they travel inside a signed record rather than a free-text log line.
    """
    context: dict[str, Any] = {}
    if request is None:
        return context
    client = getattr(request, "client", None)
    if client is not None and getattr(client, "host", None):
        context["src_ip"] = client.host
    forwarded = None
    headers = getattr(request, "headers", None)
    if headers is not None:
        forwarded = headers.get("x-forwarded-for")
        user_agent = headers.get("user-agent")
        if user_agent:
            context["user_agent"] = user_agent
    if forwarded:
        context["src_ip_forwarded"] = forwarded.split(",")[0].strip()
    return context