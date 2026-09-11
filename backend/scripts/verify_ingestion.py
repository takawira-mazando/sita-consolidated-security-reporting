#!/usr/bin/env python3
"""
Verify AppScan ingestion by calling the FastAPI endpoints.
Run after seeding/ingesting to confirm data flows to frontend.
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta

import httpx

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')



API_BASE = "http://localhost:8000/api/v1"


async def get_token(email: str = "admin@example.com", password: str = "admin123") -> str:
    """Get JWT token for authenticated endpoints."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def test_public_summary():
    """Test public summary endpoint (no auth required)."""
    print("\n🔍 Testing /public/summary...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/public/summary")
        resp.raise_for_status()
        data = resp.json()
        print(f"   Total findings: {data['findings']['total']}")
        print(f"   Open findings: {data['findings']['open']}")
        print(f"   By severity: {data['findings']['by_severity']}")
        return data


async def test_findings_list(token: str):
    """Test findings list with filters."""
    print("\n🔍 Testing /findings (appscan, size=10)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/findings",
            params={"source": "appscan", "size": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"   Total: {data['total']}")
        print(f"   Page: {data['page']}/{data['pages']}")
        print(f"   Items returned: {len(data['items'])}")
        if data["items"]:
            item = data["items"][0]
            print(f"   Sample: {item['app_name']} | {item['severity']} | {item['title'][:50]}...")
        return data


async def test_findings_by_severity(token: str):
    """Test findings filtered by severity."""
    print("\n🔍 Testing /findings?severity=critical...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/findings",
            params={"source": "appscan", "severity": "critical", "size": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"   Critical findings: {data['total']}")
        return data


async def test_fix_rate(token: str):
    """Test fix rate metric."""
    print("\n🔍 Testing /metrics/fix-rate...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/metrics/fix-rate",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"   Fix rate: {data.get('fix_rate', 'N/A')}%")
        return data


async def test_waf_summary(token: str):
    """Test WAF summary."""
    print("\n🔍 Testing /metrics/waf-summary...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/metrics/waf-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"   Total WAF blocks: {data.get('total', 0)}")
        print(f"   By type: {data.get('by_type', [])}")
        return data


async def test_api_exposure(token: str):
    """Test API exposure metric."""
    print("\n🔍 Testing /metrics/api-exposure...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/metrics/api-exposure",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"   Total endpoints: {data.get('total', 0)}")
        print(f"   Shadow APIs: {data.get('shadow_total', 0)}")
        return data


async def main():
    print("=" * 60)
    print("SITA Platform - AppScan Ingestion Verification")
    print("=" * 60)

    # Test public endpoint first (no auth)
    try:
        await test_public_summary()
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return 1

    # Get auth token
    try:
        token = await get_token()
        print(f"\n🔐 Got auth token: {token[:20]}...")
    except Exception as e:
        print(f"   ❌ Auth failed: {e}")
        return 1

    # Test authenticated endpoints
    tests = [
        test_findings_list,
        test_findings_by_severity,
        test_fix_rate,
        test_waf_summary,
        test_api_exposure,
    ]

    passed = 0
    for test in tests:
        try:
            await test(token)
            passed += 1
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} endpoint tests passed")
    print("=" * 60)

    if passed == len(tests):
        print("✅ All checks passed! Dashboard should display data.")
        return 0
    else:
        print("⚠️  Some checks failed. Check backend logs.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))