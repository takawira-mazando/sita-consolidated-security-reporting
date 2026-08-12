"""Migrate the SITA platform to government-style multi-tenancy.

Adds the Department -> Branch hierarchy (warehouse.departments/branches),
`department_id` and `branch_id` columns to every app/db-scoped warehouse
table, then backfills existing rows from the app/db-name mapping. Also moves
identity.users from a single `department_id` to admin-set `department_ids` /
`branch_ids` scope lists and drops the legacy Ministry grouping.

Idempotent: safe to run repeatedly.

Usage:
    python _migrate_tenancy.py
"""
import asyncio
import logging

from app.db import SessionFactory
from app.models.tenant import Branch, Department
from app.tenant import (
    APP_BRANCHES,
    APP_DEPARTMENTS,
    BRANCHES,
    DB_TO_BRANCH,
    DB_TO_DEPARTMENT,
    DEPARTMENT_TO_MINISTRY,
    DEPARTMENTS,
    MINISTRY_TO_CLUSTER,
)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger("migrate_tenancy")

TABLES = [
    ("warehouse.findings", "app_name"),
    ("warehouse.risk_scores", "app_name"),
    ("warehouse.alerts", "target_id"),
    ("warehouse.dispatch_log", None),
    ("warehouse.api_endpoints", "app_name"),
    ("warehouse.waf_blocks", "app_name"),
    ("warehouse.database_inventory", "name"),
]

BACKFILL = {
    "warehouse.findings": ("app_name", {**APP_DEPARTMENTS, **DB_TO_DEPARTMENT}),
    "warehouse.risk_scores": ("app_name", {**APP_DEPARTMENTS, **DB_TO_DEPARTMENT}),
    "warehouse.alerts": ("target_id", {**APP_DEPARTMENTS, **DB_TO_DEPARTMENT}),
    "warehouse.api_endpoints": ("app_name", APP_DEPARTMENTS),
    "warehouse.waf_blocks": ("app_name", APP_DEPARTMENTS),
    "warehouse.database_inventory": ("name", DB_TO_DEPARTMENT),
}

BRANCH_BACKFILL = {
    "warehouse.findings": ("app_name", {**APP_BRANCHES, **DB_TO_BRANCH}),
    "warehouse.risk_scores": ("app_name", {**APP_BRANCHES, **DB_TO_BRANCH}),
    "warehouse.alerts": ("target_id", {**APP_BRANCHES, **DB_TO_BRANCH}),
    "warehouse.api_endpoints": ("app_name", APP_BRANCHES),
    "warehouse.waf_blocks": ("app_name", APP_BRANCHES),
    "warehouse.database_inventory": ("name", DB_TO_BRANCH),
}


async def create_tables(session) -> None:
    for stmt in (
        "CREATE TABLE IF NOT EXISTS warehouse.departments ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  name VARCHAR(120) NOT NULL,"
        "  code VARCHAR(60) NOT NULL UNIQUE)",
        "CREATE TABLE IF NOT EXISTS warehouse.branches ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  name VARCHAR(120) NOT NULL,"
        "  code VARCHAR(60) NOT NULL UNIQUE,"
        "  department_id VARCHAR(36) NOT NULL)",
        "CREATE TABLE IF NOT EXISTS identity.persons ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  employee_number VARCHAR(50) UNIQUE,"
        "  email VARCHAR(255) UNIQUE,"
        "  id_number VARCHAR(20),"
        "  title VARCHAR(20),"
        "  initials VARCHAR(20),"
        "  surname VARCHAR(100),"
        "  display_name VARCHAR(100),"
        "  job_title VARCHAR(120),"
        "  org_unit VARCHAR(120),"
        "  department_id VARCHAR(36),"
        "  branch_id VARCHAR(36),"
        "  manager_id VARCHAR(36),"
        "  manager_name VARCHAR(120),"
        "  work_phone VARCHAR(30),"
        "  location VARCHAR(120),"
        "  employment_status VARCHAR(30) NOT NULL DEFAULT 'active',"
        "  clearance_level VARCHAR(30),"
        "  source VARCHAR(20) NOT NULL DEFAULT 'hr',"
        "  is_active BOOLEAN NOT NULL DEFAULT TRUE,"
        "  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
        "  updated_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    ):
        await session.execute(text(stmt))
    await session.commit()
    logger.info("created departments/branches/persons tables")


async def seed_tenants(session) -> None:
    departments = [{"id": did, "name": name, "code": did} for did, name in DEPARTMENTS.items()]
    stmt = pg_insert(Department).values(departments)
    stmt = stmt.on_conflict_do_nothing(index_elements=[Department.id])
    await session.execute(stmt)
    branches = [
        {"id": bid, "name": name, "code": bid, "department_id": parent}
        for bid, (name, parent) in BRANCHES.items()
    ]
    stmt = pg_insert(Branch).values(branches)
    stmt = stmt.on_conflict_do_nothing(index_elements=[Branch.id])
    await session.execute(stmt)
    await session.commit()
    logger.info("seeded %d departments, %d branches", len(departments), len(branches))


async def add_columns(session) -> None:
    for table, _ in TABLES:
        for column in ("department_id", "branch_id", "ministry_id", "cluster_id"):
            await session.execute(
                text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "
                    f"{column} VARCHAR(36)"
                )
            )
    await session.execute(
        text(
            "ALTER TABLE identity.users ADD COLUMN IF NOT EXISTS "
            "department_ids JSONB DEFAULT '[]'::jsonb"
        )
    )
    await session.execute(
        text(
            "ALTER TABLE identity.users ADD COLUMN IF NOT EXISTS "
            "branch_ids JSONB DEFAULT '[]'::jsonb"
        )
    )
    await session.execute(
        text(
            "ALTER TABLE identity.users ADD COLUMN IF NOT EXISTS "
            "person_id VARCHAR(36)"
        )
    )
    await session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_users_person "
            "ON identity.users(person_id)"
        )
    )
    # Widen dedup_key: national app/db names push source+app composite past 64 chars.
    await session.execute(
        text("ALTER TABLE warehouse.alerts ALTER COLUMN dedup_key TYPE VARCHAR(190)")
    )
    await session.commit()
    logger.info("added department_id/branch_id columns")


async def backfill(session) -> None:
    # Direct app/db-name -> department mappings.
    for table, (col, mapping) in BACKFILL.items():
        for key, dept_id in mapping.items():
            await session.execute(
                text(
                    f"UPDATE {table} SET department_id = :dept "
                    f"WHERE {col} = :key AND department_id IS NULL"
                ),
                {"dept": dept_id, "key": key},
            )
    # Direct app/db-name -> branch mappings.
    for table, (col, mapping) in BRANCH_BACKFILL.items():
        for key, branch_id in mapping.items():
            await session.execute(
                text(
                    f"UPDATE {table} SET branch_id = :branch "
                    f"WHERE {col} = :key AND branch_id IS NULL"
                ),
                {"branch": branch_id, "key": key},
            )
    # ministry/cluster are derived from the resolved department_id (nullable).
    ministry_by_dept = {did: DEPARTMENT_TO_MINISTRY[did] for did in DEPARTMENT_TO_MINISTRY}
    cluster_by_dept = {
        did: MINISTRY_TO_CLUSTER[ministry_by_dept[did]]
        for did in ministry_by_dept
        if ministry_by_dept[did] in MINISTRY_TO_CLUSTER
    }
    for table, _ in TABLES:
        for dept_id, ministry_id in ministry_by_dept.items():
            await session.execute(
                text(
                    f"UPDATE {table} SET ministry_id = :ministry "
                    f"WHERE department_id = :dept AND ministry_id IS NULL"
                ),
                {"ministry": ministry_id, "dept": dept_id},
            )
        for dept_id, cluster_id in cluster_by_dept.items():
            await session.execute(
                text(
                    f"UPDATE {table} SET cluster_id = :cluster "
                    f"WHERE department_id = :dept AND cluster_id IS NULL"
                ),
                {"cluster": cluster_id, "dept": dept_id},
            )
    # dispatch_log inherits from its alert.
    await session.execute(
        text(
            "UPDATE warehouse.dispatch_log dl SET department_id = a.department_id "
            "FROM warehouse.alerts a WHERE dl.alert_id = a.id AND dl.department_id IS NULL"
        )
    )
    await session.execute(
        text(
            "UPDATE warehouse.dispatch_log dl SET branch_id = a.branch_id "
            "FROM warehouse.alerts a WHERE dl.alert_id = a.id AND dl.branch_id IS NULL"
        )
    )
    await session.execute(
        text(
            "UPDATE warehouse.dispatch_log dl SET ministry_id = a.ministry_id "
            "FROM warehouse.alerts a WHERE dl.alert_id = a.id AND dl.ministry_id IS NULL"
        )
    )
    await session.execute(
        text(
            "UPDATE warehouse.dispatch_log dl SET cluster_id = a.cluster_id "
            "FROM warehouse.alerts a WHERE dl.alert_id = a.id AND dl.cluster_id IS NULL"
        )
    )
    # identity.users: migrate legacy single department_id -> scope lists. Only
    # runs while the legacy column still exists (idempotent across re-runs).
    legacy_col = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='identity' AND table_name='users' "
                "AND column_name='department_id'"
            )
        )
    ).scalar()
    if legacy_col:
        await session.execute(
            text(
                "UPDATE identity.users SET department_ids = to_jsonb(array[department_id]) "
                "WHERE department_id IS NOT NULL AND (department_ids IS NULL OR department_ids = '[]'::jsonb)"
            )
        )
        await session.execute(
            text(
                "UPDATE identity.users SET branch_ids = '[]'::jsonb "
                "WHERE branch_ids IS NULL"
            )
        )
        await session.execute(
            text("ALTER TABLE identity.users DROP COLUMN IF EXISTS department_id")
        )
    await session.commit()
    logger.info("backfilled department_id/branch_id from app/db mapping")


async def add_indexes(session) -> None:
    index_defs = [
        ("warehouse.findings", "idx_findings_dept", "department_id"),
        ("warehouse.risk_scores", "idx_risk_dept", "department_id"),
        ("warehouse.alerts", "idx_alerts_dept", "department_id"),
        ("warehouse.dispatch_log", "idx_dispatch_dept", "department_id"),
        ("warehouse.api_endpoints", "idx_api_dept", "department_id"),
        ("warehouse.waf_blocks", "idx_waf_dept", "department_id"),
        ("warehouse.database_inventory", "idx_db_dept", "department_id"),
        ("warehouse.findings", "idx_findings_branch", "branch_id"),
        ("warehouse.risk_scores", "idx_risk_branch", "branch_id"),
        ("warehouse.alerts", "idx_alerts_branch", "branch_id"),
        ("warehouse.dispatch_log", "idx_dispatch_branch", "branch_id"),
        ("warehouse.api_endpoints", "idx_api_branch", "branch_id"),
        ("warehouse.waf_blocks", "idx_waf_branch", "branch_id"),
        ("warehouse.database_inventory", "idx_db_branch", "branch_id"),
        ("warehouse.branches", "idx_branches_dept", "department_id"),
        ("warehouse.findings", "idx_findings_ministry", "ministry_id"),
        ("warehouse.risk_scores", "idx_risk_ministry", "ministry_id"),
        ("warehouse.alerts", "idx_alerts_ministry", "ministry_id"),
        ("warehouse.dispatch_log", "idx_dispatch_ministry", "ministry_id"),
        ("warehouse.api_endpoints", "idx_api_ministry", "ministry_id"),
        ("warehouse.waf_blocks", "idx_waf_ministry", "ministry_id"),
        ("warehouse.database_inventory", "idx_db_ministry", "ministry_id"),
        ("warehouse.findings", "idx_findings_cluster", "cluster_id"),
        ("warehouse.risk_scores", "idx_risk_cluster", "cluster_id"),
        ("warehouse.alerts", "idx_alerts_cluster", "cluster_id"),
        ("warehouse.dispatch_log", "idx_dispatch_cluster", "cluster_id"),
        ("warehouse.api_endpoints", "idx_api_cluster", "cluster_id"),
        ("warehouse.waf_blocks", "idx_waf_cluster", "cluster_id"),
        ("warehouse.database_inventory", "idx_db_cluster", "cluster_id"),
    ]
    for table, index, column in index_defs:
        await session.execute(
            text(f"CREATE INDEX IF NOT EXISTS {index} ON {table}({column})")
        )
    await session.commit()
    logger.info("created department_id/branch_id indexes")


async def drop_legacy_ministry(session) -> None:
    """Remove the obsolete Ministry grouping (tenant is the department)."""
    await session.execute(
        text("ALTER TABLE warehouse.departments DROP COLUMN IF EXISTS ministry_id")
    )
    await session.execute(text("DROP TABLE IF EXISTS warehouse.ministries"))
    await session.commit()
    logger.info("dropped legacy ministries table / ministry_id column")


async def main() -> None:
    async with SessionFactory() as session:
        await create_tables(session)
        # Drop the obsolete ministry grouping first so seed_tenants can insert on
        # databases that still carry the legacy NOT NULL ministry_id column.
        await drop_legacy_ministry(session)
        await seed_tenants(session)
        await add_columns(session)
        await backfill(session)
        await add_indexes(session)
    logger.info("tenancy migration complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(main())
