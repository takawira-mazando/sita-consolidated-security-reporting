"""
Seed proper admin accounts across all tenancy tiers.
Run once. Uses the system admin (admin@example.com / admin123) to bootstrap.
"""
import secrets
import string

import httpx

BASE_URL = "http://localhost:8000"

def gen_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# First login as system admin
def login_as_admin():
    r = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    r.raise_for_status()
    return r.json()["token"]

def create_user(token, email, display_name, roles, dept_ids=None, branch_ids=None, province_ids=None, password=None):
    if password is None:
        password = gen_password()
    payload = {
        "email": email,
        "display_name": display_name,
        "password": password,
        "roles": roles,
        "department_ids": dept_ids or [],
        "branch_ids": branch_ids or [],
        "province_ids": province_ids or [],
    }
    r = httpx.post(
        f"{BASE_URL}/admin/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code == 409:
        return None, password, "already exists"
    r.raise_for_status()
    return r.json(), password, "created"

def main():
    token = login_as_admin()
    print("[OK] Logged in as system admin\n")

    credentials = []

    # ─── Tier 4: System admin (already exists) ───────────────────────────────
    credentials.append({"role": "System Admin", "email": "admin@example.com", "password": "admin123 (existing)", "scope": "National Estate"})

    # ─── Tier 3: National transversal superadmins ─────────────────────────────
    accounts_t3 = [
        ("sita.superadmin@sita.co.za",       "SITA National Superadmin",    "transversal-admin", [], [], []),
        ("client.superadmin@gov.za",          "Client National Superadmin",  "transversal-admin", [], [], []),
    ]

    for email, name, role, depts, branches, provinces in accounts_t3:
        pwd = gen_password()
        _, pwd, status = create_user(token, email, name, [role], depts, branches, provinces, pwd)
        print(f"  [{status.upper()}] {email} [{role}]")
        credentials.append({"role": f"National Superadmin ({name})", "email": email, "password": pwd, "scope": "National Estate"})

    # ─── Tier 2: Dept admins (one per key national department) ───────────────
    # Key departments with real slugs from the SITA tenant catalogue
    key_depts = [
        ("home-affairs-digital",  "dha.admin@gov.za",       "DHA Dept Admin"),
        ("treasury",              "treasury.admin@gov.za",  "National Treasury Dept Admin"),
        ("justice-document",      "doj.admin@gov.za",       "DOJ Dept Admin"),
        ("health-legacy",         "health.admin@gov.za",    "Health Dept Admin"),
        ("dpsa-hr",               "dpsa.admin@gov.za",      "DPSA Dept Admin"),
        ("saps",                  "saps.admin@gov.za",      "SAPS Dept Admin"),
        ("defence",               "defence.admin@gov.za",   "Defence Dept Admin"),
        ("cogta",                 "cogta.admin@gov.za",     "COGTA Dept Admin"),
        ("communications",        "doc.admin@gov.za",       "DCDT Dept Admin"),
        ("presidency",            "presidency.admin@gov.za","Presidency Dept Admin"),
    ]

    for dept_id, email, name in key_depts:
        pwd = gen_password()
        _, pwd, status = create_user(token, email, name, ["dept-admin"], [dept_id], [], [], pwd)
        print(f"  [{status.upper()}] {email} [dept-admin -> {dept_id}]")
        credentials.append({"role": "Dept Admin", "email": email, "password": pwd, "scope": dept_id})

    # ─── Tier 1: Branch admins (one representative per tier-2 dept above) ────
    # Branches are derived from the BRANCHES dict — grab first branch per dept
    branch_accounts = [
        ("home-affairs-digital",  "dha-digital",      "dha.branch@gov.za",       "DHA Digital Branch Admin"),
        ("treasury",              "treasury-budget",  "treasury.branch@gov.za",  "Treasury Budget Branch Admin"),
        ("dpsa-hr",               "dpsa-hr-ops",      "dpsa.branch@gov.za",      "DPSA HR Ops Branch Admin"),
    ]

    for dept_id, branch_id, email, name in branch_accounts:
        pwd = gen_password()
        _, pwd, status = create_user(token, email, name, ["branch-admin"], [dept_id], [branch_id], [], pwd)
        print(f"  [{status.upper()}] {email} [branch-admin -> {branch_id}]")
        credentials.append({"role": "Branch Admin", "email": email, "password": pwd, "scope": f"{dept_id} / {branch_id}"})

    # Print credential summary
    print("\n" + "=" * 72)
    print("  ADMIN CREDENTIAL SUMMARY - store securely, rotate after first login")
    print("=" * 72)
    with open('new_credentials.txt', 'w', encoding='utf-8') as f:
        for c in credentials:
            summary = f"Role: {c['role']}\nEmail: {c['email']}\nPassword: {c['password']}\nScope: {c['scope']}\n\n"
            print(summary)
            f.write(summary)

if __name__ == "__main__":
    main()
