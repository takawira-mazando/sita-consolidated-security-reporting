from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

security = HTTPBearer(auto_error=False)

ROLES_HIERARCHY = {
    "exec": {"risks", "compliance", "alerts", "alerts_read", "alerts_write", "findings", "dashboard"},
    "soc": {"findings", "alerts_read", "alerts_write", "dashboard"},
    "appsec": {"risks", "findings"},
    "dbsec": {"risks", "findings", "alerts_read"},
    "compliance": {"compliance"},
    "sre": {"admin_read", "admin_write", "alerts_read", "dashboard"},
    "admin": {"*"},
}

class JWTClaims(BaseModel):
    sub: str = ""
    email: str = ""
    roles: list[str] = []
    exp: int = 0

@lru_cache
def get_jwks():
    return {}

async def verify_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> JWTClaims:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        if settings.auth0_domain:
            payload = jwt.decode(
                credentials.credentials,
                settings.auth0_domain,
                algorithms=settings.auth0_algorithms,
                audience=settings.auth0_audience,
                options={"verify_aud": bool(settings.auth0_audience)},
            )
        else:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
                options={"verify_signature": True},
            )
        return JWTClaims(**payload)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_roles(*required: str):
    async def checker(claims: JWTClaims = Depends(verify_token)):
        user_roles = set(claims.roles)
        allowed = any(
            user_role == "admin" or perm in ROLES_HIERARCHY.get(user_role, set())
            for user_role in user_roles
            for perm in required
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return claims
    return checker
