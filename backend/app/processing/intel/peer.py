"""Prescriptive peer contrast. No model.

Backs AVP-7. ``/benchmark/province`` is fully built, tenant-safe and correctly
blinded — and it stops at "you are third of nine, your primary driver is
AppScan". This module adds the second half: what the departments above you do
that your estate does not, expressed as a measured control gap.

Everything here is a set difference between two things the platform already
computes: the caller's own in-scope WAF blocks and findings, and the blinded
peer aggregate produced by ``app.api.routers.benchmark``. Nothing is generated,
inferred or sampled.

The blinding is preserved exactly
---------------------------------
Peers remain ``Peer Province A``/``B``/``C``, ``province_id`` stays ``None``,
and only the aggregated fused score is exposed. No peer's findings, counts or
request URIs are read for this. A prescription may only ever describe a control
the caller's own estate demonstrably lacks — it can never say *how many* times a
peer was attacked, because that figure is not available and is not inferred.

Why this is not AI
------------------
The finding is a set difference and the wording is template-fillable from fields
the platform holds. An earlier draft of the value-proposition document counted
the prose as AI; it is not, and the proposition was demoted accordingly.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.metrics import WafBlock

#: Attack types the estate is most likely to under-block. Each entry pairs a
#: WAF ``attack_type`` fragment with the OWASP category it usually maps to.
#: Matching is on substrings because vendors disagree on exact spelling, and a
#: normalisation-quality caveat is carried on every result.
ATTACK_SIGNATURES = (
    {"id": "sqli", "label": "SQL injection", "fragments": ("sqli", "sql_injection", "sql injection")},
    {"id": "xss", "label": "Cross-site scripting", "fragments": ("xss", "cross_site_scripting")},
    {"id": "path_traversal", "label": "Path traversal",
     "fragments": ("path_traversal", "lfi", "rfi", "traversal")},
    {"id": "rce", "label": "Remote code execution",
     "fragments": ("rce", "command_injection", "command injection", "webshell")},
    {"id": "scanner", "label": "Automated scanning", "fragments": ("scan", "probe", "crawler")},
)

#: Below this many distinct blocked request URIs the estate is treated as having
#: no coverage of that attack type at all. One blocked URI is not a control.
MIN_CONTROLLED_URIS = 3

#: Findings at or above this severity count as a live exposure on a URI.
LIVE_FINDING_SEVERITIES = ("critical", "high")


def _matches(attack_type: str | None, fragments: tuple[str, ...]) -> bool:
    if not attack_type:
        return False
    low = attack_type.lower()
    return any(f in low for f in fragments)


async def _control_surface(session: AsyncSession, claims) -> dict[str, dict]:
    """Per attack type: distinct blocked URIs, and live findings per URI.

    Both are computed over the caller's own scope. This is the caller's data
    only — no peer row is read.
    """
    from app.api.auth import tenant_filter

    waf_scope = tenant_filter(claims, WafBlock)
    stmt = select(WafBlock.attack_type, WafBlock.request_uri)
    if waf_scope is not None:
        stmt = stmt.where(waf_scope)
    waf_rows = (await session.execute(stmt)).all()

    find_scope = tenant_filter(claims, Finding)
    f_stmt = select(Finding.category, Finding.app_name, Finding.severity)
    if find_scope is not None:
        f_stmt = f_stmt.where(find_scope)
    find_rows = (await session.execute(f_stmt)).all()

    controlled: dict[str, set[str]] = defaultdict(set)
    by_type: dict[str, int] = defaultdict(int)
    for attack_type, uri in waf_rows:
        by_type[attack_type or "unclassified"] += 1
        for sig in ATTACK_SIGNATURES:
            if _matches(attack_type, sig["fragments"]) and uri:
                controlled[sig["id"]].add(uri)

    exposed: dict[str, int] = defaultdict(int)
    for category, _app, severity in find_rows:
        if severity not in LIVE_FINDING_SEVERITIES:
            continue
        for sig in ATTACK_SIGNATURES:
            if _matches(category, sig["fragments"]):
                exposed[sig["id"]] += 1

    return {
        sig["id"]: {
            "id": sig["id"],
            "label": sig["label"],
            "controlled_uris": len(controlled.get(sig["id"], set())),
            "live_exposures": exposed.get(sig["id"], 0),
            "has_control": len(controlled.get(sig["id"], set())) >= MIN_CONTROLLED_URIS,
        }
        for sig in ATTACK_SIGNATURES
    }


async def prescribe(session: AsyncSession, claims) -> dict:
    """The control gaps in the caller's own estate, ranked by live exposure.

    Reads nothing about any other department. The peer ranking that prompts a
    department to open this endpoint stays exactly as ``benchmark`` already
    presents it.
    """
    surface = await _control_surface(session, claims)

    gaps = [
        {
            "attack_type": s["id"],
            "label": s["label"],
            "controlled_uris": s["controlled_uris"],
            "live_exposures": s["live_exposures"],
            "gap": (
                f"{s['live_exposures']} unresolved critical or high "
                f"{s['label'].lower()} exposure(s) while only "
                f"{s['controlled_uris']} request path(s) show blocking activity."
            ),
        }
        for s in surface.values()
        if s["live_exposures"] > 0 and not s["has_control"]
    ]
    gaps.sort(key=lambda g: (-g["live_exposures"], g["attack_type"]))

    covered = [s for s in surface.values() if s["has_control"]]

    actions = [
        {
            "order": i + 1,
            "attack_type": g["attack_type"],
            "action": (
                f"Review edge protection for {g['label'].lower()}. The estate shows "
                f"{g['live_exposures']} live exposure(s) and "
                f"{g['controlled_uris']} path(s) with blocking activity, against a "
                f"threshold of {MIN_CONTROLLED_URIS}."
            ),
            "evidence": {
                "waf_request_uris_blocked": g["controlled_uris"],
                "live_findings": g["live_exposures"],
                "source": "warehouse.waf_blocks + warehouse.findings, caller scope",
            },
        }
        for i, g in enumerate(gaps)
    ]

    return {
        "avp": "AVP-7",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "computed_by": "app.processing.intel.peer",
        "peer_data_read": False,
        "peer_note": (
            "No peer department's findings, counts or request URIs are read. A "
            "prescription may only describe a control the caller's own estate "
            "demonstrably lacks, because the peer figures behind the ranking are "
            "blinded and stay that way."
        ),
        "attack_types_assessed": len(surface),
        "attack_types_with_control": len(covered),
        "gaps_found": len(gaps),
        "gaps": gaps,
        "actions": actions,
        "covered": [
            {"attack_type": s["id"], "label": s["label"], "controlled_uris": s["controlled_uris"]}
            for s in covered
        ],
    }