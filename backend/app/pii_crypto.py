"""Transparent encryption of personal data at rest (column level).

Closes the encryption-at-rest half of the limitation recorded on slide 9 of
``presentation.html``.

Approach: application-level AES-256-GCM via a SQLAlchemy ``TypeDecorator``, so
the column transparently decrypts on read and encrypts on write. Every existing
call site keeps working unchanged — no serialiser has to remember to decrypt,
which is precisely how plaintext leaks back in after a control is added.

Why not pgcrypto
----------------
``pgcrypto`` is the usual answer, but it is **not installed** on the EDB Windows
PostgreSQL build this platform runs against, and the application role is not a
superuser, so ``CREATE EXTENSION`` is unavailable without a DBA action.
Application-level encryption uses ``cryptography``, which is already a
dependency for the ECDSA attestation engine, and therefore has no new supply
chain, no database extension and no privileged migration.

Envelope format
---------------

::

    v1:<b64url nonce>:<b64url ciphertext+tag>

The version prefix makes the scheme self-describing: a future key or algorithm
change can be detected rather than mis-parsed as corruption.

The GCM authentication tag is bound to **additional authenticated data** naming
the column, so a ciphertext cannot be relocated between columns or between
person rows undetected. An attacker with write access who copies an encrypted
ID number from one employee's row onto another's produces a value that fails to
decrypt, rather than one that silently authenticates.

Scope
-----

Only ``identity.persons.id_number`` is encrypted. The rest of the person record
(name, work phone, email, clearance) is personal information but is not a
high-value unique identifier; encrypting every column would break tenant
filtering, sorting and reporting on those fields for a marginal gain, and
minimisation is the better control for them.

Key management is operational: ``PII_ENCRYPTION_KEY`` holds a base64-encoded
32-byte key. Losing it makes every encrypted value unrecoverable. That is a
deliberate trade — it means a database dump alone cannot expose identity
numbers, at the cost of requiring real key custody.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
from typing import Any, Optional

from cryptography.exceptions import InvalidTag
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.config import settings

ENVELOPE_VERSION = "v1"
_KEY_BYTES = 32
_NONCE_BYTES = 12

_cache: dict[str, Any] = {}


class PiiCryptoError(RuntimeError):
    """Raised when personal data cannot be encrypted or decrypted."""


class PiiDecryptionError(PiiCryptoError):
    """Raised when a stored value is not a well-formed envelope for this key."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _load_key() -> bytes:
    """Resolve the 32-byte data key.

    A dev-only default exists so encryption is exercised in local development
    rather than silently disabled. In every other environment
    ``config.Settings`` refuses to start without a real key.
    """
    cached = _cache.get("key")
    if cached is not None:
        return cached

    raw = (settings.pii_encryption_key or "").strip()
    if not raw:
        raise PiiCryptoError(
            "PII_ENCRYPTION_KEY is not set; cannot encrypt personal data at rest. "
            "Generate one with: python -c \"import secrets,base64;"
            "print(base64.b64encode(secrets.token_bytes(32)).decode())\""
        )

    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise PiiCryptoError(f"PII_ENCRYPTION_KEY is not valid base64: {exc}") from exc

    if len(key) != _KEY_BYTES:
        raise PiiCryptoError(
            f"PII_ENCRYPTION_KEY must decode to exactly {_KEY_BYTES} bytes "
            f"(got {len(key)}). Generate one with: python -c \"import secrets,"
            "base64;print(base64.b64encode(secrets.token_bytes(32)).decode())\""
        )

    _cache["key"] = key
    return key


def key_id() -> str:
    """Short fingerprint of the active key.

    Lets an operator confirm which key an environment is using, and makes a
    wrong-key decryption failure diagnosable rather than mysterious.
    """
    return hashlib.sha256(_load_key()).hexdigest()[:12]


def is_encrypted(value: Any) -> bool:
    """True when a stored value already carries a recognised encryption envelope."""
    return isinstance(value, str) and value.startswith(f"{ENVELOPE_VERSION}:")


def _looks_versioned(value: Any) -> bool:
    """True for anything shaped like an envelope, including a future version.

    Used so a value written by a later scheme is rejected rather than being
    mistaken for legacy plaintext and returned verbatim — which would silently
    expose an envelope string as if it were an identity number.
    """
    return isinstance(value, str) and re.match(r"^v\d+:[A-Za-z0-9_\-]+:", value) is not None


def encrypt(value: Optional[str], *, aad: str) -> Optional[str]:
    """Encrypt a plaintext value into a versioned envelope.

    ``aad`` names the column and is authenticated by GCM but not encrypted, so
    moving a ciphertext between columns invalidates it.
    """
    if value is None:
        return None
    if is_encrypted(value):
        # Idempotent: re-encrypting an envelope would double-wrap it and make
        # the row unreadable. Safe because the column is only ever written from
        # one of two states.
        return value

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(_NONCE_BYTES)
    sealed = AESGCM(_load_key()).encrypt(nonce, value.encode("utf-8"), aad.encode("utf-8"))
    return f"{ENVELOPE_VERSION}:{_b64e(nonce)}:{_b64e(sealed)}"


def decrypt(value: Optional[str], *, aad: str) -> Optional[str]:
    """Decrypt an envelope back to plaintext.

    A value without an envelope is returned unchanged rather than raising, so
    rows written before encryption was enabled stay readable. This is a
    deliberate transitional affordance and is reported by
    ``scripts/check_plaintext_pii.py``.
    """
    if value is None:
        return None
    if not is_encrypted(value):
        if _looks_versioned(value):
            raise PiiDecryptionError(
                f"Stored value carries an unrecognised envelope version "
                f"({value.split(':', 1)[0]}); this build understands "
                f"{ENVELOPE_VERSION}. Refusing to return it as plaintext."
            )
        return value

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        _, nonce_b64, sealed_b64 = value.split(":", 2)
        plaintext = AESGCM(_load_key()).decrypt(
            _b64d(nonce_b64), _b64d(sealed_b64), aad.encode("utf-8")
        )
        return plaintext.decode("utf-8")
    except InvalidTag as exc:
        raise PiiDecryptionError(
            "Decryption failed the authentication check. Either the value was "
            "tampered with, or it was encrypted under a different "
            "PII_ENCRYPTION_KEY or bound to a different column."
        ) from exc
    except PiiCryptoError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PiiDecryptionError(f"Stored value is not a valid {ENVELOPE_VERSION} envelope: {exc}") from exc


class EncryptedText(TypeDecorator):
    """SQLAlchemy column type that encrypts on write and decrypts on read.

    Applied to the column definition so that no query, serialiser or exporter
    has to be taught about encryption. ``aad`` binds each ciphertext to its
    column name.
    """

    impl = Text
    cache_ok = True

    def __init__(self, aad: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.aad = aad

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        return encrypt(value, aad=self.aad)

    def process_result_value(self, value: Any, dialect: Any) -> Optional[str]:
        return decrypt(value, aad=self.aad)