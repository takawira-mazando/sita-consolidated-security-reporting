"""Migration: add the provincial layer + audit action trail.

Adds identity.users.province_ids, warehouse.provinces, warehouse.departments
.province_id, and the audit.action_audit table for the Auditor-General secure
export engine. Idempotent (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

Run: python _migrate_province.py
"""
import asyncio

from app.db import SessionFactory
from sqlalchemy import text

STATEMENTS = [
    "ALTER TABLE identity.users ADD COLUMN IF NOT EXISTS province_ids JSONB NOT NULL DEFAULT '[]'::jsonb",
    "CREATE TABLE IF NOT EXISTS warehouse.provinces (id VARCHAR(20) PRIMARY KEY, name VARCHAR(60) NOT NULL, code VARCHAR(20) NOT NULL UNIQUE)",
    "ALTER TABLE warehouse.departments ADD COLUMN IF NOT EXISTS province_id VARCHAR(20)",
    "CREATE INDEX IF NOT EXISTS idx_departments_province ON warehouse.departments(province_id)",
    "CREATE TABLE IF NOT EXISTS audit.action_audit (id VARCHAR(36) PRIMARY KEY, actor VARCHAR(255) NOT NULL, action VARCHAR(50) NOT NULL, target VARCHAR(255), tenant_scope JSONB, payload_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    "CREATE INDEX IF NOT EXISTS idx_action_audit_actor ON audit.action_audit(actor)",
    "CREATE INDEX IF NOT EXISTS idx_action_audit_created ON audit.action_audit(created_at)",
]


async def main():
    async with SessionFactory() as s:
        for stmt in STATEMENTS:
            await s.execute(text(stmt))
        await s.commit()
        tables = (await s.execute(text(
            "SELECT table_schema || '.' || table_name FROM information_schema.tables "
            "WHERE table_schema IN ('warehouse','identity','audit') ORDER BY 1"
        ))).all()
        print("tables:", [r[0] for r in tables])
        cols = (await s.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='identity' AND table_name='users' ORDER BY ordinal_position"
        ))).all()
        print("identity.users columns:", [r[0] for r in cols])


asyncio.run(main())
