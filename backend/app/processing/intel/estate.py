"""Estate ownership and concentration. No model, no external call.

Backs AVP-6. The graph this module reads is already fully denormalised onto
every warehouse row: ``app_name`` x ``department_id`` x ``branch_id`` x
``ministry_id`` x ``cluster_id`` x ``source``. Six columns, present on every
table, joined for the first time.

Why this matters
----------------
An application attributed to two departments in two provinces has no owner of
record. Nobody knows who is accountable for fixing it, which is the failure
mode that lets a critical finding sit open across a budget cycle. No single OEM
can see it, because each sees only its own rows.

What it is not
--------------
This is not a dependency graph. Third-party dependency data is never ingested;
AppScan's SCA output would arrive unstructured inside ``raw_data`` and is not
mapped. That idea was removed from AVP-6 for exactly this reason.

It is also not clustering, and it needs no embeddings. These are ``GROUP BY
... HAVING COUNT(DISTINCT ...) > 1`` queries over indexed columns. The plan's
gate V8 on vector retrieval is untouched and remains closed — semantic retrieval
does not beat a filtered ``ILIKE`` on short free-text findings, and nothing here
depends on that being untrue.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.metrics import ApiEndpoint, DatabaseInventory, WafBlock

#: The source tables carrying the denormalised tenancy columns.
TENANCY_TABLES = (Finding, ApiEndpoint, WafBlock, DatabaseInventory)


@dataclass(frozen=True)
class Finding_(object):
    """Observation about the estate's ownership graph."""

    id: str
    finding: str
    count: int
    detail: list[dict] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["detail"] = self.detail or []
        return d


async def _distinct_owners(session: AsyncSession, claims, column, label: str) -> Finding_:
    """Applications carrying more than one distinct value in ``column``.

    ``column`` is one of the denormalised tenancy columns. A count above one is
    the ambiguity this proposition exists to surface.
    """
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Finding)
    stmt = (
        select(
            Finding.app_name,
            func.count(distinct(column)).label("owners"),
            func.array_agg(distinct(column)).label("values"),
        )
        .where(Finding.app_name.isnot(None))
        .group_by(Finding.app_name)
        .having(func.count(distinct(column)) > 1)
        .order_by(func.count(distinct(column)).desc())
        .limit(50)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()
    return Finding_(
        id=f"ambiguous_{label}",
        finding=(
            f"Applications attributed to more than one {label}. Ownership of record "
            f"is unclear, so remediation accountability is unclear."
        ),
        count=len(rows),
        detail=[
            {"app_name": r.app_name, f"{label}_count": r.owners, "values": sorted(v for v in (r.values or []) if v)}
            for r in rows
        ],
    )


async def ambiguous_ownership(session: AsyncSession, claims) -> dict:
    """Ambiguity across department, branch, ministry and cluster (AVP-6)."""
    parts = [
        await _distinct_owners(session, claims, Finding.department_id, "department"),
        await _distinct_owners(session, claims, Finding.branch_id, "branch"),
        await _distinct_owners(session, claims, Finding.ministry_id, "ministry"),
        await _distinct_owners(session, claims, Finding.cluster_id, "cluster"),
    ]
    total = sum(p.count for p in parts)
    return {
        "avp": "AVP-6",
        "requires_model": False,
        "scope_class": "tenant_scoped",
        "computed_by": "app.processing.intel.estate",
        "ambiguous_applications": total,
        "checks": [p.as_dict() for p in parts],
    }


async def shared_application_blast_radius(session: AsyncSession, claims) -> Finding_:
    """Departments that appear against the same application name (AVP-6).

    A compromise of a shared application reaches every department holding it.
    The same underlying rows drive this and ``ambiguous_ownership``; this
    presentation is ordered by blast radius, that one by ambiguity depth.
    """
    from app.api.auth import tenant_filter

    scope = tenant_filter(claims, Finding)
    stmt = (
        select(
            Finding.app_name,
            func.count(distinct(Finding.department_id)).label("depts"),
            func.array_agg(distinct(Finding.department_id)).label("departments"),
            func.count(distinct(Finding.branch_id)).label("branches"),
        )
        .where(Finding.app_name.isnot(None), Finding.department_id.isnot(None))
        .group_by(Finding.app_name)
        .having(func.count(distinct(Finding.department_id)) > 1)
        .order_by(func.count(distinct(Finding.department_id)).desc())
        .limit(50)
    )
    if scope is not None:
        stmt = stmt.where(scope)
    rows = (await session.execute(stmt)).all()
    return Finding_(
        id="shared_application_blast_radius",
        finding=(
            "Applications carrying findings for more than one department. A "
            "compromise reaches all of them."
        ),
        count=len(rows),
        detail=[
            {
                "app_name": r.app_name,
                "department_count": r.depts,
                "departments": sorted(d for d in (r.departments or []) if d),
                "branch_count": r.branches,
            }
            for r in rows
        ],
    )


async def monitoring_asymmetry(session: AsyncSession, claims) -> Finding_:
    """Applications the database layer sees but the application layer does not (AVP-6).

    Imperva DAM reports database activity and AppScan reports application
    defects. An application appearing under one and not the other is a layer the
    estate is watching unevenly. This is a coverage asymmetry observation, not a
    defect in either vendor.
    """
    from app.api.auth import tenant_filter

    scope_f = tenant_filter(claims, Finding)
    stmt = (
        select(Finding.app_name, func.array_agg(distinct(Finding.source)))
        .where(Finding.app_name.isnot(None))
        .group_by(Finding.app_name)
    )
    if scope_f is not None:
        stmt = stmt.where(scope_f)
    rows = (await session.execute(stmt)).all()

    dam_only, appscan_only, both = [], [], []
    for app_name, sources in rows:
        src = set(sources or [])
        has_dam = bool(src & {"imperva_dam", "imperva_waf"})
        has_as = "appscan" in src
        if has_dam and not has_as:
            dam_only.append({"app_name": app_name, "sources": sorted(src)})
        elif has_as and not has_dam:
            appscan_only.append({"app_name": app_name, "sources": sorted(src)})
        elif has_as and has_dam:
            both.append({"app_name": app_name})

    return Finding_(
        id="monitoring_asymmetry",
        finding=(
            "Applications reported by the database-activity layer but not the "
            "application-scanning layer, and the reverse. Uneven coverage between "
            "layers, not a vendor defect."
        ),
        count=len(dam_only) + len(appscan_only),
        detail=[{
            "database_layer_only": len(dam_only),
            "application_layer_only": len(appscan_only),
            "both_layers": len(both),
            "examples_database_layer_only": dam_only[:10],
            "examples_application_layer_only": appscan_only[:10],
        }],
    )


async def estate_graph(session: AsyncSession, claims) -> dict:
    """Every deterministic ownership observation for one caller's scope (AVP-6)."""
    ownership = await ambiguous_ownership(session, claims)
    blast = await shared_application_blast_radius(session, claims)
    asym = await monitoring_asymmetry(session, claims)
    return {
        "scope_class": "tenant_scoped",
        "requires_model": False,
        "graph_columns": [
            "app_name", "department_id", "branch_id", "ministry_id", "cluster_id", "source",
        ],
        "source_tables": [t.__tablename__ for t in TENANCY_TABLES],
        "ambiguous_ownership": ownership["checks"],
        "ambiguous_applications": ownership["ambiguous_applications"],
        "blast_radius": blast.as_dict(),
        "monitoring_asymmetry": asym.as_dict(),
    }