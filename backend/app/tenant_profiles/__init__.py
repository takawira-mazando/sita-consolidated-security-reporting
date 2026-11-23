"""Tenant Profiles package.

Provides a generic MSSP tenant‑profile template and the built‑in Enterprise profile.
"""
from __future__ import annotations

from app.tenant_engine import TenantProfile, tenant_registry
from app.tenant_profiles.template import build_profile

from app.config import settings

profile = build_profile(
    client_id=settings.tenant_profile,
    client_name=settings.tenant_display_name or "Unified Data Security Platform",
)
tenant_registry.register(profile)
tenant_registry.set_active(profile.id)


def get_active_profile() -> TenantProfile:
    return tenant_registry.get_active()


def set_active_profile(profile_id: str) -> TenantProfile:
    return tenant_registry.set_active(profile_id)
