# Archived: already-applied seed data

These scripts populated the development and demonstration database. **The seeding
has already been run against it**, so they were removed from the live tree on
2026-10-12 to stop them being mistaken for steps still to be performed.

They are kept here — not deleted — because they are the only record of how the
current data was produced, and because a fresh environment still needs a way to
be populated.

## What is here

| Archived file | Original location | Produced |
|---|---|---|
| `seed-demo.sql` | `infrastructure/scripts/` | Demo tenants, applications, database assets and scope data |
| `seed-hr-system.sql` | `infrastructure/scripts/` | Curated HR employee master |
| `seed-hr-system-branches.sql` | `infrastructure/scripts/` | 2,451 HR employee records across department branches (generated — see below) |
| `seed_simulated.py` | `backend/app/entrypoints/` | Synthetic OEM telemetry: AppScan / Imperva / API-security records |
| `seed_demo_findings.py` | `backend/scripts/` | Demo findings |
| `seed_real_appscan.py` | `backend/` | Real AppScan Cloud findings |
| `seed_admin_accounts.py` | `backend/` | Tier 1–4 administrator accounts |

## Deliberately NOT archived

| File | Why it stayed |
|---|---|
| `infrastructure/scripts/init-db.sql` | **Schema, not seed.** Idempotent DDL. A fresh environment needs it. Also carries the `identity.employment_identifier` backfill |
| `backend/_create_tables.py` | Legacy schema migration (`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN`), not seed data |

## Consequences to be aware of

**1. `docker-compose.remote.yml` no longer provisions a fresh environment.**
It mounted `seed-hr-system.sql` and `seed-hr-system-branches.sql` into
`/docker-entrypoint-initdb.d/`. Those mounts are now commented out. Re-enable
them by pointing at this folder:

```yaml
- ./_archive/seeded/seed-hr-system.sql:/docker-entrypoint-initdb.d/02-seed-hr.sql
- ./_archive/seeded/seed-hr-system-branches.sql:/docker-entrypoint-initdb.d/03-seed-hr-branches.sql
```

**2. `backend/scripts/gen_hr_branch_employees.py` still writes to the old path.**
Its output target was not changed. Update `OUT` if you regenerate.

**3. Several documents still instruct operators to run these scripts.**
`docs/TEST_PLAN.md`, `docs/DEMO_PLAN.md`, `docs/MANUAL_TEST_PLAN.md`,
`docs/SITA_Platform_System_Documentation.md` and `docs/DEPLOYMENT_PLAN.md`
reference the pre-archive paths. Those references are now historical — pointing
at this folder if you need to reproduce a seeded environment.

**4. `seed_admin_accounts.py` is the provenance record for the live
high-privilege accounts.** `sita.superadmin@sita.co.za` and
`client.superadmin@gov.za` were created by it, holding estate-wide
`transversal-admin` scope. See also `docs/admin_credentials.md`, which records
their passwords in plaintext and should be rotated and removed.