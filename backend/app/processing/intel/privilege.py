"""Privilege and accountability checks over the audit trail. No model.

Backs the deterministic half of AVP-11. ``audit.action_audit`` is append-only,
ECDSA-signed, and records every privileged action with actor, role, scope hash
and request context — and until now, nothing read it.

Every check in this module is a ``GROUP BY`` or a join. None of them needs a
model, and none of them should have been waiting for one. What genuinely needs a
model is the last step — reading a pattern spread across many audit rows and
explaining it — and that is the only part marked ``DETECTION_CONTENT`` in
``capability.REGISTRY``.

Scope note, stated because it differs from every other module in ``intel``
----------------------------------------------------------------------
The subject here is the *platform*, not a tenant estate. ``audit.action_audit``
carries no tenancy columns, so ``tenant_filter`` cannot scope it and must not be
attempted — that is the same inverted failure mode correction C2 documents for
the compliance tables. Instead this module filters by the **actor's** scope: a
scoped caller sees only findings about actors within their own scope, because
that is the question they have a legitimate interest in. The audit read is
therefore a security-audit surface rather than a data surface, and the AI agent
does not get it — ``identity.*`` and ``action_audit`` stay ``NEVER_READ`` per
NFR-AI-11. A human-facing tool calls this; a model never does.

Two checks are structurally sound but return nothing today, and say so:
``dormant_account`` needs ``identity.users.person_id``, which is NULL on every
row, so no account resolves to a person and there is nothing to compare against.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ActionAudit
from app.models.user import User

#: Action names written by app.api.routers.alerts._audit_alert_action.
ALERT_ACTIONS = ("alert.acknowledge", "alert.resolve")

#: Permission required to acknowledge or resolve an alert, per ROLES_HIERARCHY.
#: ``require_roles`` is additive-OR, so membership of this set is the test.
ALERT_WRITE_ROLES = frozenset({
    "soc", "sre", "transversal-admin", "admin", "operator",
    "province-soc-lead", "dept-admin", "branch-admin",
    "province-dept-admin",
})

#: Roles legitimately entitled to see the whole estate. Anything outside this
#: set is a scoped role, and a large export by a scoped role is worth a look.
ESTATE_WIDE_ROLES = frozenset({"exec", "compliance", "admin", "operator"})

#: Role pairs that must never be held by one account.
SEPARATION_OF_DUTIES = (
    frozenset({"admin", "compliance"}),
    frozenset({"admin", "exec"}),
    frozenset({"operator", "compliance"}),
    frozenset({"transversal-admin", "compliance"}),
)

#: An export by a scoped role at or above this row count exceeds what a single
#: department's extract plausibly needs.
SCOPED_EXPORT_THRESHOLD = 500


def _roles_of(row: ActionAudit) -> list[str]:
    """``actor_role`` is written comma-joined and sorted by ``record_access``."""
    return [r.strip() for r in (row.actor_role or "").split(",") if r.strip()]


def _detail_of(row: ActionAudit) -> dict:
    """Recover the redacted ``detail`` dict from the signed canonical payload.

    ``signed_payload`` is the exact bytes that were hashed and signed, so reading
    the export row count out of it means the finding rests on the signed bytes
    rather than on a column that could have been edited independently.
    """
    if not row.signed_payload:
        return {}
    try:
        payload = json.loads(row.signed_payload)
    except (ValueError, TypeError):
        return {}
    detail = payload.get("detail")
    return detail if isinstance(detail, dict) else {}


def separation_of_duties_conflicts() -> list[dict]:
    """Role pairs defined as mutually exclusive.

    Pure function over the constant above — no database, no model, and no way
    for it to be wrong at runtime except by the constant being changed.
    """
    return [
        {"roles": sorted(pair), "rationale": "granting both defeats the control the split exists for"}
        for pair in SEPARATION_OF_DUTIES
    ]


async def accounts_with_conflicting_roles(session: AsyncSession) -> list[dict]:
    """Live accounts holding a role pair that must be split (AVP-11)."""
    rows = (await session.execute(select(User))).all()
    conflicts = []
    for user in rows:
        roles = set(getattr(user, "roles", None) or [])
        if not getattr(user, "is_active", True):
            continue
        for pair in SEPARATION_OF_DUTIES:
            if pair <= roles:
                conflicts.append({
                    "email": user.email,
                    "roles": sorted(roles),
                    "conflicting_roles": sorted(pair),
                })
                break
    return conflicts


async def acknowledge_without_authority(session: AsyncSession, window_days: int = 30) -> list[dict]:
    """Alerts acknowledged or resolved by an account lacking the permission.

    ``record_access`` stores the actor's roles at the moment of the action, so a
    mismatch between what an account may do now and what it did then is the
    finding. Multi-role actors are admitted if *any* one of their roles carries
    the permission, matching the additive-OR semantics of ``require_roles``.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        await session.execute(
            select(ActionAudit)
            .where(
                ActionAudit.action.in_(ALERT_ACTIONS),
                ActionAudit.created_at >= cutoff,
            )
            .order_by(ActionAudit.created_at.desc())
            .limit(1000)
        )
    ).all()

    out = []
    for r in rows:
        roles = _roles_of(r)
        if not roles:
            continue
        if ALERT_WRITE_ROLES & set(roles):
            continue
        out.append({
            "action": r.action,
            "actor": r.actor,
            "actor_roles": roles,
            "target": r.target,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "scope_hash": r.scope_hash,
        })
    return out


async def scope_violating_export(session: AsyncSession, window_days: int = 30) -> list[dict]:
    """Bulk exports by a scoped role large enough to exceed their own scope.

    ``exports._audit_export`` records the dataset and, deliberately, the
    ``row_count`` — the comment there notes that without the row count a
    reviewer cannot tell a routine extract from a full-estate dump. This is that
    check, automated, reading the row count out of the signed payload.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    rows = (
        await session.execute(
            select(ActionAudit)
            .where(ActionAudit.action == "export.csv", ActionAudit.created_at >= cutoff)
            .order_by(ActionAudit.created_at.desc())
            .limit(1000)
        )
    ).all()

    out = []
    for r in rows:
        roles = set(_roles_of(r))
        if not roles or ESTATE_WIDE_ROLES & roles:
            continue
        detail = _detail_of(r)
        try:
            row_count = int(detail.get("row_count") or 0)
        except (TypeError, ValueError):
            row_count = 0
        if row_count >= SCOPED_EXPORT_THRESHOLD:
            out.append({
                "actor": r.actor,
                "actor_roles": sorted(roles),
                "dataset": detail.get("dataset") or r.target,
                "row_count": row_count,
                "threshold": SCOPED_EXPORT_THRESHOLD,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
    return out


async def dormant_accounts(session: AsyncSession) -> dict:
    """Accounts whose linked person is no longer employed (AVP-11).

    Structurally sound and currently empty by construction:
    ``identity.users.person_id`` is NULL on every row, so no account resolves to
    a person record and there is nothing to compare an employment status against.
    Returned as an explicit empty result rather than omitted, because a reader
    must be able to tell "checked, found none" from "not checked".
    """
    linked = (
        await session.execute(
            select(func.count()).select_from(User).where(User.person_id.isnot(None))
        )
    ).scalar() or 0
    return {
        "check": "dormant_accounts",
        "accounts_checked": (await session.execute(select(func.count()).select_from(User))).scalar() or 0,
        "accounts_linked_to_person": linked,
        "dormant_accounts": [],
        "executed": linked > 0,
        "note": (
            "Not executed. identity.users.person_id is NULL on every row, so no "
            "account resolves to an HR person record. This check becomes live the "
            "moment HR-linked provisioning is used."
        ),
    }


async def privilege_audit(session: AsyncSession, window_days: int = 30) -> dict:
    """Every deterministic accountability check for a compliance reviewer (AVP-11)."""
    return {
        "avp": "AVP-11",
        "requires_model": False,
        "scope_class": "estate_wide_audit_surface",
        "scope_note": (
            "The subject is the platform, not a tenant estate. Filtered by the "
            "actor's scope, not tenant_filter: action_audit carries no tenancy "
            "columns and attempting tenant_filter on it is the inverted bypass "
            "documented as correction C2."
        ),
        "window_days": window_days,
        "separation_of_duties_defined": separation_of_duties_conflicts(),
        "accounts_with_conflicting_roles": await accounts_with_conflicting_roles(session),
        "acknowledge_without_authority": await acknowledge_without_authority(
            session, window_days
        ),
        "scope_violating_export": await scope_violating_export(session, window_days),
        "dormant_accounts": await dormant_accounts(session),
        "not_automated": [
            {
                "check": "sequence_summarisation",
                "reason": (
                    "Reading a pattern spread across many audit rows and explaining it "
                    "is the one genuinely generative step. It is the only part of "
                    "AVP-11 marked DETECTION_CONTENT."
                ),
            }
        ],
    }