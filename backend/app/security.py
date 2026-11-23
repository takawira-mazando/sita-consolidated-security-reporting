import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings

_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (
        _ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_b64, hash_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(
    sub: str,
    email: str,
    roles: list[str],
    ttl_seconds: int | None = None,
    department_ids: list[str] | None = None,
    branch_ids: list[str] | None = None,
    province_ids: list[str] | None = None,
    tenant_workspace_ids: list[str] | None = None,
    tenant_scope_unit_ids: list[str] | None = None,
    tenant_can_manage_members: bool = False,
    tenant_workspace_access: list[dict] | None = None,
) -> str:
    ttl = ttl_seconds or settings.jwt_ttl_seconds
    now = datetime.now(timezone.utc)
    department_ids = list(department_ids or [])
    branch_ids = list(branch_ids or [])
    province_ids = list(province_ids or [])
    payload = {
        "sub": sub,
        "email": email,
        "roles": roles,
        "department_ids": department_ids,
        "branch_ids": branch_ids,
        "province_ids": province_ids,
        "tenant_workspace_ids": list(tenant_workspace_ids or []),
        "tenant_scope_unit_ids": list(tenant_scope_unit_ids or []),
        "tenant_can_manage_members": tenant_can_manage_members,
        "tenant_workspace_access": list(tenant_workspace_access or []),
        "department_id": department_ids[0] if department_ids else None,
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
