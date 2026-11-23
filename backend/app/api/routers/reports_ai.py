"""REST API Router for AI Report Generation (Stage 4 / G2 Specification).

Endpoints:
- GET  /api/v1/reports-ai/available  -> List reports authorized for caller's role set (Gate 1)
- GET  /api/v1/reports-ai/catalog    -> Complete catalog with descriptions and roles
- POST /api/v1/reports-ai/generate   -> Generate verified, scope-contained AI intelligence report
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.generator import generate_report
from app.ai.permissions import REPORT_CATALOGUE, can_access_report, get_available_reports
from app.ai.scope import resolve_report_scope
from app.api.auth import JWTClaims, verify_token
from app.db import get_session
from app.monitoring.access_audit import record_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports-ai", tags=["reports-ai"])


class GenerateReportRequest(BaseModel):
    report_type: str = Field(..., description="ID of report to generate (e.g. executive_summary)")


@router.get("/available")
async def available_reports(
    claims: JWTClaims = Depends(verify_token),
) -> list[dict[str, Any]]:
    """Return report templates that the caller holds an authorized role to generate (Gate 1)."""
    workspace_roles, _ = _active_workspace_report_scope(claims, None)
    roles = list(dict.fromkeys([*claims.roles, *workspace_roles]))
    return get_available_reports(roles)


def _active_workspace_report_scope(
    claims: JWTClaims,
    report_type: str | None,
) -> tuple[set[str], set[str]]:
    workspace = next(
        (
            item
            for item in claims.tenant_workspace_access
            if item.get("workspace_id") == claims.active_tenant_workspace_id
        ),
        None,
    )
    if not workspace:
        return set(), set()

    cockpit_scopes = workspace.get("cockpit_scopes") or {}
    if report_type is None:
        return set(cockpit_scopes), set()

    report = REPORT_CATALOGUE.get(report_type)
    if report is None:
        return set(), set()
    allowed_cockpits = set(report["allowed_roles"]) & set(cockpit_scopes)
    scope_levels = {
        level
        for cockpit in allowed_cockpits
        for level in cockpit_scopes[cockpit]
    }
    return allowed_cockpits, scope_levels


@router.get("/catalog")
async def report_catalog(
    claims: JWTClaims = Depends(verify_token),
) -> dict[str, Any]:
    """Return full platform report catalog metadata."""
    return REPORT_CATALOGUE


@router.post("/generate")
async def generate_ai_report(
    payload: GenerateReportRequest,
    session: AsyncSession = Depends(get_session),
    claims: JWTClaims = Depends(verify_token),
) -> dict[str, Any]:
    """Generate a verified, tenancy-scoped AI intelligence report.

    Enforces the Two-Gate Authorization Model:
    - Gate 1: Capability RBAC check against REPORT_CATALOGUE
    - Gate 2: Tenancy Scope encapsulation via ReportScope & scope_hash
    """
    report_type = payload.report_type
    workspace_roles, scope_levels = _active_workspace_report_scope(
        claims, report_type
    )

    # Gate 1: Check capability RBAC
    if not can_access_report(claims.roles, report_type) and not workspace_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{','.join(claims.roles)}' is not authorized to generate '{report_type}' reports.",
        )

    # Gate 2: Derive immutable tenancy scope
    scoped_claims = claims.model_copy(
        update={"active_tenant_scope_level_keys": sorted(scope_levels)}
    )
    scope = resolve_report_scope(scoped_claims)

    try:
        report = await generate_report(session, scope, report_type)

        # Audit recording
        await record_access(
            session,
            action="ai_report.generated",
            actor=claims.email or claims.sub,
            target=report_type,
            tenant_scope={
                "tenant_scope_unit_ids": list(scope.tenant_scope_unit_ids),
                "tenant_workspace_id": scope.tenant_workspace_id,
                "tenant_scope_level_keys": list(scope.tenant_scope_level_keys),
            },
            actor_role=",".join(sorted(claims.roles)),
            scope_hash=scope.scope_hash,
            detail={
                "report_id": report["report_id"],
                "report_type": report_type,
                "fidelity_score": report["verification"]["fidelity_score"],
                "fallback_used": report["fallback_used"],
            },
        )

        return report

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate AI report: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate AI report narrative.")
