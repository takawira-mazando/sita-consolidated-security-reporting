"""Central personal-information field classification and masking policy.

Closes the output-path half of gap G-06 in ``docs/B5_ICASA_ECT_Gap_Analysis.md``.

Before this module each router carried its own ad-hoc masking. ``id_number`` was
masked in exactly two places; a third serializer would have leaked it silently.
Policy therefore lives here, once, and response dicts are passed through
:func:`apply_person_policy` so that a field added to the classification is
masked automatically everywhere rather than only where someone remembered.

Statutory basis
---------------

``identity.persons.id_number`` is a SA national identity number. Under POPIA:

- **s.13(c)** — personal information (an "identifying number").
- A **"unique identifier"** — the Information Regulator's guidance note on prior
  authorisation names identity numbers and employee numbers explicitly.

It is **not** "special personal information": s.26 enumerates beliefs, race or
ethnic origin, trade union membership, political persuasion, health or sex life,
biometric information and criminal behaviour. None are stored. See B5 §5.1 for
the correction of this point.

Because the platform links HR-sourced person records across all department
tenants, s.57(1)(a) prior authorisation from the Information Regulator is
required for that linking and is **not on file**. That is a legal action, not a
code action — this module implements the complementary s.19 security safeguards.

The stored value remains unmasked in the database. Masking is an output control;
it is not encryption, and it does not defend a database dump. Encrypting
``id_number`` at rest requires a key-management decision and is tracked
separately as G-08.
"""
from __future__ import annotations

from typing import Any

#: How aggressively a field is masked when it leaves the platform.
MASK_FULL = "full"  # replaced entirely; no part of the value is emitted
MASK_TAIL = "tail"  # keep the trailing N characters, replace the rest


#: Per-field policy for person/employee records. Anything listed here is masked
#: on every output path; anything absent is treated as ordinary personal
#: information and emitted as-is.
#:
#: ``work_phone`` is classified as a unique identifier on the same basis as the
#: identity number: POPIA s.13(c) makes a telephone number personal information
#: and the Regulator's guidance lists it among unique identifiers. It was
#: previously emitted in full on both admin paths.
PERSON_FIELD_POLICY: dict[str, dict[str, Any]] = {
    "id_number": {
        "mask": MASK_TAIL,
        "visible": 4,
        "classification": "unique-identifier",
        "popia_ref": "s.13(c); unique identifier (s.57)",
        "note": "SA national identity number. Linking across tenants requires "
                "prior authorisation under s.57(1)(a).",
    },
    "work_phone": {
        "mask": MASK_TAIL,
        "visible": 3,
        "classification": "unique-identifier",
        "popia_ref": "s.13(c); unique identifier (s.57)",
        "note": "Office contact number for a named employee.",
    },
    "employee_number": {
        "mask": MASK_TAIL,
        "visible": 3,
        "classification": "unique-identifier",
        "popia_ref": "s.13(c); unique identifier (s.57)",
        "note": "Listed as a unique identifier in the Regulator's guidance.",
    },
    "clearance_level": {
        "mask": MASK_FULL,
        "classification": "personal-information",
        "popia_ref": "s.13",
        "note": "Security clearance is a security attribute, not an "
                "identifier. Masked because it enables targeting of an "
                "individual; relax with care.",
    },
}

#: Fields that identify a field as carrying a value that must never be emitted
#: in full, regardless of the per-field policy above.
NEVER_EMIT_FIELDS = frozenset({"password", "password_hash", "token"})


def mask_value(value: Any, policy: dict[str, Any]) -> Any:
    """Apply one field's masking policy. Non-strings pass through unchanged."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    mode = policy.get("mask", MASK_FULL)
    if mode == MASK_FULL:
        return "[redacted]" if value else value

    visible = int(policy.get("visible", 4))
    if len(value) <= visible:
        # Emit a fixed-width block rather than one asterisk per character, so a
        # short value does not reveal its own length through the mask width.
        return "*" * visible
    return "*" * (len(value) - visible) + value[-visible:]


def apply_person_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Mask every classified field in a person-record response dict.

    Applied to the whole dict rather than to individual values so that adding a
    sensitive field to :data:`PERSON_FIELD_POLICY` immediately protects every
    output path, including ones written later.

    Keys not present in the policy are left untouched, so this is safe to call
    on any response dict.
    """
    masked = dict(payload)
    for field in NEVER_EMIT_FIELDS:
        if field in masked:
            masked[field] = "[redacted]"
    for field, policy in PERSON_FIELD_POLICY.items():
        if field in masked and masked[field] not in (None, ""):
            masked[field] = mask_value(masked[field], policy)
    return masked


def describe() -> list[dict[str, Any]]:
    """The classification, for a control catalogue or regulator-facing export."""
    return [
        {"field": field, **policy} for field, policy in PERSON_FIELD_POLICY.items()
    ]