"""LDAP identity identifier validation."""
from __future__ import annotations

import re
from dataclasses import dataclass


class IdentifierSchemeError(ValueError):
    """Raised when an identifier does not satisfy its declared scheme."""


def looks_like_sa_id_number(value: str) -> bool:
    """Recognize a South African identity number by date and Luhn checksum."""
    candidate = (value or "").strip()
    if len(candidate) != 13 or not candidate.isdigit():
        return False

    year, month, day = int(candidate[0:2]), int(candidate[2:4]), int(candidate[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    leap = year % 4 == 0
    max_day = 29 if month == 2 and leap else 30 if month in (4, 6, 9, 11) else 28 if month == 2 else 31
    if day > max_day:
        return False

    total = 0
    for index, character in enumerate(candidate[:12]):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10 == int(candidate[12])


@dataclass(frozen=True)
class IdentifierScheme:
    id: str
    label: str
    authority: str
    identifies: str
    pattern: re.Pattern
    pattern_description: str
    notes: str = ""

    def validate(self, value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise IdentifierSchemeError(f"{self.id}: identifier is empty")
        if not self.pattern.fullmatch(candidate):
            raise IdentifierSchemeError(
                f"{self.id}: {candidate!r} does not match expected form "
                f"({self.pattern_description})"
            )
        if looks_like_sa_id_number(candidate):
            raise IdentifierSchemeError(
                "A South African identity number identifies a person, not an "
                "LDAP account. Store it only under the controls in app.pii."
            )
        return candidate


SCHEME_LDAP = "ldap"
VERIFIED_PERSON_SOURCES = frozenset({"ldap", "active_directory", "directory"})

SCHEMES: dict[str, IdentifierScheme] = {
    SCHEME_LDAP: IdentifierScheme(
        id=SCHEME_LDAP,
        label="LDAP / Active Directory account identifier",
        authority="Enterprise Directory Service (LDAP / Active Directory)",
        identifies="employment",
        pattern=re.compile(r"[A-Za-z0-9._\-@\\]{3,64}"),
        pattern_description="3-64 characters (sAMAccountName, uid, or userPrincipalName)",
        notes="Authoritative identity from the configured enterprise directory.",
    ),
}


def get_scheme(scheme_id: str) -> IdentifierScheme:
    try:
        return SCHEMES[scheme_id]
    except KeyError:
        raise IdentifierSchemeError(
            f"unknown identifier scheme {scheme_id!r}; known: {sorted(SCHEMES)}"
        ) from None


def validate(scheme_id: str, value: str) -> str:
    return get_scheme(scheme_id).validate(value)
