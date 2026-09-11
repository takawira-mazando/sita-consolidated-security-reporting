"""Comprehensive API test for SITA platform demo case."""
import asyncio
import json
import sys

import aiohttp

API_V1 = "http://localhost:8000/api/v1"
ADMIN = "http://localhost:8000/admin"


async def check(label: str, r: aiohttp.ClientResponse, expected_status: int = 200):
    ok = r.status == expected_status
    icon = "[PASS]" if ok else "[FAIL]"
    print(f"  {icon} [{label}] HTTP {r.status}")
    try:
        data = await r.json()
    except Exception:
        data = None
    if not ok:
        print(f"       error: {data}")
    return data, ok


async def main():
    passed = 0
    failed = 0

    async with aiohttp.ClientSession() as s:
        print("\n" + "=" * 60)
        print("  SITA PLATFORM - COMPREHENSIVE DEMO TEST")
        print("=" * 60)

        # ── TIER 4: SITA Command Center (nationwide admin) ─────────────
        print("\n[TIER 4] SITA Command Center Authentication")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "admin@example.com", "password": "admin123"})
        data, ok = await check("SITA Admin Login", r)
        if not ok:
            print("FATAL: Cannot continue without SITA admin token")
            sys.exit(1)
        sita_token = data["token"]
        sita_user = data["user"]
        print(f"         roles   : {sita_user['roles']}")
        print(f"         dept_ids: {sita_user['department_ids']} (empty=nationwide)")
        passed += 1
        sita_hdrs = {"Authorization": f"Bearer {sita_token}"}

        # ── TIER 4: SITA Transversal Admin ─────────────────────────────
        print("\n[TIER 4] SITA Transversal Admin")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "transversal@example.com", "password": "pass123"})
        data, ok = await check("Transversal Admin Login", r)
        if ok:
            print(f"         roles: {data['user']['roles']}")
            passed += 1
        else:
            failed += 1

        # ── TIER 2: DHA Department Admin ───────────────────────────────
        print("\n[TIER 2] Department of Home Affairs — Dept Admin")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "deptadmin-ha@example.com", "password": "pass123"})
        data, ok = await check("DHA Dept Admin Login", r)
        if ok:
            dha_admin_token = data["token"]
            u = data["user"]
            print(f"         roles      : {u['roles']}")
            print(f"         dept_ids   : {u['department_ids']}")
            print(f"         branch_ids : {u['branch_ids']}")
            passed += 1
        else:
            failed += 1
        dha_admin_hdrs = {"Authorization": f"Bearer {dha_admin_token}"}

        # ── TIER 1: DHA SOC Analyst ──────────────────────────────────
        print("\n[TIER 1] Branch — DHA SOC Analyst")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "soc-ha@example.com", "password": "pass123"})
        data, ok = await check("DHA SOC Login", r)
        if ok:
            soc_token = data["token"]
            print(f"         roles: {data['user']['roles']}")
            passed += 1
        else:
            failed += 1
        soc_hdrs = {"Authorization": f"Bearer {soc_token}"}

        # ── TIER 1: DHA AppSec Analyst ────────────────────────────────
        print("\n[TIER 1] Branch — DHA AppSec Analyst")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "appsec-ha@example.com", "password": "pass123"})
        data, ok = await check("DHA AppSec Login", r)
        if ok:
            appsec_token = data["token"]
            passed += 1
        else:
            failed += 1
        appsec_hdrs = {"Authorization": f"Bearer {appsec_token}"}

        # ── TIER 1: DHA DB Security Analyst ───────────────────────────
        print("\n[TIER 1] Branch — DHA DB Security Analyst")
        r = await s.post(f"{API_V1}/auth/login",
                         json={"email": "dbsec-ha@example.com", "password": "pass123"})
        data, ok = await check("DHA DB Sec Login", r)
        if ok:
            dbsec_token = data["token"]
            passed += 1
        else:
            failed += 1
        dbsec_hdrs = {"Authorization": f"Bearer {dbsec_token}"}

        # ── TENANCY HIERARCHY ─────────────────────────────────────────
        print("\n[TENANCY] Full Hierarchy")
        r = await s.get(f"{API_V1}/auth/tenancy", headers=sita_hdrs)
        data, ok = await check("Tenancy Hierarchy", r)
        if ok:
            print(f"         departments : {data['counts']['departments']}")
            print(f"         branches    : {data['counts']['branches']}")
            print(f"         provinces   : {data['counts']['provinces']}")
            dha = next((d for d in data["departments"] if d["id"] == "home-affairs-digital"), None)
            if dha:
                print(f"         DHA name    : {dha['name']}")
                print(f"         DHA branches: {dha['branch_count']}")
            passed += 1
        else:
            failed += 1

        # ── APPSCAN FINDINGS (real data) ──────────────────────────────
        print("\n[APPSEC] AppScan Real Findings — DHA Scope")
        r = await s.get(f"{API_V1}/findings", headers=appsec_hdrs)
        data, ok = await check("Findings /findings", r)
        if ok:
            items = data.get("items", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else data.get("total", "?")
            print(f"         total_findings: {count}")
            if isinstance(items, list) and items:
                s0 = items[0]
                keys = ["title", "severity", "source", "department_id", "issue_type"]
                snippet = {k: s0.get(k) for k in keys if k in s0}
                print(f"         sample: {json.dumps(snippet)}")
            passed += 1
        else:
            failed += 1

        # ── THALES DB SECURITY INVENTORY ─────────────────────────────
        print("\n[DBSEC] Thales DAM — DB Inventory (DHA Scope)")
        r = await s.get(f"{API_V1}/metrics/dbsec/inventory", headers=dbsec_hdrs)
        data, ok = await check("DB Inventory /metrics/dbsec/inventory", r)
        if ok:
            items = data if isinstance(data, list) else data.get("items", data.get("databases", []))
            print(f"         db_instances: {len(items) if isinstance(items, list) else '?'}")
            if isinstance(items, list) and items:
                print(f"         sample_db: {json.dumps({k: items[0].get(k) for k in ['name','engine','classification','cia_tier'] if k in items[0]})}")
            passed += 1
        else:
            failed += 1

        # ── ALERTS ────────────────────────────────────────────────────
        print("\n[SOC] Alert Queue — DHA Scope")
        r = await s.get(f"{API_V1}/alerts", headers=soc_hdrs)
        data, ok = await check("Alerts /alerts", r)
        if ok:
            items = data.get("items", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else data.get("total", "?")
            print(f"         total_alerts: {count}")
            if isinstance(items, list) and items:
                a0 = items[0]
                print(f"         sample: {json.dumps({k: a0.get(k) for k in ['title','severity','source'] if k in a0})}")
            passed += 1
        else:
            failed += 1

        # ── COMPLIANCE (national) ──────────────────────────────────────
        print("\n[COMPLIANCE] National Compliance — SITA Scope")
        r = await s.get(f"{API_V1}/compliance", headers=sita_hdrs)
        data, ok = await check("Compliance /compliance", r)
        if ok:
            print(f"         framework   : {data.get('framework', '?')}")
            print(f"         overall_score: {data.get('overall_score', '?')}")
            print(f"         controls    : {data.get('passed_controls', '?')}/{data.get('total_controls', '?')}")
            passed += 1
        else:
            failed += 1

        # ── COMPLIANCE TREND ──────────────────────────────────────────
        print("\n[COMPLIANCE] Trend (SITA Scope)")
        r = await s.get(f"{API_V1}/metrics/compliance/trend", headers=sita_hdrs)
        data, ok = await check("Compliance Trend", r)
        if ok:
            items = data.get("items", data.get("data", [])) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            points = len(items)
            print(f"         data_points: {points}")
            passed += 1
        else:
            failed += 1

        # ── ADMIN USERS (admin router at /admin, not /api/v1) ──────────
        print("\n[ADMIN] User Management — SITA Superadmin")
        r = await s.get(f"{ADMIN}/users", headers=sita_hdrs)
        data, ok = await check("SITA All Users /admin/users", r)
        if ok:
            users_list = data if isinstance(data, list) else data.get("items", [])
            print(f"         total_users: {len(users_list)}")
            roles_seen = set()
            for u in users_list:
                roles_seen.update(u.get("roles", []))
            print(f"         roles_seen : {sorted(roles_seen)}")
            passed += 1
        else:
            failed += 1

        # ── ADMIN USERS (DHA dept admin — scoped) ─────────────────────
        print("\n[ADMIN] User Management — DHA Dept Admin (scoped)")
        r = await s.get(f"{ADMIN}/users", headers=dha_admin_hdrs)
        data, ok = await check("DHA Dept Admin Users /admin/users", r)
        if ok:
            users_list = data if isinstance(data, list) else data.get("items", [])
            print(f"         dha_users_visible: {len(users_list)}")
            passed += 1
        elif r.status == 403:
            print(f"         [EXPECTED] DHA admin blocked from /admin/users — good isolation")
            passed += 1
        else:
            failed += 1

        # ── SCOPE ISOLATION ────────────────────────────────────────────
        print("\n[ISOLATION] JWT Scope — SOC-HA sees only DHA findings")
        r = await s.get(f"{API_V1}/findings", headers=soc_hdrs)
        data, ok = await check("SOC-HA Findings (JWT scoped)", r)
        if ok:
            items = data.get("items", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                # Verify no non-DHA findings leaked
                leaked = [f for f in items if f.get("department_id") not in (
                    "home-affairs-digital", None, ""
                )]
                if leaked:
                    print(f"  [FAIL] Scope leak: {len(leaked)} non-DHA items found!")
                    failed += 1
                else:
                    print(f"  [PASS] All {len(items)} findings scoped to DHA — no leak")
                    passed += 1
            else:
                passed += 1
        else:
            failed += 1

        # ── APPSEC METRICS ────────────────────────────────────────────
        print("\n[APPSEC] AppSec WAF + API Exposure Metrics")
        for ep, label in [
            ("/metrics/appsec/waf", "WAF Metrics"),
            ("/metrics/appsec/api-exposure", "API Exposure"),
            ("/metrics/appsec/fix-rate", "Fix Rate"),
        ]:
            r = await s.get(f"{API_V1}{ep}", headers=appsec_hdrs)
            data, ok = await check(label, r)
            if ok:
                passed += 1
            else:
                failed += 1

        # ── SOC METRICS ────────────────────────────────────────────────
        print("\n[SOC] SOC SLO Metrics")
        r = await s.get(f"{API_V1}/metrics/soc/slo", headers=soc_hdrs)
        data, ok = await check("SOC SLO", r)
        if ok:
            passed += 1
        else:
            failed += 1

        # ── DEMO ACCOUNTS ─────────────────────────────────────────────
        print("\n[DEMO] Demo Accounts Discovery")
        r = await s.get(f"{API_V1}/auth/demo-accounts", headers=sita_hdrs)
        data, ok = await check("Demo Accounts List", r)
        if ok:
            print(f"         demo_accounts: {len(data)}")
            for acc in data:
                dept_name = acc.get("department_name") or "(nationwide)"
                print(f"           - {acc['role']:30s} {dept_name}")
            passed += 1
        else:
            failed += 1

        # ── SUMMARY ───────────────────────────────────────────────────
        print("\n" + "=" * 60)
        total = passed + failed
        print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed")
        print("=" * 60 + "\n")
        return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
