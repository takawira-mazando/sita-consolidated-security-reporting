"""Tests for column-level encryption of personal data at rest (app/pii_crypto).

The control is only worth anything if it holds under the obvious attacks:
reading the database, moving a ciphertext between rows, and re-running the
migration. Those are what these tests pin.
"""
from __future__ import annotations

import pytest
from app.pii_crypto import (
    ENVELOPE_VERSION,
    PiiCryptoError,
    PiiDecryptionError,
    decrypt,
    encrypt,
    is_encrypted,
    key_id,
)

AAD = "identity.persons.id_number"
OTHER_AAD = "identity.persons.work_phone"
ID = "8001015009087"


# --------------------------------------------------------------------------
# round trip
# --------------------------------------------------------------------------


def test_round_trip_returns_the_original_plaintext():
    assert decrypt(encrypt(ID, aad=AAD), aad=AAD) == ID


def test_stored_form_is_a_versioned_envelope():
    stored = encrypt(ID, aad=AAD)
    assert stored.startswith(f"{ENVELOPE_VERSION}:")
    assert is_encrypted(stored)
    assert not is_encrypted(ID)


def test_ciphertext_does_not_contain_the_plaintext():
    assert ID not in encrypt(ID, aad=AAD)


def test_none_round_trips():
    assert encrypt(None, aad=AAD) is None
    assert decrypt(None, aad=AAD) is None


def test_unicode_and_empty_values_survive():
    for value in ["", "Müller", "身份证", "a" * 500]:
        assert decrypt(encrypt(value, aad=AAD), aad=AAD) == value


# --------------------------------------------------------------------------
# tamper resistance
# --------------------------------------------------------------------------


def test_each_encryption_uses_a_fresh_nonce():
    """Deterministic ciphertext would leak that two rows share an ID number."""
    assert encrypt(ID, aad=AAD) != encrypt(ID, aad=AAD)


def test_aad_binds_ciphertext_to_its_column():
    """A ciphertext moved between columns must fail, not authenticate."""
    stored = encrypt(ID, aad=AAD)
    with pytest.raises(PiiDecryptionError):
        decrypt(stored, aad=OTHER_AAD)


def test_tampered_ciphertext_is_rejected():
    stored = encrypt(ID, aad=AAD)
    version, nonce, payload = stored.split(":", 2)
    flipped = payload[:-2] + ("A" if payload[-2] != "A" else "B") + payload[-1]
    with pytest.raises(PiiDecryptionError):
        decrypt(f"{version}:{nonce}:{flipped}", aad=AAD)


def test_tampered_nonce_is_rejected():
    version, nonce, payload = encrypt(ID, aad=AAD).split(":", 2)
    with pytest.raises(PiiDecryptionError):
        decrypt(f"{version}:{'A' * len(nonce)}:{payload}", aad=AAD)


def test_truncated_envelope_is_rejected_not_silently_returned():
    stored = encrypt(ID, aad=AAD)
    with pytest.raises(PiiDecryptionError):
        decrypt(stored[:20], aad=AAD)


# --------------------------------------------------------------------------
# transitional behaviour
# --------------------------------------------------------------------------


def test_legacy_plaintext_is_readable():
    """Rows written before encryption was enabled must remain readable."""
    assert decrypt(ID, aad=AAD) == ID


def test_reencrypting_an_envelope_is_idempotent():
    """Prevents double-wrapping, which would make a row unreadable."""
    stored = encrypt(ID, aad=AAD)
    assert encrypt(stored, aad=AAD) == stored


def test_key_id_is_stable_and_short():
    kid = key_id()
    assert len(kid) == 12
    assert kid == key_id()


def test_unknown_envelope_version_is_rejected():
    """A future scheme must fail loudly rather than be mis-parsed."""
    with pytest.raises(PiiDecryptionError):
        decrypt("v9:abc:def", aad=AAD)


# --------------------------------------------------------------------------
# key configuration
# --------------------------------------------------------------------------


def test_missing_or_wrong_length_key_is_refused(monkeypatch):
    import app.pii_crypto as crypto

    monkeypatch.setattr(crypto, "_cache", {})
    monkeypatch.setattr(crypto.settings, "pii_encryption_key", "", raising=False)

    with pytest.raises(PiiCryptoError):
        crypto.key_id()

    monkeypatch.setattr(crypto.settings, "pii_encryption_key", "not-base64!!", raising=False)
    with pytest.raises(PiiCryptoError):
        crypto.key_id()

    # Correct base64 but wrong length.
    monkeypatch.setattr(crypto.settings, "pii_encryption_key", "c2hvcnQ=", raising=False)
    with pytest.raises(PiiCryptoError):
        crypto.key_id()


#: A 32-byte key distinct from the published dev key, standing in for an
#: operator-supplied production value.
PRODUCTION_KEY = "cHJvZHVjdGlvbi1vbmx5LXRlc3Qta2V5LTMyYiEh"


def test_non_dev_environment_refuses_the_dev_key():
    """The dev key is published in source; it must not survive a production boot."""
    from app.config import DEV_PII_KEY, Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="PII_ENCRYPTION_KEY"):
        Settings(
            environment="production",
            jwt_secret="a" * 64,
            bootstrap_admin_password="A-Strong-Password-9182",
            seed_demo_users_enabled=False,
            pii_encryption_key=DEV_PII_KEY,
        )


def test_signing_key_is_static_by_default_outside_development():
    """A generated attestation key changes every deploy and breaks prior attestations."""
    from app.config import Settings

    prod = Settings(
        environment="production",
        jwt_secret="a" * 64,
        bootstrap_admin_password="A-Strong-Password-9182",
        seed_demo_users_enabled=False,
        pii_encryption_key=PRODUCTION_KEY,
    )
    assert prod.require_static_signing_key is True

    assert Settings().require_static_signing_key is False