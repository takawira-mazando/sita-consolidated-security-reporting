"""Add OWASP Top 10 classification to warehouse.findings.

Adds `owasp_id`, `cwe_id`, `owasp_status` and `taxonomy_version`, then
classifies every existing row from the `source` + `category` already stored.
`category` is never rewritten -- the OEM's value is preserved and this only
adds the platform's own mapping beside it.

Idempotent: safe to run repeatedly. Re-running re-classifies every row, which is
the intended way to pick up an edited `owasp_mapping.yaml`.

Usage:
    python _migrate_owasp.py            # apply and backfill
    python _migrate_owasp.py --dry-run  # report only
    python _migrate_owasp.py --report   # classification coverage, no writes
"""
import asyncio
import logging
import sys

from app.db import SessionFactory
from app.processing import owasp
from sqlalchemy import text

logger = logging.getLogger("migrate_owasp")

NEW_COLUMNS = [
    ("owasp_id", "VARCHAR(10)"),
    ("cwe_id", "VARCHAR(20)"),
    ("owasp_status", "VARCHAR(20)"),
    ("taxonomy_version", "VARCHAR(32)"),
]

NEW_INDEXES = [
    ("idx_findings_owasp", "owasp_id"),
    ("idx_findings_cwe", "cwe_id"),
    ("idx_findings_owasp_status", "owasp_status"),
    ("idx_findings_owasp_dept", "(department_id, owasp_id)"),
]

ARCHIVE_COLUMNS = [
    ("owasp_id", "VARCHAR(10)"),
    ("cwe_id", "VARCHAR(20)"),
    ("owasp_status", "VARCHAR(20)"),
    ("taxonomy_version", "VARCHAR(32)"),
]


async def add_columns(session, table: str, columns) -> list[str]:
    """Add any of `columns` that `table` does not already have."""
    added = []
    exists = {
        r["column_name"]
        for r in (await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = :table"
            ),
            {"schema": table.split(".")[0], "table": table.split(".")[1]},
        )).mappings()
    }
    for name, ddl in columns:
        if name in exists:
            continue
        await session.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}"))
        added.append(name)
    return added


async def add_indexes(session) -> None:
    for name, cols in NEW_INDEXES:
        await session.execute(
            text(f"CREATE INDEX IF NOT EXISTS {name} ON warehouse.findings {cols}")
        )


async def backfill(session, dry_run: bool = False) -> dict:
    rows = (
        await session.execute(
            text("SELECT id, source, category FROM warehouse.findings")
        )
    ).mappings().all()

    stats = {"classified": 0, "unmapped": 0, "not_applicable": 0, "absent": 0}
    unmapped_values: dict[str, int] = {}
    updates = []

    for row in rows:
        result = owasp.classify(row["category"], row["source"])
        stats[result.status] = stats.get(result.status, 0) + 1
        if result.status == owasp.UNMAPPED:
            key = f"{row['source']}::{row['category']}"
            unmapped_values[key] = unmapped_values.get(key, 0) + 1
        updates.append(
            {
                "id": row["id"],
                "owasp_id": result.owasp_id,
                "cwe_id": result.cwe_id,
                "owasp_status": result.status,
                "taxonomy_version": result.taxonomy_version,
            }
        )

    if not dry_run and updates:
        await session.execute(
            text(
                """
                UPDATE warehouse.findings f
                   SET owasp_id         = v.owasp_id,
                       cwe_id           = v.cwe_id,
                       owasp_status     = v.owasp_status,
                       taxonomy_version = v.taxonomy_version
                  FROM (SELECT unnest(:ids) AS id,
                               unnest(:owasp_ids) AS owasp_id,
                               unnest(:cwe_ids) AS cwe_id,
                               unnest(:statuses) AS owasp_status,
                               unnest(:versions) AS taxonomy_version) v
                 WHERE f.id = v.id
                """
            ),
            {
                "ids": [u["id"] for u in updates],
                "owasp_ids": [u["owasp_id"] for u in updates],
                "cwe_ids": [u["cwe_id"] for u in updates],
                "statuses": [u["owasp_status"] for u in updates],
                "versions": [u["taxonomy_version"] for u in updates],
            },
        )

    stats["_unmapped_values"] = unmapped_values
    stats["_total"] = len(rows)
    return stats


async def report(session) -> None:
    rows = (
        await session.execute(
            text(
                "SELECT source, category, count(*) AS n "
                "FROM warehouse.findings "
                "WHERE owasp_status = 'unmapped' "
                "GROUP BY source, category ORDER BY n DESC"
            )
        )
    ).mappings().all()
    print("\nUnmapped vendor values awaiting a rule in owasp_mapping.yaml:\n")
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  {r['n']:>6}  {r['source']:<14} {r['category']}")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dry_run = "--dry-run" in sys.argv
    report_only = "--report" in sys.argv

    async with SessionFactory() as session:
        if report_only:
            await report(session)
            return

        added = await add_columns(session, "warehouse.findings", NEW_COLUMNS)
        logger.info(
            "warehouse.findings: added %s",
            ", ".join(added) if added else "nothing (already migrated)",
        )

        # archive.findings is created with LIKE ... INCLUDING ALL, so on a fresh
        # install the columns arrive automatically. On an existing install the
        # table predates them and rotation would silently drop the values.
        try:
            await add_columns(session, "archive.findings", ARCHIVE_COLUMNS)
            logger.info("archive.findings: columns ensured")
        except Exception as exc:  # noqa: BLE001 - archive may not exist yet
            logger.warning("archive.findings skipped: %s", exc)

        await add_indexes(session)

        stats = await backfill(session, dry_run=dry_run)
        if dry_run:
            await session.rollback()
            logger.info("dry run - no writes committed")
        else:
            await session.commit()

        logger.info("taxonomy      : %s", owasp.taxonomy_version())
        logger.info("rows examined : %s", stats["_total"])
        for status in ("classified", "unmapped", "not_applicable", "absent"):
            logger.info("  %-14s %s", status, stats.get(status, 0))

        if stats["_unmapped_values"]:
            logger.info("\nunmapped vendor values to curate in owasp_mapping.yaml:")
            for key, n in sorted(
                stats["_unmapped_values"].items(), key=lambda kv: -kv[1]
            ):
                logger.info("  %6s  %s", n, key)

    if not dry_run:
        await report_from_new_session()


async def report_from_new_session() -> None:
    async with SessionFactory() as session:
        await report(session)


if __name__ == "__main__":
    asyncio.run(main())
