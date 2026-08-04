from fastapi import Depends

from app.api.auth import require_roles, verify_token
from app.config import settings

__all__ = ["get_current_user", "get_settings", "require_roles"]


def get_settings():
    return settings


async def get_current_user(credentials=Depends(verify_token)):
    return credentials
