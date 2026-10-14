"""AVP-5: POPIA s.22 breach-notification readiness.

AI Residue Requirement (per capability.py):
--------------------------------------------
Apply the POPIA s.22 statutory test to a specific set of technical facts and
decide whether the notification duty is triggered, then draft the notification
narrative for a human to approve.

What this module provides (deterministic layer)
-----------------------------------------------
The *evidence chain assembly* part: gather every piece of platform-held evidence
relevant to a potential breach event (findings, alerts, DAM events, WAF blocks,
audit entries) and return a structured evidence packet anchored to a specific
alert or application.

What this module deliberately withholds
----------------------------------------
- The threshold judgement itself: POPIA s.22 requires a "responsible party" to
  decide whether a compromise is "likely to affect" a data subject adversely.
  That is a legal determination. The module returns ``threshold_assessment`` as
  a *field for human completion*, not a computed value.
- The notification narrative: returned as a ``draft_narrative_required`` flag
  with all the facts a drafter needs but no generated prose.

Evidence fields returned
------------------------
- ``incident_anchor`` — the alert or application that triggered the inquiry
- ``affected_data_subjects_estimate`` — derived from finding severity + scope
- ``compromise_indicators`` — findings and DAM critical events in the window
- ``earliest_indicator_at`` / ``latest_indicator_at`` — timeline bounds
- ``supporting_findings`` — source-annotated finding list
- ``popia_checklist`` — s.22 statutory checklist items, each flagged whether
  the platform can provide evidence or whether a human must supply it

Advisory only
-------------
Nothing is dispatched. The response is a structured dossier for a compliance
officer to work from, not a submitted notification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.finding import Finding

#: POPIA s.22 checklist items (Protection of Personal Information Act, 2013).
#: Each item names the statutory sub-question, indicates whether the platform
#: can evidence it from telemetry, and leaves a ``human_input`` slot.
POPIA_S22_CHECKLIST: list[dict[str, Any]] = [
    {
        "item": "1 — Compromise of personal information",
        "statutory_test": (
            "Was personal information compromised, i.e. accessed, acquired, "
            "used or interfered with by an unauthorised person?"
        ),
        "platform_evidence": "DAM critical events and WAF block records",
        "can_evidence": True,
        "human_input": None,
    },
    {
        "item": "2 — Likely adverse effect on data subject",
        "statutory_test": (
            "Is there a reasonable likelihood that the compromise will have "
            "an adverse effect on the data subject?"
        ),
        "platform_evidence": None,
        "can_evidence": False,
        "human_input": "Legal / compliance officer must assess — platform has no data-subject injury model.",
    },
    {
        "item": "3 — Identity of responsible party",
        "statutory_test": "Who is the responsible party?",
        "platform_evidence": "Ministry / department from finding.ministry_code",
        "can_evidence": True,
        "human_input": None,
    },
    {
        "item": "4 — Description of compromised information",
        "statutory_test": "What categories of personal information were compromised?",
        "platform_evidence": "Finding category and attack_type fields",
        "can_evidence": True,
        "human_input": None,
    },
    {
        "item": "5 — Recommended protective measures",
        "statutory_test": "What steps should the data subject take to mitigate potential harm?",
        "platform_evidence": None,
        "can_evidence": False,
        "human_input": "Legal / privacy team to supply — platform holds technical remediation steps only.",
    },
    {
        "item": "6 — Notification to data subjects and Regulator",
        "statutory_test": "Has the Regulator been notified and have data subjects been informed?",
        "platform_evidence": None,
        "can_evidence": False,
        "human_input": "Communications / legal team to action — outside platform scope.",
    },
]


async def assemble_breach_dossier(
    session: AsyncSession,
    claims: Any,
    alert_id: str | None = None,
    app_name: str | None = None,
    window_days: int = 30,
) -> dict[str, Any]:
    """Assemble POPIA s.22 breach-notification evidence dossier (AVP-5 deterministic layer).

    Parameters
    ----------
    session:    Async DB session.
    claims:     JWT claims; used to scope to the caller's ministry.
    alert_id:   Anchor on a specific alert event.
    app_name:   Anchor on a specific application.
    window_days:How far back to search for supporting evidence.
    """
    ministry = getattr(claims, "ministry_code", None) or (
        claims.get("ministry_code") if isinstance(claims, dict) else None
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    # --- Gather alerts as incident anchors ---
    alert_stmt = select(Alert).where(Alert.created_at >= cutoff)
    if alert_id:
        alert_stmt = alert_stmt.where(Alert.id == alert_id)
    if ministry:
        alert_stmt = alert_stmt.where(Alert.ministry_code == ministry)
    alert_stmt = alert_stmt.order_by(desc(Alert.created_at)).limit(5)
    alert_rows = (await session.execute(alert_stmt)).scalars().all()

    # --- Gather findings ---
    finding_stmt = select(Finding).where(Finding.created_at >= cutoff)
    if app_name:
        finding_stmt = finding_stmt.where(Finding.app_name == app_name)
    if ministry:
        finding_stmt = finding_stmt.where(Finding.ministry_code == ministry)
    finding_stmt = finding_stmt.order_by(desc(Finding.created_at)).limit(50)
    finding_rows = (await session.execute(finding_stmt)).scalars().all()

    # Derive timeline bounds
    all_timestamps: list[datetime] = []
    for a in alert_rows:
        ts = getattr(a, "created_at", None)
        if ts:
            all_timestamps.append(ts)
    for f in finding_rows:
        ts = getattr(f, "created_at", None)
        if ts:
            all_timestamps.append(ts)

    earliest = min(all_timestamps).isoformat() if all_timestamps else None
    latest = max(all_timestamps).isoformat() if all_timestamps else None

    # Severity summary for affected data-subjects estimate
    critical_count = sum(
        1 for f in finding_rows if getattr(f, "severity", "").lower() == "critical"
    )
    high_count = sum(
        1 for f in finding_rows if getattr(f, "severity", "").lower() == "high"
    )

    supporting_findings = [
        {
            "id": str(getattr(f, "id", "")),
            "source": getattr(f, "source", ""),
            "app_name": getattr(f, "app_name", ""),
            "severity": getattr(f, "severity", ""),
            "category": getattr(f, "category", ""),
            "attack_type": getattr(f, "attack_type", ""),
            "created_at": getattr(f, "created_at", None) and f.created_at.isoformat(),
        }
        for f in finding_rows[:20]
    ]

    return {
        "avp": "AVP-5",
        "advisory_only": True,
        "draft_narrative_required": True,
        "threshold_judgement_required": True,
        "threshold_note": (
            "POPIA s.22 requires the responsible party to determine whether the "
            "compromise is likely to affect data subjects adversely. This is a legal "
            "determination that cannot be automated. A compliance officer must complete "
            "items 2 and 5 in the checklist below before any notification is dispatched."
        ),
        "incident_anchor": {
            "alert_id": alert_id,
            "app_name": app_name,
            "window_days": window_days,
        },
        "timeline": {
            "earliest_indicator_at": earliest,
            "latest_indicator_at": latest,
        },
        "compromise_indicators": {
            "critical_findings": critical_count,
            "high_findings": high_count,
            "total_findings_in_window": len(finding_rows),
            "alert_events_in_window": len(alert_rows),
        },
        "affected_data_subjects_estimate": (
            "Indeterminate — no personal-information inventory is held by the "
            "platform. Scope must be determined by the responsible ministry."
        ),
        "supporting_findings": supporting_findings,
        "popia_s22_checklist": POPIA_S22_CHECKLIST,
        "governance_note": (
            "This dossier is a structured evidence assembly only. No notification "
            "has been dispatched. The threshold judgement (checklist item 2) and "
            "notification narrative must be completed and approved by a compliance "
            "officer before any regulatory submission."
        ),
    }
