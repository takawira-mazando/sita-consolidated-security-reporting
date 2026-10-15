"""Gate 2: ReportScope Value Object & Tenancy Hash.

Implements Gate 2 of the G2 specification:
Encapsulates caller tenancy into an immutable, frozen ReportScope.
Calculates a canonical SHA-256 scope_hash for caching, auditing, and isolation.
"""
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from app.api.auth import JWTClaims, is_nationwide, tenant_filter
from app.tenant import DEPARTMENTS, provincial_departments_for_province


@dataclass(frozen=True)
class ReportScope:
    department_ids: tuple[str, ...]
    branch_ids: tuple[str, ...]
    province_ids: tuple[str, ...]
    is_nationwide: bool
    scope_hash: str

    def get_filter(self, model: Any) -> Any:
        """Delegate directly to platform tenant_filter for 100% parity."""
        dummy_claims = JWTClaims(
            roles=["admin"] if self.is_nationwide else ["soc"],
            department_ids=list(self.department_ids),
            branch_ids=list(self.branch_ids),
            province_ids=list(self.province_ids),
        )
        return tenant_filter(dummy_claims, model)

    def describe(self) -> str:
        """Human-readable scope description for disclosure banner."""
        if self.is_nationwide and not self.department_ids and not self.branch_ids:
            return "Estate-Wide (All 43 National Departments & 9 Provinces)"
        parts = []
        if self.department_ids:
            dept_names = [DEPARTMENTS.get(d, d) for d in self.department_ids[:3]]
            if len(self.department_ids) > 3:
                dept_names.append(f"+{len(self.department_ids) - 3} more")
            parts.append(f"Departments: {', '.join(dept_names)}")
        if self.branch_ids:
            parts.append(f"Branches: {len(self.branch_ids)} assigned")
        if self.province_ids:
            parts.append(f"Provinces: {', '.join(self.province_ids).upper()}")
        return " | ".join(parts) if parts else "Assigned Department Scope"


def compute_scope_hash(
    department_ids: list[str],
    branch_ids: list[str],
    province_ids: list[str],
    is_nationwide: bool,
) -> str:
    """Canonical SHA-256 hash representing this exact tenancy boundary."""
    canonical_dict = {
        "depts": sorted(department_ids),
        "branches": sorted(branch_ids),
        "provinces": sorted(province_ids),
        "nationwide": bool(is_nationwide),
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def resolve_report_scope(claims: JWTClaims) -> ReportScope:
    """Derive frozen ReportScope from authenticated caller claims."""
    nationwide = is_nationwide(claims)
    raw_depts = list(getattr(claims, "department_ids", None) or [])
    raw_branches = list(getattr(claims, "branch_ids", None) or [])
    raw_provinces = list(getattr(claims, "province_ids", None) or [])

    # If provincial persona, expand province to all departments in province
    expanded_depts = set(raw_depts)
    for prov in raw_provinces:
        expanded_depts.update(provincial_departments_for_province(prov))

    final_depts = sorted(expanded_depts)
    final_branches = sorted(set(raw_branches))
    final_provinces = sorted(set(raw_provinces))

    shash = compute_scope_hash(final_depts, final_branches, final_provinces, nationwide)

    return ReportScope(
        department_ids=tuple(final_depts),
        branch_ids=tuple(final_branches),
        province_ids=tuple(final_provinces),
        is_nationwide=nationwide and not final_depts and not final_branches,
        scope_hash=shash,
    )
