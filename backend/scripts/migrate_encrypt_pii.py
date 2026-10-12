"""Migrate plaintext personal data in place to encrypted envelopes.

One-off, idempotent. Run after ``init-db.sql`` and after the application has
been configured with a real ``PII_ENCRYPTION_KEY``::

    python -m scripts.migrate_encrypt_pii

The application reads legacy plaintext transparently (see
``app.pii_crypto.decrypt``), so this is not urgent for correctness — it is what
makes the at-rest claim true on the rows that already exist.

Idempotent: rows already carrying an envelope are skipped, so re-running is
safe. ``--verify`` reports without writing.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.db import SessionFactory
from app.models.person import Person
from app.pii_crypto import ENVELOPE_VERSION, is_encrypted, key_id
from sqlalchemy import func, select, text, update

#: Columns holding personal data that must not sit on disk in the clear.
PII_COLUMNS = ("id_number",)
AAD = {column: f"identity.persons.{column}" for column in PII_COLUMNS}


async def survey() -> dict[str, int]:
    async with SessionFactory() as session:
        counts = {}
        for column in PII_COLUMNS:
            total = (
                await session.execute(
                    select(func.count())
                    .select_from(Person)
                    .where(getattr(Person, column).is_not(None))
                )
            ).scalar_one()
            encrypted = await session.execute(
                select(func.count())
                .select_from(Person)
                .where(
                    getattr(Person, column).is_not(None),
                    getattr(Person, column).like(f"{ENVELOPE_VERSION}:%"),
                )
            )
            counts[column] = {"total": total, "encrypted": encrypted.scalar_one()}
        return counts


async def migrate(dry_run: bool = False) -> dict[str, int]:
    """Rewrite plaintext PII columns as encrypted envelopes.

    Reads the **raw** stored form via text() rather than through the ORM. The
    TypeDecorator decrypts on read by design, so an ORM read of an encrypted row
    returns plaintext and ``is_encrypted`` would report every row as needing
    migration -- causing an endless rewrite on each run and a meaningless
    "migrated" count.
    """
    migrated = 0
    async with SessionFactory() as session:
        raw = (
            await session.execute(
                text("SELECT id, id_number FROM identity.persons "
                     "WHERE id_number IS NOT NULL")
            )
        ).fetchall()
        for row in raw:
            if is_encrypted(row.id_number):
                continue
            if not dry_run:
                # Writing the plaintext back through the column re-encrypts it
                # on the way to the database via the TypeDecorator.
                await session.execute(
                    update(Person)
                    .where(Person.id == row.id)
                    .values(id_number=row.id_number)
                )
            migrated += 1
        if not dry_run:
            await session.commit()
    return {"migrated": migrated}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    print(f"PII encryption key id: {key_id()}")

    before = await survey()
    for column, stats in before.items():
        plaintext = stats["total"] - stats["encrypted"]
        state = "OK" if plaintext == 0 else "PLAINTEXT PRESENT"
        print(f"  {column:12s} total={stats['total']:6d} encrypted={stats['encrypted']:6d} "
              f"plaintext={plaintext:6d}  {state}")

    if args.verify:
        return 0

    result = await migrate()
    print(f"\nmigrated {result['migrated']} row(s) to encrypted envelopes")

    after = await survey()
    for column, stats in after.items():
        plaintext = stats["total"] - stats["encrypted"]
        if plaintext:
            print(f"  WARNING: {column} still has {plaintext} plaintext row(s)", file=sys.stderr)
            return 1
        print(f"  {column}: all {stats['total']} row(s) encrypted")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))