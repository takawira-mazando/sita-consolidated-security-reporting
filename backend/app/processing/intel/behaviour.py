"""AVP-11: Privilege and accountability audit — behavioural sequence explanation.

AI Residue Requirement (per capability.py):
--------------------------------------------
Read a behavioural sequence spread across many signed audit rows and explain it:
recognise that a pattern exists which no single rule would flag.

What this module provides (deterministic layer)
-----------------------------------------------
The ``privilege.py`` module already detects per-row violations:
- Separation-of-duties conflicts
- Acknowledge-without-authority
- Scope-violating exports

This module adds the *sequence analysis* layer: given a window of signed audit
events for a single user or entity, it:
1. Groups them into temporal clusters (events within a configurable burst window).
2. Scores each cluster for multi-step privilege escalation patterns.
3. Returns a ``SequenceReport`` with the clusters, their pattern labels, and a
   prose narration stub (structured, not generated) that names what happened in
   order.

Pattern labels (deterministic, no model required)
--------------------------------------------------
- ``SELF_APPROVE_CHAIN`` — acknowledges own findings in sequence
- ``ESCALATING_EXPORT`` — exports increasing volumes across successive actions
- ``CROSS_SCOPE_PIVOT`` — actions on resources outside caller's scope in order
- ``RAPID_AUTHORITY_SWEEP`` — many different privileged operations in a short burst
- ``DORMANT_THEN_ACTIVE`` — long gap then sudden burst (requires dormant_account data)

Advisory only
-------------
The report is returned as a structured dossier. Nothing is dispatched or
committed. The ``pattern_confidence`` field indicates how many corroborating
signals were found — it is not a probability estimate from a model.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import ActionAudit

# Burst window: events within this many minutes are grouped into one cluster
BURST_WINDOW_MINUTES = 15

# Escalating-export threshold: export row counts must increase by this factor
EXPORT_ESCALATION_FACTOR = 2.0

# Minimum cluster size before pattern-labelling is meaningful
MIN_CLUSTER_SIZE = 2

_PRIVILEGED_ACTIONS = frozenset(
    {
        "acknowledge",
        "export",
        "delete",
        "suppress",
        "admin_create",
        "role_assign",
        "bulk_close",
        "override_severity",
    }
)


@dataclass
class AuditCluster:
    """A temporal burst of audit events from the same actor."""

    actor_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    pattern_labels: list[str] = field(default_factory=list)
    pattern_confidence: int = 0  # count of corroborating signals, not a probability


@dataclass
class SequenceReport:
    """Output of ``explain_behaviour``."""

    avp: str = "AVP-11"
    advisory_only: bool = True
    window_days: int = 30
    actors_analysed: int = 0
    clusters: list[AuditCluster] = field(default_factory=list)
    anomalous_clusters: list[AuditCluster] = field(default_factory=list)
    narration_stub: str = ""
    analyst_review_required: bool = True
    governance_note: str = (
        "Sequence analysis surfaces patterns across audit rows that no single "
        "rule would flag. Each anomalous cluster must be reviewed by an "
        "authorised analyst before any disciplinary or regulatory action is taken."
    )


def _cluster_events(
    events: list[dict[str, Any]],
    window_minutes: int = BURST_WINDOW_MINUTES,
) -> list[list[dict[str, Any]]]:
    """Group events into temporal bursts."""
    if not events:
        return []
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [events[0]]
    for ev in events[1:]:
        prev_ts = current[-1].get("timestamp")
        curr_ts = ev.get("timestamp")
        if prev_ts and curr_ts:
            try:
                delta = abs((curr_ts - prev_ts).total_seconds())
                if delta <= window_minutes * 60:
                    current.append(ev)
                    continue
            except Exception:
                pass
        clusters.append(current)
        current = [ev]
    clusters.append(current)
    return clusters


def _label_cluster(events: list[dict[str, Any]]) -> tuple[list[str], int]:
    """Return pattern labels and a confidence count for a cluster."""
    labels: list[str] = []
    confidence = 0

    actions = [str(e.get("action", "")).lower() for e in events]
    resources = [str(e.get("resource_id", "")) for e in events]
    scopes = [str(e.get("scope", "")) for e in events]
    row_counts = [e.get("row_count", 0) for e in events if e.get("row_count")]
    actor_ids = {str(e.get("actor_id", "")) for e in events}
    resource_actors = {str(e.get("resource_owner_id", "")) for e in events}

    # SELF_APPROVE_CHAIN — acknowledges resources owned by same actor
    if "acknowledge" in actions or "bulk_close" in actions:
        if actor_ids & resource_actors:
            labels.append("SELF_APPROVE_CHAIN")
            confidence += 2

    # ESCALATING_EXPORT
    if row_counts and len(row_counts) >= 2:
        escalating = all(
            row_counts[i + 1] >= row_counts[i] * EXPORT_ESCALATION_FACTOR
            for i in range(len(row_counts) - 1)
        )
        if escalating:
            labels.append("ESCALATING_EXPORT")
            confidence += 3

    # CROSS_SCOPE_PIVOT — multiple different scopes in one cluster
    unique_scopes = {s for s in scopes if s}
    if len(unique_scopes) > 1:
        labels.append("CROSS_SCOPE_PIVOT")
        confidence += 1

    # RAPID_AUTHORITY_SWEEP — variety of privileged actions
    privileged_in_cluster = {a for a in actions if a in _PRIVILEGED_ACTIONS}
    if len(privileged_in_cluster) >= 3:
        labels.append("RAPID_AUTHORITY_SWEEP")
        confidence += len(privileged_in_cluster)

    return labels, confidence


async def explain_behaviour(
    session: AsyncSession,
    window_days: int = 30,
    actor_id: str | None = None,
    min_confidence: int = 2,
) -> SequenceReport:
    """Explain behavioural sequences in the signed audit trail (AVP-11 residue layer).

    Parameters
    ----------
    session:        Async DB session.
    window_days:    How far back to read audit events.
    actor_id:       Optionally scope to a single actor.
    min_confidence: Minimum corroborating-signal count to include a cluster in
                    ``anomalous_clusters``.
    """
    report = SequenceReport(window_days=window_days)

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    stmt = (
        select(ActionAudit)
        .where(ActionAudit.created_at >= cutoff)
        .order_by(ActionAudit.actor, ActionAudit.created_at)
    )
    if actor_id:
        stmt = stmt.where(ActionAudit.actor == actor_id)
    rows = (await session.execute(stmt)).scalars().all()

    # Group by actor
    by_actor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        # Derive a scope string from tenant_scope JSON if present
        tenant_scope = getattr(row, "tenant_scope", None) or {}
        scope_str = str(tenant_scope.get("ministry_code", "")) if isinstance(tenant_scope, dict) else ""
        ev = {
            "id": str(getattr(row, "id", "")),
            "actor_id": str(getattr(row, "actor", "")),
            "action": getattr(row, "action", ""),
            "resource_id": str(getattr(row, "target", "")),
            "resource_owner_id": "",  # not held in current schema
            "scope": scope_str,
            "row_count": getattr(row, "attestation_size_bytes", 0) or 0,
            "timestamp": getattr(row, "created_at", None),
        }
        by_actor[ev["actor_id"]].append(ev)

    report.actors_analysed = len(by_actor)
    all_clusters: list[AuditCluster] = []
    anomalous: list[AuditCluster] = []

    for aid, events in by_actor.items():
        bursts = _cluster_events(events)
        for burst in bursts:
            if len(burst) < MIN_CLUSTER_SIZE:
                continue
            labels, confidence = _label_cluster(burst)
            cluster = AuditCluster(
                actor_id=aid,
                events=burst,
                pattern_labels=labels,
                pattern_confidence=confidence,
            )
            all_clusters.append(cluster)
            if labels and confidence >= min_confidence:
                anomalous.append(cluster)

    report.clusters = all_clusters
    report.anomalous_clusters = anomalous

    if anomalous:
        summaries: list[str] = []
        for c in anomalous[:5]:
            label_str = ", ".join(c.pattern_labels) if c.pattern_labels else "UNLABELLED"
            event_count = len(c.events)
            earliest = (
                min(e["timestamp"] for e in c.events if e["timestamp"])
                if any(e["timestamp"] for e in c.events)
                else None
            )
            ts_str = earliest.strftime("%Y-%m-%dT%H:%M:%SZ") if earliest else "unknown time"
            summaries.append(
                f"Actor '{c.actor_id}': {label_str} ({event_count} events, from {ts_str})"
            )
        report.narration_stub = (
            f"{len(anomalous)} anomalous cluster(s) detected across "
            f"{report.actors_analysed} actor(s) in the past {window_days} days. "
            "Each cluster spans multiple audit events; no single rule would flag "
            "the pattern in isolation. Analyst review required before action.\n\n"
            + "\n".join(f"  • {s}" for s in summaries)
        )
    else:
        report.narration_stub = (
            f"No anomalous multi-step patterns detected across "
            f"{report.actors_analysed} actor(s) in the past {window_days} days."
        )

    return report
