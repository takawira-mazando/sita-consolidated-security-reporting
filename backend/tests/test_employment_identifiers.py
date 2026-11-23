"""LDAP-only identity identifier validation."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request

from app.employment import (
    SCHEME_LDAP,
    SCHEMES,
    IdentifierSchemeError,
    looks_like_sa_id_number,
    validate,
)
from app.api.auth import JWTClaims
from app.api.routers.admin import UserUpdate, update_user


def _synthetic_sa_id_number() -> str:
    body = "000101000000"
    total = 0
    for index, character in enumerate(body):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return body + str((10 - total % 10) % 10)


def test_ldap_is_the_only_supported_identity_scheme():
    assert set(SCHEMES) == {SCHEME_LDAP}
    assert validate(SCHEME_LDAP, "DIR-00101") == "DIR-00101"


@pytest.mark.parametrize("value", ["", "  ", "ab", "contains space", "x" * 65])
def test_ldap_identifier_rejects_invalid_values(value):
    with pytest.raises(IdentifierSchemeError):
        validate(SCHEME_LDAP, value)


@pytest.mark.parametrize("scheme", ["persal", "sap_personnel", "internal_hr", "unknown"])
def test_non_ldap_schemes_are_rejected(scheme):
    with pytest.raises(IdentifierSchemeError, match="unknown identifier scheme"):
        validate(scheme, "DIR-00101")


def test_south_african_identity_number_is_not_an_ldap_account_key():
    identifier = _synthetic_sa_id_number()
    assert looks_like_sa_id_number(identifier)
    with pytest.raises(IdentifierSchemeError, match="identifies a person"):
        validate(SCHEME_LDAP, identifier)


def test_sa_id_detection_checks_date_and_luhn_digit():
    valid_id = _synthetic_sa_id_number()
    invalid_checksum = valid_id[:-1] + str((int(valid_id[-1]) + 1) % 10)
    assert not looks_like_sa_id_number("0" * 13)
    assert not looks_like_sa_id_number(invalid_checksum)
    assert not looks_like_sa_id_number(valid_id[:-1])


@pytest.mark.asyncio
async def test_user_update_cannot_link_a_non_ldap_person():
    user = SimpleNamespace(
        id="user-1",
        roles=["soc"],
        department_ids=[],
        branch_ids=[],
        province_ids=[],
        is_active=True,
    )
    person = SimpleNamespace(id="legacy-person", source="hr", is_active=True)
    session = AsyncMock()
    session.get = AsyncMock(side_effect=[user, person])
    request = Request(
        scope={"type": "http", "method": "PATCH", "path": "/", "headers": []}
    )
    claims = JWTClaims(
        sub="admin-1",
        email="admin@example.com",
        roles=["admin"],
        department_ids=[],
        branch_ids=[],
        province_ids=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_user(
            "user-1",
            UserUpdate(person_id="legacy-person"),
            request,
            session=session,
            claims=claims,
        )

    assert exc_info.value.status_code == 400
    assert "active LDAP directory identities" in exc_info.value.detail
