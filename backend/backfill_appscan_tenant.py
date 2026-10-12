"""
Backfill tenant attribution on existing AppScan findings.

Fixes rows where app_name is the raw AppScan application UUID
(b816b09c-4240-4ea7-a4b5-f8ae89f62f57) or where department_id is NULL
on appscan-sourced rows, mapping them to home-affairs-digital / dha-digital
and renaming app_name to demo.testfire.net.

Run from backend/:
    python backfill_appscan_tenant.py
"""

import asyncio
from app.db import SessionFactory
from sqlalchemy import text


async def backfill() -> None:
    async with SessionFactory() as session:
        res = await session.execute(text("""
            SELECT count(*), department_id, app_name
            FROM warehouse.findings
            WHERE source = 'appscan'
            GROUP BY department_id, app_name
        """))
        for row in res.fetchall():
            print(dict(row._mapping))
        
        result = await session.execute(text("""
            UPDATE warehouse.findings
            SET
                department_id = 'home-affairs-digital',
                branch_id     = 'dha-digital',
                ministry_id   = 'home-affairs',
                cluster_id    = 'justice',
                app_name      = 'demo.testfire.net'
            WHERE
                source = 'appscan'
                AND (
                    LOWER(app_name) = 'b816b09c-4240-4ea7-a4b5-f8ae89f62f57'
                    OR department_id IS NULL
                )
        """))
        await session.commit()
        print(f"Rows backfilled: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(backfill())
