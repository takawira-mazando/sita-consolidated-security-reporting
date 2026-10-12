"""Employment identifier schemes for the South African public service.

Replaces a single ambiguous ``employee_number`` string with an explicit,
scheme-qualified identifier. The distinction matters because SA government
identifies the *same human* three different ways, and conflating them causes
real defects.

The three identifiers
---------------------

**PERSAL number** — 8 digits, issued by National Treasury through the PERSAL
(Personnel and Salary Administration) system, the national transversal HR and
payroll system for central government departments, provincial administrations,
SAPS, Education and Correctional Services. Attested in PERSAL Instruction Note
No. 3 of 2024-2025 (para 43) and the PERSAL User Management Policy.

Crucially, a PERSAL number is bound to the **employment record, not the person**.
A resignation and reappointment yields a new number; a transfer between
departments keeps the same one. It is not a Home Affairs identifier.

**SAP personnel number** — issued by SITA's own SAP HCM estate, and the scheme
the IFMS HR module (joint DPSA / National Treasury / SITA, SAP-based, payroll
excluded) will carry nationally as it displaces PERSAL for non-payroll HR.
SAP numbering is client-defined, so the pattern here is deliberately permissive
and is validated per-deployment rather than assumed.

**SA identity number** — 13 digits, issued by Home Affairs and recorded in the
population register. This identifies the **person**, not the employment. It is
deliberately *not* an employment identifier scheme here: keying an account on
it would collide across reappointment, and would pull the most sensitive unique
identifier in the estate (POPIA s.13(c), s.57) into the account table.

Why not key accounts on any of them
-----------------------------------

``identity.users.person_id`` stays an internal UUID foreign key. A government
identifier is an *attribute* of an account, not its primary key. If PERSAL
corrects or reissues a number, the account must not have to be re-keyed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class IdentifierSchemeError(ValueError):
    """Raised when an identifier does not satisfy its declared scheme."""


def looks_like_sa_id_number(value: str) -> bool:
    """True when a value is structurally a South African identity number.

    A 13-digit SA ID is ``YYMMDD`` + 4-digit sequence + a Luhn check digit, so
    it can be recognised rather than guessed at on length alone. Roughly one in
    ten trillion 13-digit integers passes both the date and Luhn tests, so the
    false-positive rate against a genuine 13-digit SAP personnel number is
    negligible.

    This guard exists because the ``internal_hr`` and ``sap_personnel`` patterns
    would otherwise both accept a 13-digit value, letting a Home Affairs
    identity number be ingested as an employment identifier. That is precisely
    the conflation the scheme model exists to prevent: the ID number identifies
    a person rather than an employment, it is the estate's most sensitive unique
    identifier (POPIA s.13(c), s.57), and it collides across reappointment.
    """
    candidate = (value or "").strip()
    if len(candidate) != 13 or not candidate.isdigit():
        return False

    year, month, day = int(candidate[0:2]), int(candidate[2:4]), int(candidate[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    # Days-per-month check, allowing for leap years (the year is two-digit, so
    # both 19xx and 20xx century interpretations are accepted).
    leap = year % 4 == 0
    max_day = 29 if (month == 2 and leap) else (30 if month in (4, 6, 9, 11) else 28 if month == 2 else 31)
    if day > max_day:
        return False

    digits = [int(ch) for ch in candidate]
    total = 0
    for index, digit in enumerate(digits[:12]):
        # SA ID Luhn doubles every second digit counting from the right of the
        # 12-digit body, i.e. odd zero-based indices (11, 9, 7, 5, 3, 1).
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - (total % 10)) % 10 == digits[12]


@dataclass(frozen=True)
class IdentifierScheme:
    id: str
    label: str
    authority: str
    identifies: str  # "employment" or "person"
    pattern: re.Pattern
    pattern_description: str
    notes: str = ""

    def validate(self, value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise IdentifierSchemeError(f"{self.id}: identifier is empty")
        if not self.pattern.match(candidate):
            raise IdentifierSchemeError(
                f"{self.id}: {candidate!r} does not match expected form "
                f"({self.pattern_description})"
            )
        if looks_like_sa_id_number(candidate):
            raise IdentifierSchemeError(
                f"{self.id}: {candidate!r} is a South African identity number, which "
                f"identifies a person rather than an employment. It is not a valid "
                f"employment identifier for any scheme; store it on "
                f"identity.persons.id_number under the controls in app.pii instead."
            )
        return candidate


SCHEME_PERSAL = "persal"
SCHEME_SAP_PERSONNEL = "sap_personnel"
SCHEME_INTERNAL = "internal_hr"

SCHEMES: dict[str, IdentifierScheme] = {
    SCHEME_PERSAL: IdentifierScheme(
        id=SCHEME_PERSAL,
        label="PERSAL personnel number",
        authority="National Treasury (PERSAL)",
        identifies="employment",
        pattern=re.compile(r"^\d{8}$"),
        pattern_description="exactly 8 digits",
        notes=(
            "Bound to the employment record, not the person. A transfer keeps "
            "it; a resignation and reappointment produces a new one."
        ),
    ),
    SCHEME_SAP_PERSONNEL: IdentifierScheme(
        id=SCHEME_SAP_PERSONNEL,
        label="SAP personnel number",
        authority="SITA SAP HCM / IFMS HR module",
        identifies="employment",
        pattern=re.compile(r"^[A-Za-z0-9]{4,20}$"),
        pattern_description="4-20 alphanumeric characters",
        notes=(
            "SAP numbering is client-defined and varies between installations. "
            "Validate against the live feed before enforcing this in production."
        ),
    ),
    SCHEME_INTERNAL: IdentifierScheme(
        id=SCHEME_INTERNAL,
        label="Internal HR feed identifier",
        authority="Platform / originating HR feed",
        identifies="employment",
        pattern=re.compile(r"^[A-Za-z0-9._-]{3,64}$"),
        pattern_description="3-64 characters, letters/digits/dot/underscore/hyphen",
        notes=(
            "Used for feeds that carry no national scheme, including the "
            "simulated HR stand-in. Not meaningful outside this platform."
        ),
    ),
}

#: Schemes that identify an employment relationship and are therefore valid as
#: the basis for provisioning a platform account.
EMPLOYMENT_SCHEMES = frozenset(SCHEMES)


def get_scheme(scheme_id: str) -> IdentifierScheme:
    try:
        return SCHEMES[scheme_id]
    except KeyError:
        raise IdentifierSchemeError(
            f"unknown identifier scheme {scheme_id!r}; known: {sorted(SCHEMES)}"
        ) from None


def validate(scheme_id: str, value: str) -> str:
    return get_scheme(scheme_id).validate(value)


def classify(value: str) -> str | None:
    """Infer a scheme from an identifier's shape.

    Returns ``None`` when the shape is ambiguous rather than guessing. Callers
    should treat ``None`` as "ask the feed which scheme this is" — silently
    coercing an unrecognised number into a scheme is how a PERSAL number ends up
    stored under ``internal_hr`` and never matches.
    """
    candidate = (value or "").strip()
    if not candidate:
        return None
    matches = [s.id for s in SCHEMES.values() if s.pattern.match(candidate)]
    if len(matches) == 1:
        return matches[0]
    if SCHEME_PERSAL in matches:
        # 8 digits also satisfies the SAP pattern; PERSAL is the more specific
        # reading and the one that is nationally meaningful.
        return SCHEME_PERSAL
    if looks_like_sa_id_number(candidate):
        # Person identifier. Never an employment identifier, whatever the
        # patterns say.
        return None
    return None


def is_national_scheme(scheme_id: str) -> bool:
    """True for schemes issued by a national public-service authority."""
    return scheme_id in (SCHEME_PERSAL, SCHEME_SAP_PERSONNEL)