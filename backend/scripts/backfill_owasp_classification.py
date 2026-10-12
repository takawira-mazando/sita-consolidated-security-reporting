"""Backfill OWASP classification on findings ingested before it existed.

The four classification columns (``owasp_id``, ``cwe_id``, ``owasp_status``,
``taxonomy_version``) are populated at ingest by
``app.lake.writer._build_finding`` calling ``app.processing.owasp.classify``.
Rows ingested before that logic landed have them NULL, so:

- ``GET /api/v1/findings?owasp_id=A03`` returns nothing, silently;
- the AppSec OWASP rollup reads as "no categorised findings" rather than
  "this data predates classification".

Runs the *same* classifier the ingest path uses, so backfilled rows are
indistinguishable from freshly ingested ones. No new mapping logic, which is the
whole point: a second implementation would drift.

Idempotent and safe to re-run. Writes only rows whose classification is still
NULL, so a later taxonomy change is not silently overwritten here --
re-classification is a deliberate act via ``--force``.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.db import SessionFactory
from app.models.finding import Finding
from app.processing import owasp
from sqlalchemy import select, update


async def survey() -> dict[str, int]:
    async with SessionFactory() as session:
        total = (await session.execute(select(Finding.id))).scalars().all()
        classified = (
            await session.execute(
                select(Finding.id).where(Finding.owasp_id.is_not(None))
            )
        ).scalars().all()
        status_recorded = (
            await session.execute(
                select(Finding.id).where(Finding.owasp_status.is_not(None))
            )
        ).scalars().all()
    return {
        "total": len(total),
        "classified": len(classified),
        "status_recorded": len(status_recorded),
    }


async def backfill(force: bool = False) -> dict[str, int]:
    """Recompute classification for findings that lack it.

    Every row is written, including the ones that do not map. That is the point
    of ``owasp_status``: a NULL ``owasp_id`` is ambiguous on its own, and
    recording *why* it is empty (unmapped / not_applicable / absent) is what
    makes the column trustworthy. Writing only the classified rows would leave
    the remainder indistinguishable from "never ran the backfill".
    """
    updated = skipped = 0

    async with SessionFactory() as session:
        q = select(Finding)
        if not force:
            q = q.where(Finding.owasp_id.is_(None))
        rows = (await session.execute(q)).scalars().all()

        for row in rows:
            classification = owasp.classify(row.category, row.source)
            if classification is None:
                # classify() should always return a Classification, including an
                # unclassified one. Treat a None as a defect rather than
                # silently leaving the row ambiguous.
                skipped += 1
                continue
            if (
                not force
                and row.owasp_id == classification.owasp_id
                and row.owasp_status == classification.status
                and row.cwe_id == classification.cwe_id
            ):
                continue
            await session.execute(
                update(Finding)
                .where(Finding.id == row.id)
                .values(
                    owasp_id=classification.owasp_id,
                    cwe_id=classification.cwe_id,
                    owasp_status=classification.status,
                    taxonomy_version=classification.taxonomy_version,
                )
            )
            updated += 1

        await session.commit()
    return {
        "updated": updated,
        "skipped": skipped,
        "taxonomy_version": owasp.taxonomy_version(),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-classify rows that already have an owasp_id (use after a taxonomy change)",
    )
    parser.add_argument("--verify", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    print(f"OWASP taxonomy version: {owasp.taxonomy_version()}")

    before = await survey()
    print(
        f"  before: {before['classified']}/{before['total']} classified, "
        f"{before['status_recorded']}/{before['total']} with a recorded status"
    )
    if args.verify:
        return 0

    result = await backfill(force=args.force)
    print(
        f"  updated {result['updated']} row(s); {result['skipped']} could not be "
        f"classified at all"
    )

    after = await survey()
    print(
        f"  after:  {after['classified']}/{after['total']} classified, "
        f"{after['status_recorded']}/{after['total']} with a recorded status"
    )

    async with SessionFactory() as session:
        print("\n  distribution (owasp_id / owasp_status):")
        rows = (
            await session.execute(
                select(Finding.owasp_id, Finding.owasp_status)
                .where(Finding.owasp_status.is_not(None))
            )
        ).all()
        counts: dict[tuple, int] = {}
        for r in rows:
            counts[(r.owasp_id, r.owasp_status)] = counts.get((r.owasp_id, r.owasp_status), 0) + 1
        for (oid, status), n in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            print(f"    {str(oid):8s} {str(status):16s} {n}")
        if not counts:
            print("    (nothing classified -- check the taxonomy mapping file)",
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))