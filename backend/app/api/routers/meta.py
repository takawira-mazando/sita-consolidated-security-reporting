"""Platform self-description endpoint.

Serves the constants the dashboard narrative needs so that prose describing the
risk model, the compliance model and the alert rules is rendered from the same
values those systems compute with, rather than from string literals that drift.

No tenant data is returned and no database session is opened -- the response is
assembled from module-level constants. It is still authenticated, because the
dashboard overlay is a post-login surface and an anonymous endpoint is not worth
the marginal convenience.
"""
from fastapi import APIRouter, Depends

from app.api.auth import require_roles
from app.api.narrative import narrative_facts, platform_model

router = APIRouter(tags=["meta"])


@router.get("/meta/model")
async def get_platform_model(claims=Depends(require_roles("dashboard"))):
    return platform_model()


@router.get("/meta/narrative-facts")
async def get_narrative_facts(claims=Depends(require_roles("dashboard"))):
    return narrative_facts()