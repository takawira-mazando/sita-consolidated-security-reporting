"""Tests for tenancy-aligned RBAC provisioning.

Covers the provisioning gates on ``POST /admin/users`` and the update path:

1. **SITA provisioning authority** (``can_manage``) — may the caller grant this authority?
2. **Tenancy** (``person_within_scope``) — is this the caller's employee?
3. **Alignment** — a scoped account must sit in the employee's own department.

Gates 1 and 2 are independent questions. A grant can look entirely legitimate
while the employee being provisioned belongs to a different tenant, which is a
cross-tenant provisioning hole that delegation checking alone cannot see.
"""
from __future__ import annotations

from app.api.auth import JWTClaims, can_manage, person_within_scope


class _Person:
    def __init__(self, department_id=None, branch_id=None, name="Test Employee"):
        self.department_id = department_id
        self.branch_id = branch_id
        self.display_name = name
        self.employee_number = "EMP-1"


def _claims(role, departments=(), branches=(), provinces=()):
    return JWTClaims(
        sub="u1",
        email=f"{role}@example.com",
        roles=[role],
        department_ids=list(departments),
        branch_ids=list(branches),
        province_ids=list(provinces),
    )


TENANT = "treasury"
OTHER_TENANT = "justice-document"
TENANT_BRANCH = "treasury-ict"


# ---------------------------------------------------------------------------
# The cross-tenant provisioning hole
# ---------------------------------------------------------------------------


def test_scoped_sita_admin_cannot_provision_a_treasury_employee():
    """The gap this closes.

    A scoped admin granting a tenant-scoped SOC role looks legitimate under
    role-grant checks alone. The tenancy gate also verifies the employee scope.
    """
    sita_admin = _claims("transversal-admin", departments=[TENANT])
    foreign_employee = _Person(department_id=OTHER_TENANT)

    # Gate 1 passes - the grant is squarely inside the admin's own authority.
    assert can_manage(sita_admin, ["soc"], [TENANT], []) is True
    # Gate 2 is what catches it.
    assert person_within_scope(sita_admin, foreign_employee) is False


def test_scoped_sita_admin_can_provision_an_in_scope_employee():
    sita_admin = _claims("transversal-admin", departments=[TENANT])
    assert person_within_scope(sita_admin, _Person(department_id=TENANT)) is True


def test_scoped_sita_admin_cannot_provision_outside_their_branch():
    sita_admin = _claims("transversal-admin", departments=[TENANT], branches=[TENANT_BRANCH])
    assert person_within_scope(
        sita_admin, _Person(department_id=TENANT, branch_id=TENANT_BRANCH)
    ) is True
    assert person_within_scope(
        sita_admin, _Person(department_id=TENANT, branch_id="treasury-pfm")
    ) is False


def test_scoped_sita_admin_scope_expands_to_provinces_departments():
    """A SITA operator's provincial scope expands to that province's departments."""
    sita_admin = _claims("transversal-admin", provinces=["gp"])
    # gp-health is a Gauteng department.
    assert person_within_scope(
        sita_admin, _Person(department_id="gp-health")
    ) is True
    assert person_within_scope(
        sita_admin,         _Person(department_id=TENANT)
    ) is False


# ---------------------------------------------------------------------------
# Estate-wide authority
# ---------------------------------------------------------------------------


def test_nationwide_admin_can_provision_any_employee():
    transversal = _claims("transversal-admin")
    assert person_within_scope(transversal, _Person(department_id=TENANT)) is True
    assert person_within_scope(transversal, _Person(department_id=OTHER_TENANT)) is True


def test_scoped_admin_cannot_provision_an_untenanted_employee():
    """Fails closed: no department and no branch means no verifiable tenancy."""
    sita_admin = _claims("transversal-admin", departments=[TENANT])
    assert person_within_scope(sita_admin, _Person()) is False
    assert person_within_scope(sita_admin, _Person(department_id=None, branch_id=None)) is False


def test_only_unscoped_nationwide_role_can_provision_an_untenanted_employee():
    """Nationwide + unscoped covers the estate, so an untented record is allowed.

    A nationwide role that has itself been scoped down must not inherit that
    ability - 'has the role' and 'actually spans the estate' are different.
    """
    national = _claims("exec")
    assert person_within_scope(national, _Person()) is True

    scoped_national = _claims("exec", departments=[TENANT])
    assert person_within_scope(scoped_national, _Person()) is False


# ---------------------------------------------------------------------------
# Independence from the delegation gate
# ---------------------------------------------------------------------------


def test_tenancy_gate_is_independent_of_the_delegation_gate():
    """The two gates fail in different directions; neither subsumes the other.

    An in-scope employee with an over-reaching grant passes gate 1 and fails
    gate 3. A valid grant against a foreign employee passes gate 1 and fails
    gate 2.
    """
    sita_admin = _claims("transversal-admin", departments=[TENANT])

    # In-scope employee, but the caller tries to grant estate-wide exec.
    assert can_manage(sita_admin, ["exec"], [], []) is False
    assert person_within_scope(sita_admin, _Person(department_id=TENANT)) is True

    # Valid in-scope grant, but the employee is not the caller's.
    assert can_manage(sita_admin, ["soc"], [TENANT], []) is True
    assert person_within_scope(sita_admin, _Person(department_id=OTHER_TENANT)) is False


def test_person_without_department_attribute_is_handled_safely():
    """A record lacking the attributes entirely must not blow up the gate."""
    admin = _claims("transversal-admin", departments=[TENANT])

    class _Bare:
        pass

    # getattr defaults to None -> treated as untented -> denied for scoped caller.
    assert person_within_scope(admin, _Bare()) is False
