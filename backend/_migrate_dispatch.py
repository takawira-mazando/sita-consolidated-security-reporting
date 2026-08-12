import asyncio

from app.db import SessionFactory
from sqlalchemy import text

STATEMENTS = [
    "ALTER TABLE warehouse.alerts ADD COLUMN IF NOT EXISTS channels JSONB",
    "ALTER TABLE warehouse.alerts ADD COLUMN IF NOT EXISTS last_dispatched_at TIMESTAMPTZ",
    "CREATE TABLE IF NOT EXISTS warehouse.dispatch_log (id VARCHAR(36) PRIMARY KEY, alert_id VARCHAR(64) NOT NULL, channel VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'sent', error TEXT, attempted_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    "CREATE INDEX IF NOT EXISTS idx_dispatch_log_alert ON warehouse.dispatch_log(alert_id)",
    "CREATE INDEX IF NOT EXISTS idx_dispatch_log_channel ON warehouse.dispatch_log(channel)",
]


async def main():
    async with SessionFactory() as s:
        for stmt in STATEMENTS:
            await s.execute(text(stmt))
        await s.commit()
        rows = (await s.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='warehouse' AND table_name='alerts' ORDER BY ordinal_position"
        ))).all()
        print("alerts columns:", [r.column_name for r in rows])
        tables = (await s.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='warehouse' ORDER BY table_name"
        ))).all()
        print("warehouse tables:", [r.table_name for r in tables])


asyncio.run(main())
