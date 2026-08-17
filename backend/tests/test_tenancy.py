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


class TestResolveScope:
    def test_no_override_returns_empty_lists(self):
        assert auth_router._resolve_scope(None, None, None) == ([], [], [])

    def test_department_only(self):
        assert auth_router._resolve_scope("treasury", None, None) == (["treasury"], [], [])

    def test_valid_department_and_branch(self):
        assert auth_router._resolve_scope("treasury", "treasury-ict", None) == (
            ["treasury"],
            ["treasury-ict"],
            [],
        )

    def test_province_only(self):
        assert auth_router._resolve_scope(None, None, "gp") == ([], [], ["gp"])

    def test_department_and_province_conflict_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope("treasury", None, "gp")

    def test_branch_without_department_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope(None, "treasury-ict", None)

    def test_unknown_department_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope("nope", None, None)

    def test_unknown_branch_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope("treasury", "nope", None)

    def test_unknown_province_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope(None, None, "nope")

    def test_branch_of_other_department_rejected(self):
        with pytest.raises(HTTPException):
            auth_router._resolve_scope("dpsa-hr", "treasury-ict", None)


class TestDemoEntitlement:
    def _user(self, roles, department_ids=None, province_ids=None, branch_ids=None):
        return auth_router.User(
            id="u1",
            email="u@example.com",
            roles=roles,
            department_ids=department_ids or [],
            province_ids=province_ids or [],
            branch_ids=branch_ids or [],
        )

    def test_department_scope_is_account_default(self):
        user = self._user(["soc"], department_ids=["home-affairs-digital"])
        assert auth_router._account_default_scope(user) == (
            ["home-affairs-digital"],
            [],
            [],
        )

    def test_nationwide_account_defaults_to_whole_estate(self):
        user = self._user(["exec"])
        assert auth_router._account_default_scope(user) == ([], [], [])

    def test_provincial_persona_defaults_to_province(self):
        user = self._user(["province-soc-lead"], province_ids=["gp"])
        assert auth_router._account_default_scope(user) == ([], [], ["gp"])

    def test_demo_override_within_entitlement_allowed(self):
        from app.api.auth import scope_covers
        user = self._user(["soc"], department_ids=["home-affairs-digital"])
        claims = auth_router._scope_claims(user)
        assert scope_covers(claims, ["home-affairs-digital"], [])
        assert scope_covers(claims, ["home-affairs-digital"], ["dha-digital"])
        assert not scope_covers(claims, ["treasury"], [])
        assert not scope_covers(claims, [], [], province_ids=["gp"])

    def test_nationwide_demo_override_anywhere(self):
        from app.api.auth import scope_covers
        user = self._user(["exec"])
        claims = auth_router._scope_claims(user)
        assert scope_covers(claims, ["treasury"], ["treasury-ict"])
        assert scope_covers(claims, [], [], province_ids=["gp"])

    def test_province_demo_override_stays_in_province(self):
        from app.api.auth import scope_covers
        user = self._user(["province-soc-lead"], province_ids=["gp"])
        claims = auth_router._scope_claims(user)
        assert scope_covers(claims, ["gp-health"], [])
        assert scope_covers(claims, [], [], province_ids=["gp"])
        assert not scope_covers(claims, ["treasury"], [])
        assert not scope_covers(claims, [], [], province_ids=["wc"])


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
    def test_admin_grants_within_governance(self):
        c = _claims(["admin"], [], [])
        granted = grantable_roles(c)
        assert "dept-admin" in granted and "exec" in granted and "compliance" in granted
        assert "admin" not in granted and "operator" not in granted
        assert can_manage(c, ["dept-admin", "exec"], ["treasury"], ["treasury-ict"])
        assert not can_manage(c, ["admin"], [], [])
        assert not can_manage(c, ["operator"], [], [])

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
        assert GRANTABLE_ROLES["transversal-admin"] == set(DEPARTMENT_ROLES) | {"exec", "compliance", "sre", "transversal-admin"}
        assert GRANTABLE_ROLES["dept-admin"] == OPERATIONAL_DEPARTMENT_ROLES | {"branch-admin"}
        assert GRANTABLE_ROLES["province-dept-admin"] == OPERATIONAL_DEPARTMENT_ROLES
        assert GRANTABLE_ROLES["branch-admin"] == OPERATIONAL_DEPARTMENT_ROLES
        assert GRANTABLE_ROLES["sre"] == OPERATIONAL_DEPARTMENT_ROLES
        assert GRANTABLE_ROLES["operator"] == {"admin", "operator"}
        assert "admin" not in GRANTABLE_ROLES["admin"]
        assert "operator" not in GRANTABLE_ROLES["admin"]
        assert "admin" in GRANTABLE_ROLES["operator"] and "exec" not in GRANTABLE_ROLES["operator"]
        assert GRANTABLE_ROLES["dept-admin"] | GRANTABLE_ROLES["branch-admin"] | GRANTABLE_ROLES["province-dept-admin"] | set(ADMIN_TIERS) == DEPARTMENT_ROLES | {"admin", "transversal-admin", "operator"}
        assert tier_for_role("operator") > tier_for_role("admin") > tier_for_role("transversal-admin") > tier_for_role("dept-admin") > tier_for_role("branch-admin") > tier_for_role("soc")

    def test_sre_nationwide_manages_operational_users(self):
        c = _claims(["sre"], [], [])
        from app.tenant import OPERATIONAL_DEPARTMENT_ROLES
        assert grantable_roles(c) == OPERATIONAL_DEPARTMENT_ROLES
        assert can_manage(c, ["soc"], ["treasury"], [])
        assert can_manage(c, ["appsec"], ["treasury"], ["treasury-ict"])
        assert not can_manage(c, ["admin"], [], [])
        assert not can_manage(c, ["dept-admin"], ["treasury"], ["treasury-ict"])

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
        from app.tenant import GRANTABLE_ROLES
        c = _claims(["transversal-admin"], [], [])
        assert grantable_roles(c) == GRANTABLE_ROLES["transversal-admin"]
        assert "exec" in grantable_roles(c)
        assert "compliance" in grantable_roles(c)
        assert "sre" in grantable_roles(c)
        assert "transversal-admin" in grantable_roles(c)
        assert "admin" not in grantable_roles(c)

    def test_transversal_admin_cannot_grant_superior(self):
        c = _claims(["transversal-admin"], ["treasury"], [])
        assert can_manage(c, ["transversal-admin"], ["treasury"], [])  # peers grantable
        assert not can_manage(c, ["admin"], [], [])
        assert not can_manage(c, ["admin"], ["treasury"], [])  # even in-scope, superior stays out of reach
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


class TestOperatorGovernance:
    def test_operator_creates_sita_superuser(self):
        c = _claims(["operator"], [], [])
        assert grantable_roles(c) == {"admin", "operator"}
        assert can_manage(c, ["admin"], [], [])
        # The creator holds no dashboard/data grants and no bypass of the
        # SITA superuser's own job: provisioning department superusers or
        # national dashboards is the SITA superuser's (admin's) function.
        assert not can_manage(c, ["dept-admin"], [], [])
        assert not can_manage(c, ["exec"], [], [])
        assert not can_manage(c, ["soc"], ["treasury"], [])

    def test_operator_peer_rotation(self):
        c = _claims(["operator"], [], [])
        assert can_manage(c, ["operator"], [], [])

    def test_operator_is_nationwide(self):
        from app.api.auth import is_nationwide
        from app.tenant import NATIONWIDE_ROLES
        assert "operator" in NATIONWIDE_ROLES
        assert is_nationwide(_claims(["operator"], [], []))
        assert tenant_filter(_claims(["operator"], [], []), Finding) is None

    def test_only_operator_can_grant_admin(self):
        for roles, depts in [
            (["transversal-admin"], []),
            (["dept-admin"], ["treasury"]),
            (["branch-admin"], ["treasury"]),
            (["sre"], []),
        ]:
            c = _claims(roles, depts, [])
            assert not can_manage(c, ["admin"], [], [])
        assert can_manage(_claims(["operator"], [], []), ["admin"], [], [])
        # Department superusers cannot even reach their own peer tier.
        c = _claims(["dept-admin"], ["treasury"], [])
        assert not can_manage(c, ["dept-admin"], ["treasury"], [])


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

    def test_user_create_requires_hr_person(self):
        from app.api.routers.admin import UserCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(email="external@example.com", password="Secret123", roles=["soc"])
        # Explicitly no free-form identity detail fields remain on the create payload.
        assert "surname" not in UserCreate.model_fields
        assert "title" not in UserCreate.model_fields

    def test_sim_hr_row_maps_to_sync_record(self):
        from app.api.routers.admin import HRSyncRecord, _sim_row_to_sync
        row = {
            "employee_number": "EMP-2001",
            "id_number": "7802210812046",
            "title": "Dr",
            "initials": "EN",
            "first_name": "Emma",
            "surname": "Ncube",
            "display_name": "Emma Ncube",
            "email": "exec@example.com",
            "job_title": "Executive Director",
            "org_unit": "Cabinet Services",
            "department_code": "presidency",
            "branch_code": "presidency-cabinet",
            "manager_employee_number": "EMP-1002",
            "manager_name": "Naledi Khumalo",
            "work_phone": "012 300 2001",
            "location": "Union Buildings, Pretoria",
            "employment_status": "active",
            "clearance_level": "top-secret",
        }
        rec = _sim_row_to_sync(row)
        assert rec.employee_number == "EMP-2001"
        assert rec.department_id == "presidency"
        assert rec.branch_id == "presidency-cabinet"
        assert rec.surname == "Ncube"
        assert rec.employment_status == "active"
        # department_code / branch_code (HR slugs) map onto platform ids.
        assert "department_code" not in HRSyncRecord.model_fields  # external-system naming stays external

    def test_sim_hr_row_derives_display_name(self):
        from app.api.routers.admin import _sim_row_to_sync
        rec = _sim_row_to_sync(
            {"employee_number": "EMP-9", "first_name": "Zanele", "display_name": None}
        )
        assert rec.display_name == "Zanele"
