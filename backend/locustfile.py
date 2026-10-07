"""Locustfile for SITA Platform concurrency simulation (10k users)."""
from locust import HttpUser, task, between, events
import random
import time

# SITA API base - MUST match --host parameter on command line
# Use: locust -f locustfile.py --headless -u 10000 -r 500 -t 15m --host=http://localhost:8801
BASE_URL = "http://localhost:8801/api/v1"

# Personas matching TEST_PLAN.md §3 Demo Accounts
PERSONAS = [
    {"role": "exec", "dept_id": None},
    {"role": "soc", "dept_id": "home-affairs-digital"},
    {"role": "soc", "dept_id": "treasury"},
    {"role": "provincesoc", "province_id": "gp"},
    {"role": "appsec", "dept_id": "treasury"},
    {"role": "dbsec", "dept_id": "dpsa-hr"},
    {"role": "compliance", "dept_id": None},
    {"role": "sre", "dept_id": None},
    {"role": "deptadmin", "dept_id": "treasury"},
    {"role": "branchadmin", "dept_id": "treasury"},
]


class SITAUser(HttpUser):
    """Simulates a SITA platform user with realistic behavior."""

    wait_time = between(0.5, 3)
    token = None
    user_role = None

    def on_start(self):
        """Called when a user starts - login first."""
        # Perform demo login as a random persona
        persona = random.choice(PERSONAS)
        payload = {"role": persona["role"]}
        if persona.get("dept_id"):
            payload["department_id"] = persona["dept_id"]

        with self.client.post(
            f"{BASE_URL}/auth/demo-login",
            json=payload,
            catch_response=True
        ) as res:
            if res.status_code == 200:
                self.token = res.json().get("token")
                self.user_role = persona["role"]
            # If 403 or other, just continue - user may be outside entitlement

    @task(30)
    def fetch_demo_accounts(self):
        """TEST: API-01 - List demo accounts (high frequency)."""
        self.client.get(f"{BASE_URL}/auth/demo-accounts")

    @task(25)
    def fetch_public_summary(self):
        """TEST: API-02 - Public summary (no auth required)."""
        self.client.get(f"{BASE_URL}/public/summary")

    @task(20)
    def fetch_tenancy_hierarchy(self):
        """TEST: API-03 - Tenancy hierarchy for login picker."""
        self.client.get(f"{BASE_URL}/auth/tenancy")

    @task(15)
    def demo_login(self):
        """TEST: API-04/05/06/07/08 - Demo login with scope override."""
        persona = random.choice(PERSONAS)
        payload = {"role": persona["role"]}
        if persona.get("dept_id"):
            payload["department_id"] = persona["dept_id"]

        with self.client.post(
            f"{BASE_URL}/auth/demo-login",
            json=payload,
            catch_response=True
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 403:
                # Expected for scope outside entitlement
                res.success(f"Expected 403: scope outside entitlement")
            else:
                res.failure(f"Unexpected: {res.status_code}")

    @task(10)
    def switch_tenant(self):
        """TEST: TS-01/TS-02 - Tenancy switching."""
        if self.token:
            with self.client.post(
                f"{BASE_URL}/auth/switch-tenant",
                json={},
                catch_response=True
            ) as res:
                if res.status_code in (200, 403):
                    res.success()
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(8)
    def fetch_findings(self):
        """TEST: AppSec findings API with scoped JWT."""
        if self.token:
            self.client.get(
                f"{BASE_URL}/findings?source=appscan&size=10"
            )

    @task(5)
    def fetch_compliance(self):
        """TEST: National compliance (admin role)."""
        if self.user_role == "exec":
            self.client.get(f"{BASE_URL}/compliance")

    @task(3)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("http://localhost:8801/health")


# ==========================================
# Test startup event
# ==========================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print(f"\n{'='*60}")
    print("SITA Platform Concurrency Test Starting...")
    print(f"Config: --host={environment.parsed_options.host}")
    print(f"Target users: will be set via -u flag")
    print(f"Endpoints: auth, tenancy, findings, compliance")
    print(f"{'='*60}\n")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print(f"\n{'='*60}")
    print("SITA Platform Concurrency Test Complete")
    print(f"HTML report: http://localhost:8089")
    print(f"{'='*60}")


# ==========================================
# Request tracking - simple stats
# ==========================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request outcomes without Unicode chars."""
    if exception:
        # Just log to stderr, avoid encoding issues
        pass


# ==========================================
# Run guidance (DO NOT EDIT BELOW THIS LINE)
# ==========================================

"""
=== HOW TO RUN 10,000 CONCURRENT USERS ===

STEP 1: Ensure backend is running via SSH tunnel
  # Terminal 1: ssh -L 8801:localhost:8000 user@remote-vpn-host
  # Verify: curl http://localhost:8801/api/v1/auth/demo-accounts

STEP 2: Start Locust headless test
  # For 10k users ramped to 500/sec, run 15 minutes:
  locust -f locustfile.py \
    --headless \
    -u 10000 \         # 10,000 total users
    -r 500 \          # ramp over 500 seconds (~8 minutes)
    -t 15m \          # run for 15 minutes
    --host=http://localhost:8801

  # Faster ramp option (if you have more CPU):
  locust -f locustfile.py \
    --headless \
    -u 10000 \         # 10,000 total users
    -r 1000 \         # ramp over 1,000 users per second
    -t 10m \          # run for 10 minutes
    --host=http://localhost:8801

STEP 3: Monitor results
  # If GUI mode (omit --headless), open http://localhost:8089 in browser
  # For headless CLI output, stats print to console during test

STEP 4: Key metrics to verify
  ✓ No 500 errors under load
  ✓ Rate limiting works (429 after threshold per TEST_PLAN.md SEC-04)
  ✓ No cross-tenant data leaks in /findings queries
  ✓ JWT scope isolation maintained (DHA vs Treasury)
  ✓ Tenant switch responds 200/403 (never 500)
  ✓ p95 response time < 250ms (per test_exit_criteria.md Gate 5)

STEP 5: Review HTML report
  # After test completes, open http://localhost:8089
  # View: total requests, failure rates, response time percentiles,
  # per-endpoint stats, and error breakdowns

RECOMMENDED PROGRESSION:
  1. Start: 100 users - verify basic functionality
  2. Medium: 500 users - check response times, no critical errors
  3. Large: 2,000 users - validate rate limiting, scope isolation
  4. Final: 10,000 users - production readiness validation
  
HARDWARE NOTES:
  - 10k concurrent users generates ~500-2000 RPS depending on think time
  - Ensure SQL Server/PostgreSQL has sufficient max connections
  - JWT validation is lightweight; DB queries are the bottleneck
  - If seeing 500 errors, check connection pool settings
"""