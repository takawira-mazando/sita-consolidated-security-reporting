"""Deterministic cross-vendor analysis. No model, no external call.

Backs AVP-4 (cross-OEM contradiction detection) and AVP-10 (coverage and
agreement attestation). Both are joins and set differences over tables the
warehouse already holds, joined on ``app_name`` — the denormalised key that
every source-derived table already shares.

Why ``app_name``
----------------
It is the only key the four OEMs can be joined on, because it is the one field
the platform already denormalises onto every warehouse row. That makes it the
right join and simultaneously the single biggest risk in this module: vendors
spell application names differently. :func:`normalisation_quality` measures that
directly, and callers are expected to surface it alongside any conclusion drawn
from these functions. A contradiction count derived from a broken join is worse
than no count, because it looks precise.

What this module deliberately does not do
-----------------------------------------
It does not join ``findings.app_name`` to ``database_inventory.name``. Those are
different namespaces — the alert enricher carries a separate ``DB_TO_DEPARTMENT``
reverse lookup precisely because database names are not application names — and
conflating them would manufacture a contradiction on every row. Recorded in
``capability.REGISTRY`` as ``app_to_database_mapping``, blocked on a mapping
table that does not exist.

It does not compute a coverage percentage. There is no asset inventory, so the
denominator is unknown. :func:`attestation` returns ``denominator_known: false``
rather than inventing one.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.metrics import ApiEndpoint, WafBlock

#: A finding open longer than this is counted as ageing.
AGEING_DAYS = 180

#: Statuses the fix-rate and closure calculations treat as closed. Taken from the
#: existing vocabulary in app.processing.compliance and app.api.routers.metrics
#: rather than invented here, so the two cannot drift.
CLOSED_STATUSES = ("fixed", "closed", "resolved", "remediated")


@dataclass(frozen=True)
class Check:
    """One named observation. ``count`` is rows; ``detail`` carries the rows."""

    id: str
    finding: str
    count: int
    detail: list[dict] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["detail"] = self.detail or []
        return d


def _scope_clause(claims, model):
    """``tenant_filter`` for these tables, imported lazily.

    Imported inside the function so this module can be imported and unit-tested
    without a request context.
    """
    from app.api.auth import tenant_filter

    return tenant_filter(claims, model)


async def single_vendor_apps(
    session: AsyncSession, claims, limit: int = 50
) -> Check:
    """Applications reported by exactly one of the ingested sources (AVP-4).

    A single-vendor application is a coverage statement, not an accusation: it
    may be genuinely clean, or genuinely unwatched. The platform cannot
    distinguish the two without an asset inventory, so neither does this.
    """
    scope = _scope_clause(claims, Finding)
    stmt = (
        select(Finding.app_name, func.count(distinct(Finding.source)).label("sources"))
        .where(Finding.app_name.isnot(None))
        .group_by(Finding.app_name)
        .having(func.count(distinct(Finding.source)) == 1)
        .limit(limit)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    total_stmt = select(func.count()).select_from(
        select(Finding.app_name)
        .group_by(Finding.app_name)
        .having(func.count(distinct(Finding.source)) == 1)
        .subquery()
    )
    total = (await session.execute(total_stmt)).scalar() or 0

    return Check(
        id="single_vendor_apps",
        finding=(
            "Applications for which only one of the ingested security sources has "
            "ever returned a finding."
        ),
        count=total,
        detail=[{"app_name": r.app_name} for r in rows],
    )


async def vendor_agreement_matrix(session: AsyncSession, claims) -> Check:
    """Pairwise application overlap between sources (AVP-4, AVP-10).

    If two vendors overlap on most applications they broadly agree about the
    estate. If they overlap on a handful they are looking at materially different
    populations, and the merged view a client sees is a union of two incompatible
    claims. No single vendor can compute this — it requires seeing all of them.
    """
    scope = _scope_clause(claims, Finding)
    apps_by_source_stmt = (
        select(Finding.source, func.array_agg(distinct(Finding.app_name)))
        .group_by(Finding.source)
    )
    if scope is not None:
        apps_by_source_stmt = apps_by_source_stmt.where(scope)
    rows = (await session.execute(apps_by_source_stmt)).all()
    sets = {r.source: set(r[1] or []) for r in rows}

    sources = sorted(sets)
    pairs = []
    for i, a in enumerate(sources):
        for b in sources[i + 1:]:
            overlap = sets[a] & sets[b]
            union = sets[a] | sets[b]
            pairs.append({
                "source_a": a,
                "source_b": b,
                "apps_a": len(sets[a]),
                "apps_b": len(sets[b]),
                "shared_apps": len(overlap),
                # Jaccard-style ratio. Reported as a ratio of two known counts,
                # not as a coverage percentage of an unknown estate.
                "agreement": round(len(overlap) / len(union), 3) if union else 0.0,
            })
    pairs.sort(key=lambda p: p["agreement"])
    return Check(
        id="vendor_agreement_matrix",
        finding="Pairwise application overlap between ingested sources, weakest first.",
        count=len(pairs),
        detail=pairs,
    )


async def endpoints_never_attacked(session: AsyncSession, claims, limit: int = 50) -> Check:
    """Known API endpoints with no matching WAF block event (AVP-4).

    ``api_endpoints`` and ``waf_blocks`` do not share a foreign key, so the join
    is on the endpoint path itself. Imperva reports the path it blocked and the
    API inventory reports the path that exists; a path in the inventory that
    never appears in the block log is either quiet or unwatched.
    """
    scope_api = _scope_clause(claims, ApiEndpoint)
    scope_waf = _scope_clause(claims, WafBlock)

    uri_stmt = select(func.array_agg(distinct(WafBlock.request_uri))).where(
        WafBlock.request_uri.isnot(None)
    )
    if scope_waf is not None:
        uri_stmt = uri_stmt.where(scope_waf)
    seen = set((await session.execute(uri_stmt)).scalar() or [])

    endpoint_stmt = (
        select(distinct(ApiEndpoint.endpoint), ApiEndpoint.app_name)
        .where(ApiEndpoint.endpoint.isnot(None))
        .limit(limit * 4)
    )
    if scope_api is not None:
        endpoint_stmt = endpoint_stmt.where(scope_api)
    endpoints = (await session.execute(endpoint_stmt)).all()

    untouched = [
        {"app_name": r.app_name, "endpoint": r.endpoint}
        for r in endpoints
        if r.endpoint not in seen
    ]
    return Check(
        id="endpoints_never_attacked",
        finding=(
            "Endpoints present in the API inventory for which no WAF block event "
            "exists. Quiet, or unwatched - the platform cannot distinguish."
        ),
        count=len(untouched),
        detail=untouched[:limit],
    )


async def ageing_by_source(session: AsyncSession, claims) -> Check:
    """Open findings older than ``AGEING_DAYS``, by source (AVP-4, AVP-10)."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=AGEING_DAYS)
    scope = _scope_clause(claims, Finding)

    stmt = (
        select(
            Finding.source,
            func.count().label("total"),
            func.count()
            .filter(Finding.last_seen < cutoff)
            .label("ageing"),
        )
        .group_by(Finding.source)
        .order_by(Finding.source)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    detail = []
    for r in rows:
        total = r.total or 0
        detail.append({
            "source": r.source,
            "total_findings": total,
            "ageing_over_180d": r.ageing or 0,
            "ageing_pct": round((r.ageing or 0) / total * 100, 1) if total else 0.0,
        })
    return Check(
        id="ageing_by_source",
        finding=f"Findings last seen more than {AGEING_DAYS} days ago, by source.",
        count=len(detail),
        detail=detail,
    )


async def closure_rate_by_source(session: AsyncSession, claims) -> Check:
    """Share of findings in a closed state, by source (AVP-10)."""
    scope = _scope_clause(claims, Finding)
    stmt = (
        select(
            Finding.source,
            func.count().label("total"),
            func.count()
            .filter(Finding.status.in_(CLOSED_STATUSES))
            .label("closed"),
        )
        .group_by(Finding.source)
        .order_by(Finding.source)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    detail = []
    for r in rows:
        total = r.total or 0
        detail.append({
            "source": r.source,
            "total_findings": total,
            "closed": r.closed or 0,
            "closure_rate_pct": round((r.closed or 0) / total * 100, 1) if total else 0.0,
        })
    return Check(
        id="closure_rate_by_source",
        finding="Findings in a closed state, by source.",
        count=len(detail),
        detail=detail,
    )


async def normalisation_quality(session: AsyncSession, claims) -> Check:
    """How trustworthy the ``app_name`` join actually is (AVP-4, AVP-10).

    Every other function in this module joins on ``app_name``. This one measures
    that join. Sources whose spellings collapse to few canonical names are
    trustworthy; sources emitting many variants are not, and a contradiction
    count derived from them is noise dressed as precision.

    Heuristic, deliberately cheap: a name is treated as a distinct spelling when
    it differs from its nearest sibling only by case or separator. This is not a
    full fuzzy matcher and does not need to be — it exists to catch the obvious
    failure, which is inconsistent casing and separators.
    """
    scope = _scope_clause(claims, Finding)
    stmt = select(Finding.app_name, Finding.source).distinct().limit(5000)
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()

    def canon(name: str) -> str:
        return "".join(ch for ch in name.lower() if ch.isalnum())

    canonical: dict[str, set[str]] = {}
    sources_seen: dict[str, int] = {}
    for name, source in rows:
        if not name:
            continue
        sources_seen[source] = sources_seen.get(source, 0) + 1
        canonical.setdefault(canon(name), set()).add(name)

    colliding = {k: sorted(v) for k, v in canonical.items() if len(v) > 1}
    detail = []
    for canon_name, spellings in sorted(colliding.items(), key=lambda kv: -len(kv[1]))[:25]:
        detail.append({"canonical": canon_name, "spellings": spellings})

    observed = len(rows)
    collapsed = len(canonical)
    return Check(
        id="appname_normalisation_quality",
        finding=(
            "Distinct app_name spellings observed per source. A spelling count far "
            "above the canonical count means cross-vendor joins are unreliable and "
            "the other checks here should be read with that in mind."
        ),
        count=len(colliding),
        detail=[{
            "observed_spellings": observed,
            "canonical_names": collapsed,
            "collision_groups": len(colliding),
            "collision_ratio": round(len(colliding) / collapsed, 3) if collapsed else 0.0,
            "per_source_observations": dict(sorted(sources_seen.items())),
            "examples": detail,
        }],
    )


async def contradictions(session: AsyncSession, claims) -> dict:
    """Every deterministic cross-vendor check for one caller's scope (AVP-4)."""
    checks = [
        await single_vendor_apps(session, claims),
        await vendor_agreement_matrix(session, claims),
        await endpoints_never_attacked(session, claims),
        await ageing_by_source(session, claims),
        await normalisation_quality(session, claims),
    ]
    return {
        "avp": "AVP-4",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "computed_by": "app.processing.intel.vendor",
        "checks": [c.as_dict() for c in checks],
    }


async def attestation(session: AsyncSession, claims) -> dict:
    """Coverage and agreement across the ingested sources (AVP-10).

    Carries ``denominator_known: false`` throughout. There is no asset
    inventory, so a coverage percentage would be a ratio of an unknown estate —
    which is worse than no figure, because it invites a procurement decision it
    cannot support.
    """
    volume = await ageing_by_source(session, claims)
    closure = await closure_rate_by_source(session, claims)
    agreement = await vendor_agreement_matrix(session, claims)
    norm = await normalisation_quality(session, claims)

    return {
        "avp": "AVP-10",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "computed_by": "app.processing.intel.vendor",
        "denominator_known": False,
        "coverage_pct_reported": False,
        "denominator_note": (
            "The platform holds no asset inventory. Every application name in the "
            "warehouse arrived attached to a finding, so an application producing "
            "no findings is not visible to be counted. No coverage percentage is "
            "published because its denominator does not exist."
        ),
        "volume_and_ageing": volume.as_dict(),
        "closure": closure.as_dict(),
        "agreement": agreement.as_dict(),
        "normalisation_quality": norm.as_dict(),
    }