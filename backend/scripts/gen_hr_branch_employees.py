"""Generate simulated HR employees per branch.

Produces infrastructure/scripts/seed-hr-system-branches.sql: an idempotent
upsert adding PER_BRANCH hr.employees rows for every SITA branch (from
app.tenant.BRANCHES). Combined with the curated seed (seed-hr-system.sql), the
simulated HR system then covers every role tier (the 11 demo personas in
EMP-200x) and a small team per branch.

HR employees carry NO platform roles: the HR system only knows people,
PERSAL numbers, titles and employment status. Roles and access are assigned
solely inside the application when superadmin provisions a user from an HR
record (via /admin/users with person_id).

Run:  python scripts/gen_hr_branch_employees.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tenant import BRANCHES  # noqa: E402

# Employees per branch: the real ICT security job family used across SITA and
# its customer organs of state — an executive (GRCI), CSOC analyst, application
# + database security, GRCI compliance, security operations and IAM admin —
# i.e. the people superadmin provisions into exec, soc, appsec, dbsec,
# compliance, sre and branch-admin. The HR system stores only job titles; NO
# platform role is pre-assigned.
PER_BRANCH = 7

# Deterministic name pools (no Faker dependency). Emails are still unique
# because each local part carries the branch id and a per-branch index.
FIRST = [
    "Lerato", "Sipho", "Thandi", "Kagiso", "Naledi", "Sibusiso", "Zanele",
    "Bongani", "Ayanda", "Thabo", "Nomvula", "Sanele", "Palesa", "Lwazi",
    "Nokuthula", "Mandla", "Zinhle", "Katlego", "Nosipho", "Sizwe",
]
LAST = [
    "Dube", "Mkhize", "Ngcobo", "Khumalo", "Zulu", "Ndlovu", "Mthembu",
    "Nkosi", "Molefe", "Sithole", "Nxumalo", "Pillay", "Naidoo", "Govender",
    "Chetty", "Botha", "Venter", "Fourie", "Du Plessis", "Pretorius",
]

# Per-branch team by position n (1..7): (job_title, clearance). Positions are
# the real ICT security job family used across SITA and its customer organs of
# state (SAPS, DHA, DOD, Gauteng e-Gov, Presidency) — Executive: GRCI, the
# CSOC analyst cadre, applications/database security, GRCI compliance, security
# operations, and IAM administration. These are the people superadmin will
# provision into the platform roles (exec, soc, appsec, dbsec, compliance,
# sre, branch-admin). Purely HR data — no platform role is stored here.
TEAM = [
    ("Executive: Governance, Risk & Compliance", "top-secret"),   # n=1 -> exec
    ("CSOC Analyst", "secret"),                                   # n=2 -> soc
    ("Application Security Analyst", "confidential"),             # n=3 -> appsec
    ("Database Security Analyst", "confidential"),                # n=4 -> dbsec
    ("GRCI Compliance Officer", "confidential"),                  # n=5 -> compliance
    ("Security Operations Engineer", "confidential"),             # n=6 -> sre
    ("ICT Security Administrator (IAM)", "confidential"),         # n=7 -> branch-admin
]

# Department -> existing curated manager (FK-safe: all exist in hr.employees).
DEPARTMENT_MANAGER = {
    "treasury": "EMP-1001",
    "home-affairs-digital": "EMP-1003",
    "justice-document": "EMP-1006",
    "dpsa-hr": "EMP-1005",
    "health-legacy": "EMP-1007",
    "presidency": "EMP-1002",
}
DEFAULT_MANAGER = "EMP-1001"

OUT = Path(__file__).resolve().parents[2] / "infrastructure" / "scripts" / "seed-hr-system-branches.sql"


def initials_of(first: str, last: str) -> str:
    return f"{first[0]}{last[0]}".upper()


def main() -> int:
    rows = []
    total = 0
    for idx, (branch_id, (branch_name, dept_id)) in enumerate(sorted(BRANCHES.items()), start=1):
        branch_mgr = f"EMP-B{idx:04d}-1"
        exec_first = FIRST[(idx * 3 + 1) % len(FIRST)]
        exec_last = LAST[(idx * 7 + 1 * 11) % len(LAST)]
        exec_name = f"{exec_first} {exec_last}"
        for n in range(1, PER_BRANCH + 1):
            first = FIRST[(idx * 3 + n) % len(FIRST)]
            last = LAST[(idx * 7 + n * 11) % len(LAST)]
            display = f"{first} {last}"
            emp_no = f"EMP-B{idx:04d}-{n}"
            email = f"{first.lower()}.{last.lower()}.{branch_id}.{n}@sita-sim.local"
            mgr = branch_mgr if n > 1 else DEPARTMENT_MANAGER.get(dept_id, DEFAULT_MANAGER)
            mgr_name = exec_name if n > 1 else "Thabo Mokoena"
            job_title, clearance = TEAM[n - 1]
            rows.append(
                "('{emp}', NULL, '{title}', '{ini}', '{first}', '{last}', '{display}', '{email}',"
                " '{job}', '{org}', '{dept}', '{branch}', '{mgr}', '{mgr_name}',"
                " '012 000 {tel}', '{loc}', 'active', '{clr}', '{hire}', NULL)".format(
                    emp=emp_no,
                    title="Mr" if n % 2 else "Ms",
                    ini=initials_of(first, last),
                    first=first,
                    last=last,
                    display=display,
                    email=email,
                    job=job_title,
                    org=branch_name,
                    dept=dept_id,
                    branch=branch_id,
                    mgr=mgr,
                    mgr_name=mgr_name,
                    tel=f"{total + 1:04d}",
                    loc=branch_name,
                    clr=clearance,
                    hire=f"20{(14 + n + idx % 8):02d}-{(idx % 12) + 1:02d}-{(idx * n % 27) + 1:02d}",
                )
            )
            total += 1

    values = ",\n".join(rows)
    header = f"""-- ============================================================================
-- seed-hr-system-branches.sql - GENERATED, DO NOT EDIT BY HAND
-- {PER_BRANCH} simulated HR employees per SITA branch ({len(BRANCHES)} branches,
-- {total} employees). Regenerate with:
--   python backend/scripts/gen_hr_branch_employees.py
-- Per branch: the real SITA/government ICT security job family — Executive:
-- Governance, Risk & Compliance, CSOC Analyst, Application Security Analyst,
-- Database Security Analyst, GRCI Compliance Officer, Security Operations
-- Engineer, ICT Security Administrator (IAM). Representative HR job titles
-- only. NO platform roles are assigned at HR level — every role is provisioned
-- inside the application when superadmin creates a user.
-- Rerunnable: upserts on employee_number.
-- ============================================================================

INSERT INTO hr.employees (
    employee_number, id_number, title, initials, first_name, surname,
    display_name, email, job_title, org_unit, department_code, branch_code,
    manager_employee_number, manager_name, work_phone, location,
    employment_status, clearance_level, hire_date, termination_date
) VALUES
"""
    footer = """

ON CONFLICT (employee_number) DO UPDATE SET
    id_number               = EXCLUDED.id_number,
    title                   = EXCLUDED.title,
    initials                = EXCLUDED.initials,
    first_name              = EXCLUDED.first_name,
    surname                 = EXCLUDED.surname,
    display_name            = EXCLUDED.display_name,
    email                   = EXCLUDED.email,
    job_title               = EXCLUDED.job_title,
    org_unit                = EXCLUDED.org_unit,
    department_code         = EXCLUDED.department_code,
    branch_code             = EXCLUDED.branch_code,
    manager_employee_number = EXCLUDED.manager_employee_number,
    manager_name            = EXCLUDED.manager_name,
    work_phone              = EXCLUDED.work_phone,
    location                = EXCLUDED.location,
    employment_status       = EXCLUDED.employment_status,
    clearance_level         = EXCLUDED.clearance_level,
    hire_date               = EXCLUDED.hire_date,
    termination_date        = EXCLUDED.termination_date,
    updated_at              = now();
"""
    OUT.write_text(header + values + footer, encoding="utf-8")
    print(f"wrote {total} branch employees ({PER_BRANCH} per branch x {len(BRANCHES)} branches) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

