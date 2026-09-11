===============================================================================
                         BANTU INFOTECH (B.iT)
                   Pretoria, Gauteng, South Africa
                          TAX INVOICE
===============================================================================

Invoice No:       INV-2026-007
Date Issued:      31 August 2026
Prepared By:      Takawira Mazando
Email:            takawira.mazando@entailabs.com
Contact:          0672 319 200

BILL TO:
  Attn:            Koketso Molelemane
  Company:         Hosi Technologies (Pty) Ltd
                   Company ref: 2010/015030/07
                   Block A, 2nd Floor, The Pivot, Fourways, Johannesburg
  Email:           koketso@hosi.co.za
  Phone:           +27 11 023 1995

SUBJECT:  Monthly Retainer Invoice - August 2026
          Independent Contractor Agreement (01 May - 30 Nov 2026)
          SITA Unified Data Managed Service Project

===============================================================================
 DELIVERABLES BREAKDOWN
===============================================================================

SECTION A - MULTI-TENANCY & GOVERNMENT TENANCY PLATFORM (Completed Aug 11-14)
-------------------------------------------------------------------------------
 #  DELIVERABLE                                                          HOURS
-------------------------------------------------------------------------------
 A1  Tenancy Data Model (Provinces, Departments, Branches)                14
     - Full government tenancy catalog: 9 provinces, 43 national + 113
       provincial departments (156 public clients), 347 DDG-led branches
     - Province->Department->Branch->App hierarchy
     - warehouse.provinces/departments/branches tables (init-db.sql)
     - Additive migrations _migrate_tenancy.py, _migrate_province.py
     - ORM models: models/tenant.py, person.py, user.py

 A2  API-Level Tenant Filtering & Data Isolation (RLS)                     10
     - tenant_filter(claims, model) in backend/app/api/auth.py
     - SQLAlchemy dept/branch IN predicates; province scope auto-expands
       to full department set; fail-closed false() when scoped role
       has no scope; nationwide roles unscoped see whole estate
     - Wired into findings, risks, alerts, exports, dashboard, metrics,
       benchmark, admin(person) routers; province peer leaderboard
       returns blinded peers (benchmark.py)

 A3  Tenancy-Aware JWT Authentication Scopes                               6
     - JWTClaims (auth.py) carries department_ids/branch_ids/province_ids
     - verify_token validates Auth0 RS256 or HS256 and hydrates scopes
     - require_roles permission matrix (ROLES_HIERARCHY)
     - scope_covers() enforces subset + tenancy consistency
     - Demo personas bound to scope (provincesoc@example.com = Gauteng,
       deptadmin = Treasury, branchadmin = Treasury/ICT, transversal = estate)
     - Public GET /tenancy hierarchy endpoint for login scope picker

 A4  Delegated Role-Based Access Control (RBAC) Logic                      8
     - Delegated RBAC on tenant tree (tenant.py): 4 tiers
       admin(4) estate root -> transversal-admin(3) -> dept-admin/
       province-dept-admin(2) -> branch-admin(1)
     - GRANTABLE_ROLES derives each tier's grant set
     - can_manage() (auth.py) enforces strict one-way-down delegation
       on roles + scope
     - admin.py user create/update/delete runs _validate_roles/
       _validate_scope then can_manage => 403 out of authority

 A5  Frontend Scoped User Management UI (Admin Users)                      6
     - frontend/src/pages/AdminUsersPage.tsx admin user table with
       Tenant scope column (province/department/branch)
     - Scope pickers constrained to caller's subtree
     - Role picker filtered to GRANTABLE_ROLES mirror
     - RoleNav.tsx shows active tenant scope label
     - LoginPage.tsx tenancy-scoped demo login
     - api/admin.ts fetchTenancy/fetchBranches

 A6  Cross-Tenant Access Prevention & Security Auditing                    6
     - Cross-tenant prevention + immutable audit: audit.action_audit
       (actor, action, target, tenant_scope JSONB, payload_hash
       SHA-256, created_at) in init-db.sql + models/audit.py
     - AG secure export writes one immutable audit row per attestation
       binding actor + tenant scope + integrity hash (exports_ag.py)
       with /verify/{hash} endpoint
     - Prevention layered as tenant_filter (read) + can_manage (admin) +
       _tenant_consistent (scope) + blinded peer benchmark

 A7  Multi-Tenancy E2E Testing & Verification                              8
     - backend/tests/test_tenancy.py (490 lines, 8 test classes)
       tenant_filter SQL rendering, province-scope expansion, demo
       scopes, delegated-admin grant matrix, tier ordering, tenancy
       consistency, ministry/cluster lookups, person identity + HR-sync
     - Plus test_benchmark.py, test_exports_ag.py, test_new_endpoints.py
     - 128 tests passing locally; CI + GHCR green on commit a53f829

 A8  Tenancy Architecture Documentation                                    6
     - Tenancy architecture documentation: tree.html Tenancy & isolation
       button + deep-dive modal (tenancyBtn/tenancyModal) with purpose,
       tenant tree, scoping, delegated administration, DB location
     - docs/Tenancy_Stakeholder_Overview.docx (11 sections, 5 tables)
     - backend/generate_tenancy_doc.py
     - Tenancy section in docs/SITA_Platform_System_Documentation.md
       /.docx/.html
     - GitHub Project 1 issues #17-#22 marked Done (label phase: m4-tenancy)
                                                               ----
                                                                   64

SECTION B - PUBLIC ESTATE & AUTHENTICATION ENHANCEMENTS (Completed Aug 13-14)
-------------------------------------------------------------------------------
 #  DELIVERABLE                                                          HOURS
-------------------------------------------------------------------------------
 B1  Public Estate Summary API + Landing Page                              6
     - GET /api/v1/public/summary (aggregate-only, no PII) powers the
       pre-login HomePage "Live Estate" section:
       open findings by severity, risk distribution, top risky apps,
       connector health, three-tier tenancy counts
     - test_public_summary.py

 B2  Tenancy-Aware Login & Demo Scope Enforcement                          3
     - login/demo-login resolve department/branch/province scope via
       _resolve_scope()
     - scope_covers() rejects any requested scope outside the account
       admin-set entitlement
     - Demo personas sign in with their seeded scope - nationwide =
       whole estate, dept/province personas = exact subtree

 B3  Tenant Switch Without Re-auth                                         3
     - POST /api/v1/auth/switch-tenant re-issues a JWT for a new scope
       within the user entitlement
     - Backend + frontend AuthContext.switchTenant + sessionNonce
       re-render; empty body resets to account default scope

 B4  Platform Operator Role (Tier 5)                                       2
     - "operator" managed-service creator role (ADMIN_TIERS=5): creates
       the SITA superuser (admin) and peer operators for rotation ONLY
     - GRANTABLE_ROLES operator={"admin","operator"}
     - NATIONWIDE_ROLES extended with operator

 B5  HR-Only User Provisioning                                             4
     - create_user requires person_id referencing an HR-provisioned
       employee (identity.persons)
     - Account email must match the HR record; external/non-employee
       creation path removed from UserCreate/UserUpdate
     - update_user syncs job/location fields from the HR record

 B6  Simulated HR Browse & Pull-Sync Endpoints                             3
     - GET /admin/hr/sim/employees (browse simulated master)
     - POST /admin/hr/sim/sync (pull every hr.employees row through the
       shared _upsert_hr_records pipeline - same path as live POST
       /admin/hr/sync)

 B7  Admin Users HR Employee Picker                                        3
     - AdminUsersPage.tsx create form searches HR persons (debounced
       fetchPersons, active only) and pre-fills email/display name/
       department on selection
     - Account provisioning flows completely from HR records

 B8  Admin Credentials Generation & Cleanup                                2
     - seed_admin_accounts.py provisions Tier 1-4 admins with strong
       generated passwords
     - cleanup_admins.py removes stray accounts
     - test_admin_logins.py verifies all tier logins
     - Outputs admin_credentials.md / new_credentials.txt

 B9  Frontend Security Hardening                                           2
     - DOMPurify sanitises ExplainOverlay
     - nginx-unprivileged container (port 8080, USER nginx) drops root
     - Vite proxy pinned to 127.0.0.1:8000 to fix ERR_CONNECTION_REFUSED
       on HMR reload

 B10 Role Provisioning Roadmap Documentation                               2
     - docs/Role-Provisioning-Roadmap.html - full path schematic:
       HR system -> identity.persons -> delegated admin provisioning ->
       tenant-scoped user

 B11 Tenancy & Public-Summary Test Coverage                                3
     - test_public_summary.py (public aggregate endpoint)
     - Expanded test_tenancy.py (TestResolveScope, TestDemoEntitlement,
       scope_covers, operator grant matrix, province expansion)
     - CI lint+test on push/PR
                                                               ----
                                                                   33

SECTION C - DEPLOYMENT PLANNING & DOCUMENTATION (Completed Aug 19)
-------------------------------------------------------------------------------
 #  DELIVERABLE                                                          HOURS
-------------------------------------------------------------------------------
 C1  Enhanced Detailed Deployment Plan v2.0 (Markdown)                     8
     - docs/DEPLOYMENT_PLAN.md rewritten as enriched detailed plan:
       RACI, prerequisites, phased 0-6 with expected outputs +
       validation checkpoints, troubleshooting runbook, secrets mgmt,
       day-2 runbook, backup/PITR/DR, risk register, AWS Stage C
       milestones
     - Committed + pushed to main (fc55156)

 C2  Deployment Plan - Word Document                                       4
     - docs/DEPLOYMENT_PLAN.docx - Word rendering of the enriched plan
       (cover page, metadata, 35 tables, deployment systems comparison
       with pros/cons biased to Linux)

 C3  Deployment Plan - HTML Report                                         4
     - docs/DEPLOYMENT_PLAN.html - self-contained styled HTML report
       (cover header, TOC, tables, code blocks, print-friendly)
       including the deployment systems comparison deliberately
       favouring the Linux option for Stage A
                                                               ----
                                                                   16

SECTION D - SECURITY & CODE QUALITY (Completed Aug 11-14)
-------------------------------------------------------------------------------
 #  DELIVERABLE                                                          HOURS
-------------------------------------------------------------------------------
 D1  Frontend SAST Setup & Scan (Semgrep)                                  3
     - Configuration and execution of Semgrep SAST scan on frontend

 D2  Vulnerability Remediation                                             3
     - Remediation of identified frontend vulnerabilities

 D3  Backend SAST Setup & Scan (Bandit)                                    3
     - Backend Python SAST via bandit -c pyproject.toml -r .
     - Scans backend/ (incl. app, migrations, entrypoints, dispatch,
       lake, models, routers, synthetic); 8,222 LOC scanned
     - 0 issues across all severities (Undefined/Low/Medium/High = 0)
     - Run: 2026-08-12 18:47 UTC - no issues identified
     - pyproject.toml [tool.bandit] config with #nosec skip tolerance

 D4  SITA Platform Risk Engine & Pipeline Work (Aug 1-10)                 15
     - Phase 11: Alert Dispatch & Hardening activities
     - Email adapter (SMTP) with Jinja2 HTML template
     - Teams adapter (Adaptive Card) with severity colour bar
     - PagerDuty adapter (Events v2) with criticalP1, highP2
     - Per-channel rate limiter (Redis): Critical 20/hr, High 50/hr,
       Medium 100/hr; queue overflow to next window
     - AdminPage (service_ops): ConnectorHealthTable, DeadLetterQueueTable
       with reprocess, IngestionTrendChart
     - Risk: PagerDuty alert storm mitigation (WIP - throttle + dedup
       in place; chaos engineering test planned)
                                                               ----
                                                                   24

SECTION E - UAT PREPARATION & GO-LIVE READINESS (In Progress Aug 21+)
-------------------------------------------------------------------------------
 #  DELIVERABLE                                                          HOURS
-------------------------------------------------------------------------------
 E1  User Acceptance Testing Preparation                                   8
     - UAT test case design and environment setup
     - Defect tracking and prioritization framework
     - Coordination with Alutha Vongwe, Peter

 E2  Runbook & Operations Guide (Initiated)                                6
     - Operational documentation covering deployment, monitoring,
       support, troubleshooting, escalation and recovery procedures

 E3  Security Review & Penetration Test Planning                           4
     - Security vulnerabilities assessment planning
     - Penetration testing scope definition
     - Findings remediation tracking setup

 E4  Stakeholder Demo & Training Preparation                               4
     - Demo script preparation for stakeholder walkthrough
     - Training materials for key functionality and operational processes
                                                               ----
                                                                   22

===============================================================================
                                    TOTAL HOURS:         160
                              MONTHLY RETAINER:    R60,000.00
                                       VAT: R0.00 (clause 5.5)
                                  TOTAL DUE:    R60,000.00
===============================================================================

NOTES:
  - This is a fixed-price monthly retainer of R60,000 covering 160 hours
    of work across five project areas, billed under clause 5.1.
  - No duplication of billing with previous invoices (INV-2026-001 through
    INV-2026-006).
  - Hours shown are for transparency and tracking only; retainer is flat-rate.
  - August deliverables focused on multi-tenancy platform completion,
    authentication enhancements, deployment documentation, and UAT preparation.
  - Multi-tenancy features (Section A) represent core platform capability
    enabling government-wide deployment across 9 provinces, 156 departments,
    and 347 branches with full data isolation.
  - UAT preparation (Section E) ongoing into early September per project plan.

PAYMENT DETAILS
  Method:          EFT / Bank Transfer
  Account Name:    Bantu InfoTech (Pty) Ltd
  Bank:            FNB Business Banking
  Branch Code:     250655
  Account Number:  63223253129
  Reference:       INV-2026-007 / Hosi Technologies

TERMS: Payment due on receipt. Subject to Independent Contractor
       Agreement clauses 5.1-5.6.

===============================================================================
                          Bantu InfoTech (B.iT)
                          Takawira Mazando
                          takawira.mazando@entailabs.com
                          0672 319 200
===============================================================================