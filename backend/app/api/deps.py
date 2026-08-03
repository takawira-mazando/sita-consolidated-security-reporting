from app.config import settings
from app.api.auth import verify_token, require_roles

__all__ = ["get_settings", "get_current_user", "require_roles"]

def get_settings():
    return settings

async def get_current_user(credentials=Depends(verify_token)):
    return credentials
