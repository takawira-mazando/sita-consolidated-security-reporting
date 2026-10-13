"""Tests for employment identifier schemes (app/employment.py).

The platform must distinguish the three South African public-service identifiers
that all refer to the same human:

- PERSAL number  -- 8 digits, National Treasury, bound to the employment record
- SAP personnel  -- SITA's SAP HCM / the IFMS HR module
- internal       -- whatever the originating feed supplies

Conflating them produces real defects: an account provisioned against a feed's
own reference stops resolving when the feed switches to PERSAL, and a PERSAL
number reassigned after a resignation silently attaches another person's
history to the first.
"""
from __future__ import annotations

import pytest
from app.employment import (
    SCHEME_INTERNAL,
    SCHEME_PERSAL,
    SCHEME_SAP_PERSONNEL,
    IdentifierSchemeError,
    classify,
    is_national_scheme,
    validate,
)

# --------------------------------------------------------------------------
# PERSAL
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["12345678", "00000001", "80011564", "99999999"])
def test_persal_accepts_eight_digits(value):
    assert validate(SCHEME_PERSAL, value) == value


@pytest.mark.parametrize(
    "value",
    [
        "1234567",     # 7 digits
        "123456789",   # 9 digits
        "1234567a",    # non-digit
        "12 345 678",  # formatted
        "",
        "   ",
    ],
)
def test_persal_rejects_anything_that_is_not_eight_digits(value):
    with pytest.raises(IdentifierSchemeError):
        validate(SCHEME_PERSAL, value)


def test_persal_preserves_leading_zero():
    """A PERSAL number is a string, not an integer.

    Stripping or int()-ing a leading zero would produce a different, wrong
    identifier and break reconciliation against PERSAL.
    """
    assert validate(SCHEME_PERSAL, "00000001") == "00000001"


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


def test_eight_digits_classify_as_persal_not_sap():
    """8 digits satisfies both patterns; PERSAL is the specific reading."""
    assert classify("12345678") == SCHEME_PERSAL


def test_synthetic_feed_identifiers_classify_as_internal():
    assert classify("EMP-B0133-4") == SCHEME_INTERNAL
    assert classify("EMP-1001") == SCHEME_INTERNAL


def test_ambiguous_values_are_not_guessed():
    """An unrecognised shape returns None rather than a confident wrong answer.

    Silently coercing an unknown number into a scheme is how a real PERSAL
    number ends up stored under internal_hr and never matches.
    """
    assert classify("???") is None
    assert classify("") is None
    assert classify(None) is None
    assert classify("ab") is None  # below the 3-char internal minimum


def test_classification_is_stable_for_known_forms():
    for value, expected in (
        ("12345678", SCHEME_PERSAL),
        ("EMP-1001", SCHEME_INTERNAL),
        ("EMP-B0133-4", SCHEME_INTERNAL),
        ("00012345", SCHEME_PERSAL),
    ):
        assert classify(value) == expected


# --------------------------------------------------------------------------
# scheme registry
# --------------------------------------------------------------------------


def test_unknown_scheme_is_rejected_with_a_useful_message():
    with pytest.raises(IdentifierSchemeError) as exc:
        validate("nope", "12345678")
    assert "unknown identifier scheme" in str(exc.value)


def test_sap_personnel_is_permissive_but_bounded():
    assert validate(SCHEME_SAP_PERSONNEL, "S1002345")
    assert validate(SCHEME_SAP_PERSONNEL, "1002345")
    with pytest.raises(IdentifierSchemeError):
        validate(SCHEME_SAP_PERSONNEL, "ab")          # too short
    with pytest.raises(IdentifierSchemeError):
        validate(SCHEME_SAP_PERSONNEL, "A" * 21)      # too long


def test_every_scheme_is_classified_by_what_it_identifies():
    from app.employment import SCHEMES

    for scheme in SCHEMES.values():
        assert scheme.identifies == "employment", (
            f"{scheme.id} must identify an employment, not a person"
        )


def test_national_schemes_are_flagged():
    assert is_national_scheme(SCHEME_PERSAL) is True
    assert is_national_scheme(SCHEME_SAP_PERSONNEL) is True
    assert is_national_scheme(SCHEME_INTERNAL) is False


def test_identity_number_is_not_an_employment_scheme():
    """The 13-digit SA ID identifies a person, not an employment.

    Guarding this explicitly: it is the identifier most likely to be reached
    for, and keying an account on it would both collide across reappointment
    and pull POPIA s.57 unique-identifier data into account resolution.
    """
    from app.employment import SCHEMES

    for scheme_id in SCHEMES:
        with pytest.raises(IdentifierSchemeError):
            validate(scheme_id, "8001015009087")


# --------------------------------------------------------------------------
# SA identity number recognition
# --------------------------------------------------------------------------


def test_sa_id_numbers_are_recognised_structurally():
    """Date-prefix plus Luhn check digit, not a length guess."""
    from app.employment import looks_like_sa_id_number

    # Canonical well-formed SA identity number: 1980-01-01 birthdate, valid Luhn.
    assert looks_like_sa_id_number("8001015009087") is True

    # Right length and digits, impossible month -> rejected.
    assert looks_like_sa_id_number("9913015009087") is False
    # Impossible day for a 30-day month -> rejected.
    assert looks_like_sa_id_number("8004315009087") is False
    # 31 April -> rejected.
    assert looks_like_sa_id_number("8004315009087") is False
    # Valid shape, wrong check digit.
    assert looks_like_sa_id_number("8001015009088") is False
    assert looks_like_sa_id_number("800101500908") is False   # 12 digits
    assert looks_like_sa_id_number("80010150090870") is False  # 14 digits
    assert looks_like_sa_id_number("") is False


def test_every_valid_check_digit_is_accepted():
    """Across a spread of valid date prefixes, the computed check digit passes."""
    from app.employment import looks_like_sa_id_number

    def check_digit(body12: str) -> str:
        total = 0
        for i, ch in enumerate(body12):
            d = int(ch)
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return str((10 - (total % 10)) % 10)

    for prefix in ("800101", "850615", "920405", "991231", "050909"):
        body = prefix + "500908"
        candidate = body + check_digit(body)
        assert looks_like_sa_id_number(candidate) is True, candidate
        # ...and the wrong check digit must not pass.
        wrong = body + str((int(candidate[-1]) + 1) % 10)
        assert looks_like_sa_id_number(wrong) is False, wrong


def test_sa_id_detection_rejects_a_random_thirteen_digit_number():
    from app.employment import looks_like_sa_id_number

    # Valid date, wrong check digit: must not be mistaken for an identity number.
    assert looks_like_sa_id_number("8001015999999") is False


def test_an_identity_number_never_classifies_to_a_scheme():
    """classify() must not propose a scheme for a person identifier."""
    assert classify("8001015009087") is None


def test_valid_persal_numbers_are_not_mistaken_for_identity_numbers():
    """The SA-ID guard must not reject legitimate 8-digit PERSAL numbers."""
    assert validate(SCHEME_PERSAL, "80010150") == "80010150"
    assert classify("80010150") == SCHEME_PERSAL