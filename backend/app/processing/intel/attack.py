"""ATT&CK coverage and hunt proposals. No model.

Backs the deterministic half of AVP-2 and all of AVP-9.

The mapping is curated data in ``attack_mapping.yaml``, versioned and reviewed
like ``owasp_mapping.yaml`` and ``alert_rules.yaml``. **No model writes it and no
model needs to read it.** A reviewer diffs it; that is the control point.

Two sides, and the gap between them is the product
----------------------------------------------------
**Red** — techniques the estate is actually exposed to, derived from the CWE
already classified onto every finding by ``processing.owasp.py``.
**Blue** — techniques the platform's own alert rules can evidence, derived from a
side table keyed by the rule ids in ``alert_rules.yaml``. **That file is not
modified**: adding a rule never rewrites the rule file, and the map is a
separate reviewable artefact.

The gap — exposed but not detected — is what AVP-9 turns into a hunt.

Why this is not AI
-----------------
Everything here is a join and a set difference over two indexed columns. Gate V8
on vector retrieval stays closed; this opens nothing it closed.
"""
from __future__ import annotations

import os
from functools import lru_cache

import yaml
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.finding import Finding
from app.models.metrics import WafBlock

MAPPING_PATH = os.path.join(os.path.dirname(__file__), "attack_mapping.yaml")

#: Default retrospective hunt window.
HUNT_WINDOW_DAYS = 30


@lru_cache(maxsize=1)
def _mapping() -> dict:
    with open(MAPPING_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def mapping_version() -> str:
    return _mapping().get("version", "unknown")


def techniques_for_cwe(cwe_id: str | None) -> list[str]:
    """ATT&CK techniques a finding's weakness class implies.

    Unmapped CWEs return empty rather than a nearest guess. A wrong technique
    in an assurance artefact is worse than an admitted gap, and the gap is
    measurable — the same rule ``processing.owasp.py`` applies.
    """
    if not cwe_id:
        return []
    return list(_mapping()["cwe_techniques"].get(str(cwe_id).strip(), []))


def techniques_for_rule(rule_id: str | None) -> list[str]:
    if not rule_id:
        return []
    return list(_mapping()["rule_techniques"].get(rule_id, []))


def hunt_source_for(technique_id: str) -> dict | None:
    return _mapping()["hunt_sources"].get(technique_id)


async def _red_side(session: AsyncSession, claims) -> dict[str, dict]:
    """Techniques the estate is exposed to, with the findings that evidence it."""
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Finding)
    stmt = (
        select(Finding.cwe_id, Finding.owasp_id, func.count())
        .where(Finding.cwe_id.isnot(None))
        .group_by(Finding.cwe_id, Finding.owasp_id)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    exposed: dict[str, dict] = {}
    unmapped = []
    for cwe, owasp, count in rows:
        techs = techniques_for_cwe(cwe)
        if not techs:
            unmapped.append({"cwe_id": cwe, "owasp_id": owasp, "findings": count})
            continue
        for t in techs:
            slot = exposed.setdefault(t, {"technique": t, "findings": 0, "cwes": set()})
            slot["findings"] += count
            slot["cwes"].add(cwe)
    return {"exposed": exposed, "unmapped_cwes": unmapped}


async def _blue_side(session: AsyncSession, claims) -> dict[str, dict]:
    """Techniques the platform's own alerts have actually evidenced."""
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Alert)
    stmt = (
        select(Alert.rule_id, func.count())
        .group_by(Alert.rule_id)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    detected: dict[str, dict] = {}
    for rule_id, count in rows:
        for t in techniques_for_rule(rule_id):
            slot = detected.setdefault(
                t, {"technique": t, "alerts": 0, "rules": set()}
            )
            slot["alerts"] += count
            slot["rules"].add(rule_id)
    return detected


async def coverage(session: AsyncSession, claims) -> dict:
    """Red against blue, and the gap between them."""
    red = await _red_side(session, claims)
    blue = await _blue_side(session, claims)

    exposed = red["exposed"]
    detected = blue

    gaps = sorted(
        (
            {
                "technique": t,
                "findings": v["findings"],
                "cwes": sorted(v["cwes"]),
                "detected": False,
                "alerts": 0,
            }
            for t, v in exposed.items()
            if t not in detected
        ),
        key=lambda g: -g["findings"],
    )

    return {
        "avp": "AVP-2",
        "deterministic_half": True,
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "computed_by": "app.processing.intel.attack",
        "mapping_version": mapping_version(),
        "attack_release": _mapping().get("attack_release"),
        "mapping_note": (
            "Curated and versioned in attack_mapping.yaml. No model writes or "
            "reads it. alert_rules.yaml is not modified; the rule-to-technique "
            "side table is a separate reviewable artefact."
        ),
        "exposed_techniques": len(exposed),
        "detected_techniques": len(detected),
        "coverage_pct": round(
            len([t for t in exposed if t in detected]) / len(exposed) * 100, 1
        ) if exposed else None,
        "gaps": gaps,
        "gap_count": len(gaps),
        "unmapped_cwes": red["unmapped_cwes"],
        "unmapped_note": (
            "Findings whose CWE carries no ATT&CK mapping are reported, not "
            "guessed at. An unmapped weakness class is a gap in the map, and it "
            "is the platform's own gap to fix."
        ),
    }


def build_hunt_query(technique_id: str, window_days: int = HUNT_WINDOW_DAYS) -> dict:
    """A retrospective query the analyst can run against the caller's own data.

    Built only where the technique has a column binding. Where it does not the
    card says so rather than emitting SQL against columns that do not exist.
    """
    src = hunt_source_for(technique_id)
    if not src:
        return {
            "technique": technique_id,
            "runnable": False,
            "reason": (
                f"No column binding for {technique_id} in attack_mapping.yaml. "
                "No query is emitted rather than one against columns that do "
                "not exist."
            ),
        }
    preds = " OR ".join(
        f"{src['category_column']} ILIKE '%{ind}%'" for ind in src["indicators"]
    )
    sql = (
        f"SELECT {src['uri_column']}, count(*) AS hits, max({src['time_column']}) AS latest\n"
        f"FROM warehouse.{src['table']}\n"
        f"WHERE ({preds})\n"
        f"  AND {src['time_column']} > now() - interval '{window_days} days'\n"
        f"GROUP BY {src['uri_column']}\n"
        f"ORDER BY hits DESC;"
    )
    return {
        "technique": technique_id,
        "runnable": True,
        "source_table": f"warehouse.{src['table']}",
        "window_days": window_days,
        "sql": sql,
        "note": (
            "Built from curated column bindings, not generated. Read-only "
            "SELECT; the caller must still have findings or risks permission."
        ),
    }


async def expected_hit_shape(session: AsyncSession, claims, technique_id: str,
                              window_days: int = HUNT_WINDOW_DAYS) -> dict:
    """What a positive result looks like, read from the caller's own data."""
    from datetime import datetime, timedelta, timezone

    src = hunt_source_for(technique_id)
    if not src:
        return {"technique": technique_id, "available": False}

    from app.api.auth import tenant_filter

    model = WafBlock if src["table"] == "waf_blocks" else Finding
    scope = tenant_filter(claims, model)
    time_col = getattr(model, src["time_column"])
    cat_col = getattr(model, src["category_column"])
    uri_col = getattr(model, src["uri_column"])

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    preds = [cat_col.ilike(f"%{ind}%") for ind in src["indicators"]]

    hits = func.count().label("hits")
    stmt = (
        select(uri_col, hits)
        .where(or_(*preds), time_col >= cutoff)
        .group_by(uri_col)
        .order_by(hits.desc())
        .limit(10)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    total = sum(r[1] for r in rows)
    return {
        "technique": technique_id,
        "available": True,
        "window_days": window_days,
        "source_table": f"warehouse.{src['table']}",
        "total_hits": total,
        "distinct_targets": len(rows),
        "baseline_note": (
            "Counts are the caller's own scope only. Compare against the peer "
            "aggregate exposed by /api/v1/intel/peer/prescription rather than "
            "against another department's raw figures."
        ),
        "targets": [{"target": r[0], "hits": r[1]} for r in rows],
    }


async def hunts(session: AsyncSession, claims, limit: int = 10) -> dict:
    """Coverage gaps turned into prioritised, runnable hunt cards (AVP-9)."""
    cov = await coverage(session, claims)
    cards = []
    for gap in cov["gaps"][:limit]:
        query = build_hunt_query(gap["technique"])
        shape = await expected_hit_shape(session, claims, gap["technique"])
        cards.append({
            "rank": len(cards) + 1,
            "technique": gap["technique"],
            "why": (
                f"{gap['findings']} finding(s) across CWE "
                f"{', '.join(gap['cwes'])} map to {gap['technique']}, and no alert "
                "rule currently evidences it."
            ),
            "query": query,
            "expected_hit_shape": shape,
            "owner": "SOC",
        })
    return {
        "avp": "AVP-9",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "mapping_version": cov["mapping_version"],
        "gaps_available": cov["gap_count"],
        "hunts": cards,
        "note": (
            "Every field is computed: the gap from coverage, the query from "
            "curated column bindings, the expected shape from the caller's own "
            "rows. The narrative around each card is template-fillable and is "
            "not presented as AI."
        ),
    }


def navigator_layer(gap_techniques: list[str], detected_techniques: list[str]) -> dict:
    """ATT&CK Navigator layer JSON for the coverage view."""
    red = [{"technique": t, "score": 100, "color": "", "comment": "exposed"} for t in gap_techniques]
    blue = [
        {"technique": t, "score": 0, "color": "", "comment": "detected"}
        for t in detected_techniques
    ]
    return {
        "name": "SITA ATT&CK coverage",
        "versions": {"attack": _mapping().get("attack_release", "unknown"), "navigator": "4.9.0"},
        "domain": "enterprise-attack",
        "description": "Red: techniques the estate is exposed to. Green: techniques with alerting.",
        "techniques": red + blue,
        "gradient": {"colors": ["#ffffff", "#ff6666"], "minValue": 0, "maxValue": 100},
        "legendItems": [
            {"label": "exposed, no alerting", "color": "#ff6666"},
            {"label": "alerting exists", "color": "#8b949e"},
        ],
    }