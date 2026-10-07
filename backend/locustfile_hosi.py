"""Locustfile for Hosi Academy LAS 100,000 user concurrency simulation.
Adapted from SITA platform principles for ASP.NET Core + SQL Server + Azure AD auth.
Target: http://192.168.101.20/hosi_las
"""
from locust import HttpUser, task, between, events
import random
import time

# TARGET: Hosi Academy LAS
# Architecture: HTTP → IIS/NGINX → ASP.NET Core → SQL Server
BASE_URL = "http://192.168.101.20/hosi_las"

# Hosi Academy LAS Roles (from the application)
# learner, mentor, HR, team-lead, academy-lead, super-admin, etc.
ROLES = [
    "learner",
    "mentor",
    "hr",
    "team-lead",
    "academy-lead",
    "super-admin",
]


class HAUser(HttpUser):
    """Concurrent user simulation for Hosi Academy LAS."""

    wait_time = between(1, 3)  # Slightly longer think time for LMS
    token = None
    user_role = None

    def on_start(self):
        """Login as a random user role."""
        self.role = random.choice(ROLES)
        payload = {"role": self.role}

        with self.client.post(
            "/api/auth/login",  # Common ASP.NET Core API pattern
            json=payload,
            catch_response=True,
            name="/api/auth/login"
        ) as res:
            if res.status_code == 200:
                body = res.json()
                self.token = body.get("accessToken") or body.get("token") or body.get("jwt")
                self.user_role = self.role
                res.success()
            elif res.status_code == 401:
                res.success("expected_401_unauthenticated")  # Some roles may not auto-login
            else:
                res.failure(f"Unexpected: {res.status_code}")

    @task(35)
    def fetch_skills_profile(self):
        """Skills profiling endpoint - core LAS feature."""
        if self.token:
            self.client.get(
                "/api/skills/profile",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name="/api/skills/profile"
            )

    @task(30)
    def course_enrolment(self):
        """Course catalogue and enrolments."""
        if self.token:
            # Different actions: view catalogue, enrol, check progress
            action = random.choice(["view", "enrol", "progress"])
            endpoints = {
                "view": "/api/courses/catalogue",
                "enrol": "/api/courses/enrol",
                "progress": "/api/courses/progress",
            }
            with self.client.get(
                endpoints[action],
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name=f"/api/courses/{action}"
            ) as res:
                if res.status_code in (200, 403, 401):
                    res.success()
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(25)
    def reporting_dashboard(self)
 Reporting endpoint - one of 12 reports across 6 categories"""
        if self.token:
            report_type = random.choice([
                "enrolments", "progress", "overdue", 
                "certification", "completion", "team-readiness"
            ])
            with self.client.get(
                f"/api/reports/{report_type}",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name=f"/api/reports/{report_type}"
            ) as res:
                if res.status_code == 200:
                    res.success()
                elif res.status_code == 403:
                    res.success("expected_403_scoped_access")
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(20)
    def certificate_verification(self)
 Certificate verification feature"""
        if self.token:
            with self.client.get(
                "/api/certificates/verify",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name="/api/certificates/verify"
            ) as res:
                if res.status_code in (200, 404):
                    res.success()
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(15)
    def hr_sync_status(self)
 HR system integration"""
        if self.user_role in ("hr", "academy-lead", "super-admin"):
            with self.client.get(
                "/api/hr/sync-status",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name="/api/hr/sync-status"
            ) as res:
                if res.status_code in (200, 403):
                    res.success()
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(10)
    def mentoring_assignments(self)
 Mentoring and at-risk support"""
        if self.token:
            with self.client.get(
                "/api/mentoring/assignments",
                headers={"Authorization": f"Bearer {self.token}"},
                catch_response=True,
                name="/api/mentoring/assignments"
            ) as res:
                if res.status_code in (200, 403):
                    res.success()
                else:
                    res.failure(f"Unexpected: {res.status_code}")

    @task(5)
    def health_check(self)
 Infrastructure health"""
        self.client.get("/hosi_las/health", catch_response=True)


# ==========================================
# Scale-aware events
# ==========================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts at scale."""
    print(f"\n{'='*70}")
    print("Hosi Academy LAS 100k User Concurrency Test Starting...")
    print(f"Target: {environment.parsed_options.host}")
    print(f"Framework: ASP.NET Core + SQL Server + Azure AD Auth")
    print(f"Roles: {', '.join(ROLES)}")
    print(f"Endpoints: skills, courses, reports, certificates, HR, mentoring")
    print(f"{'='*70}\n")
    HAUser.request_count = 0
    HAUser.error_count = 0


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print(f"\n{'='*70}")
    print("Hosi Academy LAS 100k User Concurrency Test Complete")
    print(f"HTML report: http://localhost:8089")
    print(f"{'='*70}")


# ==========================================
# Request tracking at scale
# ==========================================

request_counter = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request outcomes at scale - minimal console output."""
    global request_counter
    request_counter += 1
    if request_counter % 500 == 0:
        pass  # Suppress flood, could write to file


# ==========================================
# Run guidance for 100k users
# ==========================================

"""
=== HOW TO RUN 100,000 CONCURRENT USERS ON HOSI ACADEMY LAS ===

PREREQUISITES:

1. Target is accessible: http://192.168.101.20/hosi_las
2. API endpoints are reachable (test with curl first)
3. Azure AD authentication is configured (or test without auth)
4. SQL Server can handle concurrent connections

=== RUN COMMAND ===

# Phase 1: Baseline 10K users
locust -f locustfile_hosi.py \
  --headless \
  -u 10000 \
  -r 500 \
  -t 15m \
  --host=http://192.168.101.20

# Phase 2: Medium load 50K users
locust -f locustfile_hosi.py \
  --headless \
  -u 50000 \
  -r 1000 \
  -t 20m \
  --host=http://192.168.101.20

# Phase 3: Full 100K stress test
locust -f locustfile_hosi.py \
  --headless \
  -u 100000 \
  -r 2000 \
  -t 25m \
  --host=http://192.168.101.20

=== ANTICIPATED METRICS ===

Based on SITA platform benchmarks (10K: 373K requests, ~587 req/s):

Throughput Expectations:
  - Conservative: 300-500 req/s (SQL Server + auth overhead)
  - Aggressive: 600-800 req/s (optimized SQL, cached queries)
  - Total requests over 25min: 450K-1.2M

Response Time Targets (p95):
  - /api/skills/profile: 400-800ms (DB query intensive)
  - /api/courses/catalogue: 200-500ms (likely cached)
  - /api/reports/enrolments: 500-1000ms (12 reports, 6 categories)
  - /api/certificates/verify: 300-600ms (verification logic)
  - /hosi_las/health: 50-100ms (static page)

Error Rate Targets:
  - 500 errors: 0 (critical - must be zero)
  - 401/403: Expected for scoped role access
  - Connection errors: 0 (indicates infrastructure issue)

Infrastructure Scaling Levers (if errors appear):

1. SQL Server:
   - Increase max connections (default 100 → 300-500)
   - Enable connection pooling (SqlConnectionPooling)
   - Optimize queries, add appropriate indexes
   - Consider read replicas for reporting workloads

2. ASP.NET Core:
   - Increase Kestrel server limits (limits.maxconnections)
   - Add Output Caching for repeated reports
   - Implement Response Compression
   - Use IMemoryCache for skills profile data

3. Authentication:
   - Azure AD token validation caching
   - Reduce JWT validation overhead
   - Token refresh intervals optimization

4. Web Server (IIS/NGINX):
   - Increase max concurrent requests
   - tune keep-alive connections
   - Cache static assets (the LAS page is mostly server-rendered)

=== VALIDATION CHECKLIST ===

✅ Pre-test:
  [ ] Target http://192.168.101.20/hosi_las accessible
  [ ] API baseline: curl -X POST http://192.168.101.20/hosi_las/api/auth/login -H "Content-Type: application/json" -d '{"role":"learner"}'
  [ ] No 500 errors in manual API testing
  [ ] SQL Server max_connections ≥ 300
  [ ] Azure AD app registration configured (if using auth)

✅ During test:
  [ ] Monitor SQL Server connections: ss -n | find "1433" or SQL Server DMVs
  [ ] Track Kestrel/IIS request queue length
  [ ] Watch for 500 error spikes in Locust output
  [ ] Verify role-based access (403 for unauthenticated roles)
  [ ] Confirm report endpoints return data (not 500)

✅ Post-test:
  [ ] HTML report at http://localhost:8089
  [ ] Total requests vs. 10K baseline comparison
  [ ] Response time percentile analysis (p50, p95, p99)
  [ ] Error category breakdown (500, 401, 403, connection)
  [ ] SQL Server connection utilization report
  [ ] Recommendations for .NET/LMS hardening

=== TROUBLESHOOTING GUIDE ===

SYMPTOM: "500 Internal Server Error" for all users
FIX:
  1. Check SQL Server is running and accessible
  2. Verify max_connections setting
  3. Check Kestrel logs for connection pool exhaustion
  4. Test API endpoint manually outside Locust
  5. Reduce concurrent users to identify breaking point

SYMPTOM: "401 Unauthorized" for all users
FIX:
  1. Azure AD token validation may be misconfigured
  2. Test with minimal auth header: Authorization: Bearer <token>
  3. Or disable auth temporarily for testing (add [AllowAnonymous] attribute)
  4. Remember to re-enable before production

SYMPTOM: Response times degrade as test progresses
FIX:
  1. SQL Server connection pool exhaustion
  2. Query plan cache invalidation
  3. Add Read Committed Snapshot Isolation (RCSI)
  4. Implement proper indexing on frequently queried columns
  5. Add OutputCache attributes on report endpoints

SYMPTOM: Role-based access not working (all users see same data)
FIX:
  1. JWT token may not contain role claims
  2. Check Azure AD app role configuration
  3. Verify the API correctly reads role from token
  4. Test with different user roles explicitly

RECOMMENDED HARDWARE FOR 100K LOCAL TEST:
- 8+ CPU cores (dedicate 4 for Docker/IIS, 4 for host)
- 16+ GB RAM (8G for containers/minimum, 16G recommended)
- SQL Server with dedicated CPU core, 4GB+ RAM minimum
- SSD storage for tempdb and user databases (critical for concurrent queries)

NOTE: The Hosi Academy LAS is a .NET enterprise LMS.
Expected behavior at 100k users:
- Role-scoped data access (learners see own data, admins see all)
- Report generation under load (12 reports × 6 categories)
- HR sync and mentoring features under concurrent access
- Certificate verification workflow stress testing
- Azure AD auth should handle the load with proper caching
"""