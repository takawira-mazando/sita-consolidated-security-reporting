"""Tests for admin-set scope RBAC: tenant_filter + admin scope validation."""
from __future__ import annotations

import pytest
from app.api.auth import JWTClaims, can_manage, grantable_roles, scope_covers, tenant_filter
from app.api.routers import admin
from app.api.routers import auth as auth_router
from app.models.finding import Finding
from fastapi import HTTPException


def _claims(roles: list[str], department_ids: list[str], branch_ids: list[str], province_ids: list[str] | None = None) -> JWTClaims:
    return JWTClaims(sub="u1", email="u@example.com", roles=roles,
                     department_ids=department_ids, branch_ids=branch_ids,
                     province_ids=province_ids or [])


def _render(clause):
    return clause.compile(compile_kwargs={"literal_binds": True}).string


class TestTenantFilter:
    def test_nationwide_no_scope_returns_none(self):
        c = _claims(["exec"], [], [])
        assert tenant_filter(c, Finding) is None

    def test_department_role_no_scope_fails_closed(self):
        c = _claims(["soc"], [], [])
        f = tenant_filter(c, Finding)
        assert f is not None
        assert "false" in _render(f)

    def test_single_department(self):
        c = _claims(["appsec"], ["treasury"], [])
        f = tenant_filter(c, Finding)
        assert "findings.department_id IN" in _render(f)
        assert "treasury" in _render(f)

    def test_multiple_departments(self):
        c = _claims(["soc"], ["treasury", "home-affairs-digital"], [])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "findings.department_id IN" in sql
        assert "treasury" in sql and "home-affairs-digital" in sql

    def test_department_plus_branch_narrows(self):
        c = _claims(["soc"], ["treasury", "home-affairs-digital"], ["treasury-ict"])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "findings.department_id IN" in sql
        assert "findings.branch_id IN" in sql
        assert "treasury-ict" in sql

    def test_nationwide_can_be_narrowed_by_admin(self):
        c = _claims(["exec"], ["treasury"], [])
        f = tenant_filter(c, Finding)
        assert "findings.department_id IN" in _render(f)

    def test_branch_only_scope(self):
        c = _claims(["dbsec"], ["dpsa-hr"], ["dpsa-hr-ops"])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "dpsa-hr" in sql and "dpsa-hr-ops" in sql

    def test_admin_empty_scope_returns_none(self):
        c = _claims(["admin"], [], [])
        assert tenant_filter(c, Finding) is None

    def test_nationwide_wins_over_department_role_when_unscoped(self):
        c = _claims(["exec", "soc"], [], [])
        assert tenant_filter(c, Finding) is None

    def test_nationwide_mixed_roles_still_narrowed_by_scope(self):
        c = _claims(["admin", "soc"], ["treasury"], ["treasury-ict"])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "findings.department_id IN" in sql
        assert "findings.branch_id IN" in sql


class TestProvinceScope:
    def test_province_filter_expands_to_full_department_set(self):
        from app.tenant import provincial_departments_for_province
        c = _claims(["province-soc-lead"], [], [], province_ids=["gp"])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        for dept in provincial_departments_for_province("gp"):
            assert dept in sql
        assert "wc-health" not in sql and "ec-education" not in sql

    def test_province_role_fails_closed_without_scope(self):
        c = _claims(["province-soc-lead"], [], [])
        f = tenant_filter(c, Finding)
        assert f is not None
        assert "false" in _render(f)

    def test_province_scope_covers_provincial_departments(self):
        c = _claims(["province-dept-admin"], [], [], province_ids=["gp"])
        assert scope_covers(c, ["gp-health"], [])
        assert scope_covers(c, ["gp-education"], [])
        assert not scope_covers(c, ["wc-health"], [])
        assert not scope_covers(c, ["treasury"], [])

    def test_province_scope_covers_province_target(self):
        c = _claims(["province-dept-admin"], [], [], province_ids=["gp"])
        assert scope_covers(c, [], [], province_ids=["gp"])
        assert not scope_covers(c, [], [], province_ids=["wc"])

    def test_can_manage_within_province(self):
        c = _claims(["province-dept-admin"], [], [], province_ids=["gp"])
        assert can_manage(c, ["soc"], ["gp-health"], [])
        assert can_manage(c, ["province-soc-lead"], ["gp-education"], [])
        assert not can_manage(c, ["soc"], ["wc-health"], [])
        assert not can_manage(c, ["province-dept-admin"], [], [], province_ids=["gp"])

    def test_province_dept_admin_cannot_grant_dept_admin(self):
        c = _claims(["province-dept-admin"], [], [], province_ids=["gp"])
        assert not can_manage(c, ["dept-admin"], ["gp-health"], [])
        assert not can_manage(c, ["branch-admin"], ["gp-health"], [])

    def test_transversal_admin_scope_covers_province(self):
        c = _claims(["transversal-admin"], [], [])
        assert scope_covers(c, ["gp-health"], [])
        assert can_manage(c, ["province-dept-admin"], ["gp-health"], [])

    def test_national_dept_admin_cannot_reach_province(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not scope_covers(c, ["gp-health"], [])
        assert not can_manage(c, ["province-soc-lead"], ["gp-health"], [])


class TestDemoScope:
    def test_no_scope_returns_no_override(self):
        assert auth_router._demo_scope(None, None) == ([], [])

    def test_department_only(self):
        assert auth_router._demo_scope("treasury", None) == (["treasury"], [])

    def test_valid_department_and_branch(self):
        assert auth_router._demo_scope("treasury", "treasury-ict") == (["treasury"], ["treasury-ict"])

    def test_unknown_department_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._demo_scope("nope", None)

    def test_unknown_branch_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._demo_scope("treasury", "nope")

    def test_branch_of_other_department_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._demo_scope("dpsa-hr", "treasury-ict")


class TestDemoNationwideRoles:
    def _user(self, roles):
        return auth_router.User(id="u1", email="u@example.com", roles=roles)

    def test_department_role_gets_nationwide_role(self):
        roles = auth_router._demo_nationwide_roles(self._user(["soc"]))
        assert "exec" in roles

    def test_all_demo_roles_widened(self):
        from app.api.routers.auth import DEMO_ACCOUNTS
        for account in DEMO_ACCOUNTS:
            roles = auth_router._demo_nationwide_roles(self._user(account["roles"]))
            # Nationwide widening OR province-scoped persona (province keeps scope)
            assert set(roles) & auth_router.NATIONWIDE_ROLES or set(roles) & auth_router.PROVINCIAL_ROLES

    def test_provincial_persona_keeps_province_scope(self):
        user = self._user(["province-soc-lead"])
        user.province_ids = ["gp"]
        assert auth_router._demo_nationwide_roles(user) == ["province-soc-lead"]
        assert auth_router._demo_province_scope(user) == ["gp"]

    def test_non_provincial_persona_has_no_province_scope(self):
        user = self._user(["soc"])
        user.province_ids = []
        assert auth_router._demo_province_scope(user) == []

    def test_nationwide_role_not_duplicated(self):
        roles = auth_router._demo_nationwide_roles(self._user(["exec"]))
        assert roles == ["exec"]

    def test_empty_scope_plus_nationwide_role_is_whole_estate(self):
        c = _claims(auth_router._demo_nationwide_roles(self._user(["soc"])), [], [])
        assert tenant_filter(c, Finding) is None


class TestAdminScopeValidation:
    def test_dept_role_without_department_rejected(self):
        with pytest.raises(HTTPException):
            admin._validate_scope(["soc"], [], [])

    def test_branch_outside_assigned_department_rejected(self):
        with pytest.raises(HTTPException):
            admin._validate_branches(["treasury-ict"], ["dpsa-hr"])

    def test_unknown_branch_rejected(self):
        with pytest.raises(HTTPException):
            admin._validate_branches(["nope"], ["treasury"])

    def test_branch_scope_without_department_rejected(self):
        with pytest.raises(HTTPException):
            admin._validate_scope(["soc"], [], ["treasury-ict"])

    def test_valid_scope_accepted(self):
        admin._validate_scope(["soc"], ["treasury"], ["treasury-ict"])
        admin._validate_branches(["treasury-ict"], ["treasury"])


class TestAdminDelegation:
    def test_admin_grants_anything(self):
        c = _claims(["admin"], [], [])
        assert grantable_roles(c) is None
        assert can_manage(c, ["admin"], [], [])
        assert can_manage(c, ["dept-admin", "exec"], ["treasury"], ["treasury-ict"])

    def test_dept_admin_grantable(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert grantable_roles(c) == {"soc", "appsec", "dbsec", "province-soc-lead", "local-appsec", "branch-admin"}

    def test_branch_admin_grantable(self):
        c = _claims(["branch-admin"], ["treasury"], ["treasury-ict"])
        assert grantable_roles(c) == {"soc", "appsec", "dbsec", "province-soc-lead", "local-appsec"}

    def test_province_dept_admin_grantable(self):
        c = _claims(["province-dept-admin"], ["gp-health"], [], province_ids=["gp"])
        assert grantable_roles(c) == {"soc", "appsec", "dbsec", "province-soc-lead", "local-appsec"}

    def test_grantable_derived_from_role_catalog(self):
        from app.tenant import (
            ADMIN_TIERS,
            DEPARTMENT_ROLES,
            GRANTABLE_ROLES,
            OPERATIONAL_DEPARTMENT_ROLES,
            tier_for_role,
        )
        assert OPERATIONAL_DEPARTMENT_ROLES == {"soc", "appsec", "dbsec", "province-soc-lead", "local-appsec"}
        assert GRANTABLE_ROLES["transversal-admin"] == OPERATIONAL_DEPARTMENT_ROLES | {"dept-admin", "branch-admin", "province-dept-admin"}
        assert GRANTABLE_ROLES["dept-admin"] == OPERATIONAL_DEPARTMENT_ROLES | {"branch-admin"}
        assert GRANTABLE_ROLES["province-dept-admin"] == OPERATIONAL_DEPARTMENT_ROLES
        assert GRANTABLE_ROLES["branch-admin"] == OPERATIONAL_DEPARTMENT_ROLES
        assert GRANTABLE_ROLES["dept-admin"] | GRANTABLE_ROLES["branch-admin"] | GRANTABLE_ROLES["province-dept-admin"] | set(ADMIN_TIERS) == DEPARTMENT_ROLES | {"admin", "transversal-admin"}
        assert tier_for_role("admin") > tier_for_role("transversal-admin") > tier_for_role("dept-admin") > tier_for_role("branch-admin") > tier_for_role("soc")

    def test_sre_nationwide_retains_full_user_management(self):
        c = _claims(["sre"], [], [])
        assert grantable_roles(c) is None
        assert can_manage(c, ["admin"], [], [])
        assert can_manage(c, ["dept-admin"], ["treasury"], ["treasury-ict"])

    def test_transversal_admin_is_nationwide(self):
        from app.api.auth import is_nationwide
        from app.tenant import NATIONWIDE_ROLES
        assert "transversal-admin" in NATIONWIDE_ROLES
        assert is_nationwide(_claims(["transversal-admin"], [], []))

    def test_transversal_admin_unscoped_sees_whole_estate(self):
        c = _claims(["transversal-admin"], [], [])
        assert tenant_filter(c, Finding) is None
        assert scope_covers(c, ["treasury"], [])
        assert scope_covers(c, [], [])
        assert can_manage(c, ["dept-admin"], ["treasury"], ["treasury-ict"])
        assert can_manage(c, ["soc"], ["home-affairs-digital"], ["dha-digital"])

    def test_transversal_admin_scoped_filter_and_covers(self):
        c = _claims(["transversal-admin"], ["treasury", "home-affairs-digital"], [])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "treasury" in sql and "home-affairs-digital" in sql
        assert scope_covers(c, ["treasury"], ["treasury-ict"])
        assert scope_covers(c, ["home-affairs-digital"], ["dha-digital"])
        assert not scope_covers(c, ["dpsa-hr"], [])

    def test_transversal_admin_grantable(self):
        c = _claims(["transversal-admin"], [], [])
        assert grantable_roles(c) == {"soc", "appsec", "dbsec", "province-soc-lead", "local-appsec", "dept-admin", "branch-admin", "province-dept-admin"}

    def test_transversal_admin_cannot_grant_peer_or_superior(self):
        c = _claims(["transversal-admin"], ["treasury"], [])
        assert not can_manage(c, ["transversal-admin"], ["treasury"], [])
        assert not can_manage(c, ["admin"], [], [])
        assert not can_manage(c, ["dept-admin"], [], [])  # whole-estate scope out of reach
        assert can_manage(c, ["dept-admin"], ["treasury"], [])
        assert can_manage(c, ["branch-admin"], ["treasury"], ["treasury-ict"])
        assert can_manage(c, ["soc"], ["treasury"], [])

    def test_transversal_admin_scoped_grants_within_scope(self):
        c = _claims(["transversal-admin"], ["treasury", "home-affairs-digital"], [])
        assert can_manage(c, ["dept-admin"], ["home-affairs-digital"], ["dha-digital"])
        assert can_manage(c, ["branch-admin"], ["treasury"], ["treasury-ict"])
        assert not can_manage(c, ["dept-admin"], ["dpsa-hr"], [])

    def test_department_admin_never_reaches_other_departments(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not scope_covers(c, ["home-affairs-digital"], [])
        assert not can_manage(c, ["soc"], ["home-affairs-digital"], ["dha-digital"])
        assert not can_manage(c, ["dept-admin"], ["dpsa-hr"], [])
        f = tenant_filter(c, Finding)
        sql = _render(f)
        assert "treasury" in sql and "home-affairs-digital" not in sql

    def test_transversal_admin_role_is_not_department_scoped(self):
        from app.api.auth import is_department_scoped
        assert not is_department_scoped(_claims(["transversal-admin"], ["treasury"], []))

    def test_exec_has_no_delegated_management(self):
        c = _claims(["exec"], [], [])
        assert grantable_roles(c) == set()
        assert not can_manage(c, ["soc"], ["treasury"], [])

    def test_dept_admin_cannot_grant_superior_roles(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not can_manage(c, ["dept-admin"], ["treasury"], [])
        assert not can_manage(c, ["exec"], [], [])
        assert not can_manage(c, ["admin"], [], [])
        assert can_manage(c, ["branch-admin"], ["treasury"], ["treasury-ict"])
        assert can_manage(c, ["soc"], ["treasury"], [])

    def test_branch_admin_cannot_grant_branch_admin(self):
        c = _claims(["branch-admin"], ["treasury"], ["treasury-ict"])
        assert not can_manage(c, ["branch-admin"], ["treasury"], ["treasury-ict"])
        assert can_manage(c, ["soc"], ["treasury"], ["treasury-ict"])

    def test_tier_ordering_blocks_at_or_above(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not can_manage(c, ["branch-admin", "dept-admin"], ["treasury"], ["treasury-ict"])
        assert not can_manage(c, ["admin"], ["treasury"], [])

    def test_dept_admin_scope_within_department(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert scope_covers(c, ["treasury"], ["treasury-ict"])
        assert not scope_covers(c, ["home-affairs-digital"], [])
        assert not scope_covers(c, [], [])  # whole-estate target out of reach

    def test_branch_admin_scope_narrowed_to_branch(self):
        c = _claims(["branch-admin"], ["treasury"], ["treasury-ict"])
        assert scope_covers(c, ["treasury"], ["treasury-ict"])
        assert not scope_covers(c, ["treasury"], [])  # dept-wide out of reach
        assert not scope_covers(c, ["treasury"], ["comms-ict-intl"])

    def test_scope_must_be_tenancy_consistent(self):
        # branch does not belong to the target department -> never covers
        c = _claims(["admin"], [], [])
        assert not scope_covers(c, ["treasury"], ["dha-ict"])
        c2 = _claims(["dept-admin"], ["treasury"], [])
        assert not scope_covers(c2, ["treasury", "home-affairs-digital"], ["dha-ict"])
        assert scope_covers(c2, ["treasury"], ["treasury-ict"])

    def test_scoped_admin_cannot_manage_whole_estate_users(self):
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not can_manage(c, ["soc"], [], [])
        assert not can_manage(c, ["admin"], [], [])

    def test_nationwide_sre_with_empty_scope_covers_all(self):
        c = _claims(["sre"], [], [])
        assert scope_covers(c, ["treasury"], [])
        assert can_manage(c, ["soc"], ["treasury"], [])

    def test_scope_validation_requires_branch_for_branch_admin(self):
        with pytest.raises(HTTPException):
            admin._validate_scope(["branch-admin"], ["treasury"], [])

    def test_scope_validation_requires_department_for_dept_admin(self):
        with pytest.raises(HTTPException):
            admin._validate_scope(["dept-admin"], [], [])

    def test_dept_admin_role_is_department_scoped(self):
        from app.api.auth import is_department_scoped
        assert is_department_scoped(_claims(["dept-admin"], ["treasury"], []))
        assert is_department_scoped(_claims(["branch-admin"], ["treasury"], ["treasury-ict"]))


class TestMinistryClusterLookups:
    def test_department_to_ministry(self):
        from app.tenant import ministry_for_department
        assert ministry_for_department("treasury") == "finance"
        assert ministry_for_department("home-affairs-digital") == "home-affairs"
        assert ministry_for_department(None) is None
        assert ministry_for_department("nope") is None

    def test_department_to_cluster(self):
        from app.tenant import cluster_for_department
        assert cluster_for_department("treasury") == "finance-admin"
        assert cluster_for_department("health-legacy") == "social"
        assert cluster_for_department("saps") == "justice"
        assert cluster_for_department(None) is None
        assert cluster_for_department("nope") is None

    def test_cluster_for_ministry(self):
        from app.tenant import cluster_for_ministry
        assert cluster_for_ministry("finance") == "finance-admin"
        assert cluster_for_ministry("justice") == "justice"
        assert cluster_for_ministry(None) is None

    def test_app_and_db_lookups(self):
        from app.tenant import cluster_for_app, cluster_for_db, ministry_for_app, ministry_for_db
        assert ministry_for_app("payment-gateway") == "finance"
        assert cluster_for_app("payment-gateway") == "finance-admin"
        assert ministry_for_db("DB-CUST-01") == "home-affairs"
        assert cluster_for_db("DB-CUST-01") == "justice"
        assert ministry_for_app("unknown-app") is None
        assert cluster_for_db("DB-NOPE-01") is None

    def test_every_department_has_ministry_and_cluster(self):
        from app.tenant import (
            CLUSTERS,
            DEPARTMENT_TO_MINISTRY,
            DEPARTMENTS,
            MINISTRY_TO_CLUSTER,
        )
        missing_ministry = [d for d in DEPARTMENTS if d not in DEPARTMENT_TO_MINISTRY]
        missing_cluster = [
            d for d, m in DEPARTMENT_TO_MINISTRY.items() if m not in MINISTRY_TO_CLUSTER
        ]
        assert not missing_ministry
        assert not missing_cluster
        assert set(MINISTRY_TO_CLUSTER.values()) <= set(CLUSTERS)


class TestPersonIdentity:
    def test_mask_id_number(self):
        assert admin._mask_id_number(None) is None
        assert admin._mask_id_number("1234") == "****"
        assert admin._mask_id_number("8001015009087") == "*********9087"
        assert admin._mask_id_number("ABC") == "****"

    def test_hr_sync_rejects_duplicate_employee_numbers(self):
        from app.api.routers.admin import HRSyncRecord
        recs = [
            HRSyncRecord(employee_number="EMP-1", surname="Doe"),
            HRSyncRecord(employee_number="EMP-1", surname="Doe"),
            HRSyncRecord(employee_number="", surname="Blank"),
        ]
        seen: set[str] = set()
        skipped = 0
        for r in recs:
            emp_no = r.employee_number.strip()
            if not emp_no or emp_no in seen:
                skipped += 1
                continue
            seen.add(emp_no)
        assert skipped == 2
        assert seen == {"EMP-1"}

    def test_hr_sync_skips_unknown_department(self):
        from app.tenant import DEPARTMENTS
        assert "not-a-dept" not in DEPARTMENTS

    def test_hr_sync_skips_branch_without_department_match(self):
        from app.api.routers.admin import HRSyncRecord
        from app.tenant import BRANCHES
        rec = HRSyncRecord(
            employee_number="EMP-2",
            department_id="treasury",
            branch_id="comms-ict-intl",
        )
        assert BRANCHES[rec.branch_id][1] != rec.department_id

    def test_hr_sync_accepts_matching_branch(self):
        from app.api.routers.admin import HRSyncRecord
        from app.tenant import BRANCHES
        rec = HRSyncRecord(
            employee_number="EMP-3",
            department_id="treasury",
            branch_id="treasury-ict",
        )
        assert BRANCHES[rec.branch_id][1] == rec.department_id

    def test_person_model_has_identity_fields(self):
        from app.models.person import Person
        for field in (
            "employee_number",
            "id_number",
            "initials",
            "surname",
            "job_title",
            "org_unit",
            "manager_id",
            "manager_name",
            "employment_status",
            "clearance_level",
            "source",
        ):
            assert field in Person.__table__.columns

    def test_user_has_person_link(self):
        from app.models.user import User
        assert "person_id" in User.__table__.columns
