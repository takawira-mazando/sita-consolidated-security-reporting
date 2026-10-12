"""
Asymmetric Cryptographic Signing Engine (ECDSA NIST P-256) for SITA Platform.
Enables offline verifiable digital signatures for Auditor-General (AG) compliance exports.

Key material resolution is deliberately separated into a signing path and a
verification path:

- Signing requires the private key.
- Verification requires ONLY the public key, so an auditor (or the platform's own
  ``/verify`` endpoint) can validate an attestation without any access to signing
  material. Deriving the public key from the private key during verification is a
  defect: it makes offline verification impossible and turns every verification
  into a privileged operation.

Every signature is reported with a ``key_id`` fingerprint so an attestation signed
by a rotated key is distinguishable from one signed by its predecessor.
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)

from app.config import settings

CERTS_DIR = Path(__file__).resolve().parent.parent / "certs"
DEFAULT_KEY_PATH = CERTS_DIR / "ag_signing_key.pem"
DEFAULT_PUB_KEY_PATH = CERTS_DIR / "ag_signing_public_key.pem"

SIGNING_ALGORITHM = "ECDSA_P256_SHA256"

_CACHED_PRIVATE_KEY: Optional[ec.EllipticCurvePrivateKey] = None
_CACHED_PRIVATE_SOURCE: Optional[str] = None


class SigningKeyUnavailable(RuntimeError):
    """Raised when private key material cannot be resolved or loaded."""


class PublicKeyUnavailable(RuntimeError):
    """Raised when public key material cannot be resolved or loaded."""


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def _ensure_ec_private_key(key) -> ec.EllipticCurvePrivateKey:
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise SigningKeyUnavailable(
            "AG signing key must be an EllipticCurvePrivateKey "
            f"(got {type(key).__name__}); ECDSA SECP256R1 required."
        )
    return key


def _ensure_ec_public_key(key) -> ec.EllipticCurvePublicKey:
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise PublicKeyUnavailable(
            "AG public key must be an EllipticCurvePublicKey "
            f"(got {type(key).__name__}); ECDSA SECP256R1 required."
        )
    return key


def _generate_keypair() -> tuple[ec.EllipticCurvePrivateKey, str, str]:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())

    pem_private = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    pem_public = key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )

    for target, data in ((DEFAULT_KEY_PATH, pem_private), (DEFAULT_PUB_KEY_PATH, pem_public)):
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)

    return key, pem_private.decode("ascii"), pem_public.decode("ascii")


def get_ec_private_key() -> ec.EllipticCurvePrivateKey:
    """Resolve the ECDSA SECP256R1 (NIST P-256) signing key.

    Resolution order: ``AG_SIGNING_PRIVATE_KEY_PEM`` env var, then
    ``certs/ag_signing_key.pem``, then generate and persist a new keypair.

    A malformed key is a hard failure, not a reason to silently mint a new key:
    silently replacing signing material would invalidate every previously issued
    attestation without any operator visibility.
    """
    global _CACHED_PRIVATE_KEY, _CACHED_PRIVATE_SOURCE

    env_key = os.environ.get("AG_SIGNING_PRIVATE_KEY_PEM")
    if env_key:
        source = "env:AG_SIGNING_PRIVATE_KEY_PEM"
        if _CACHED_PRIVATE_KEY is not None and _CACHED_PRIVATE_SOURCE == source:
            return _CACHED_PRIVATE_KEY
        try:
            key = _ensure_ec_private_key(
                load_pem_private_key(env_key.encode("utf-8"), password=None)
            )
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the caller
            raise SigningKeyUnavailable(
                f"AG_SIGNING_PRIVATE_KEY_PEM is set but could not be loaded: {exc}"
            ) from exc
        _CACHED_PRIVATE_KEY = key
        _CACHED_PRIVATE_SOURCE = source
        return key

    if DEFAULT_KEY_PATH.exists():
        if (
            _CACHED_PRIVATE_KEY is not None
            and _CACHED_PRIVATE_SOURCE == f"file:{DEFAULT_KEY_PATH}"
        ):
            return _CACHED_PRIVATE_KEY
        try:
            key = _ensure_ec_private_key(load_pem_private_key(_read_bytes(DEFAULT_KEY_PATH), password=None))
        except Exception as exc:  # noqa: BLE001
            raise SigningKeyUnavailable(
                f"Signing key at {DEFAULT_KEY_PATH} could not be loaded: {exc}"
            ) from exc
        _CACHED_PRIVATE_KEY = key
        _CACHED_PRIVATE_SOURCE = f"file:{DEFAULT_KEY_PATH}"
        return key

    key, _, _ = _generate_keypair()
    _CACHED_PRIVATE_KEY = key
    _CACHED_PRIVATE_SOURCE = f"generated:{DEFAULT_KEY_PATH}"

    # A generated key changes on every fresh deployment, which silently
    # invalidates every attestation already issued under the previous key_id:
    # verifiers hold the old public key and cannot tell the difference between a
    # legitimate rotation and a substitution. Refuse to mint one when the
    # environment demands static key material.
    if settings.require_static_signing_key:
        raise SigningKeyUnavailable(
            "No AG signing key is configured and generating one is not permitted. "
            "Set AG_SIGNING_PRIVATE_KEY_PEM, or place the key at "
            f"{DEFAULT_KEY_PATH}, before starting. Generating a key here would "
            "invalidate every attestation already issued under a previous key_id."
        )
    return key


def _load_public_key_from_pem(pem: str, source: str) -> ec.EllipticCurvePublicKey:
    try:
        return _ensure_ec_public_key(load_pem_public_key(pem.encode("utf-8")))
    except Exception as exc:  # noqa: BLE001
        raise PublicKeyUnavailable(f"Public key from {source} could not be loaded: {exc}") from exc


def get_ec_public_key() -> ec.EllipticCurvePublicKey:
    """Resolve the ECDSA SECP256R1 public key for verification.

    Resolution order: ``AG_SIGNING_PUBLIC_KEY_PEM`` env var, then
    ``certs/ag_signing_public_key.pem``, then (last resort) the public half of the
    private key. The last resort keeps single-key deployments working; production
    deployments should publish the public key so verification needs no private key.
    """
    env_key = os.environ.get("AG_SIGNING_PUBLIC_KEY_PEM")
    if env_key:
        return _load_public_key_from_pem(env_key, "env:AG_SIGNING_PUBLIC_KEY_PEM")

    if DEFAULT_PUB_KEY_PATH.exists():
        try:
            pem = _read_bytes(DEFAULT_PUB_KEY_PATH).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PublicKeyUnavailable(
                f"Public key at {DEFAULT_PUB_KEY_PATH} is not valid PEM text: {exc}"
            ) from exc
        return _load_public_key_from_pem(pem, str(DEFAULT_PUB_KEY_PATH))

    return _ensure_ec_public_key(get_ec_private_key().public_key())


def get_ec_public_key_pem() -> str:
    """Export the platform's public key in standard X.509 SubjectPublicKeyInfo PEM format."""
    return get_ec_public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def key_fingerprint(public_key: Optional[ec.EllipticCurvePublicKey] = None) -> str:
    """Stable SHA-256 fingerprint of the DER public key.

    Recorded on every issued attestation so a verifier can tell which key signed it
    and detect a rotation after the fact.
    """
    key = public_key or get_ec_public_key()
    der = key.public_bytes(
        encoding=Encoding.DER,
        format=PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def get_key_id() -> str:
    """Short, human-quotable key identifier (first 16 hex chars of the fingerprint)."""
    return key_fingerprint()[:16]


def sign_canonical_payload(canonical_bytes: bytes) -> str:
    """Sign canonical data using ECDSA-SHA256 and return base64-encoded ASN.1 DER signature."""
    private_key = get_ec_private_key()
    signature_bytes = private_key.sign(
        canonical_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    return base64.b64encode(signature_bytes).decode("ascii")


def verify_canonical_payload(
    canonical_bytes: bytes,
    signature_b64: str,
    public_key: Optional[ec.EllipticCurvePublicKey] = None,
) -> bool:
    """Verify an ECDSA-SHA256 signature against a public key.

    Uses the public key only. Never requires or derives private key material, so an
    auditor holding ``/public-key`` can verify an attestation offline.

    Returns ``False`` for any signature that is malformed, signed by a different
    key, or does not match the supplied bytes.
    """
    if not isinstance(canonical_bytes, (bytes, bytearray)):
        return False
    if not isinstance(signature_b64, str) or not signature_b64:
        return False
    try:
        signature_bytes = base64.b64decode(signature_b64.encode("ascii"), validate=True)
    except (ValueError, TypeError):
        return False
    if not signature_bytes:
        return False

    try:
        key = public_key or get_ec_public_key()
        key.verify(
            signature_bytes,
            bytes(canonical_bytes),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except InvalidSignature:
        return False
    except (ValueError, TypeError):
        return False
    except PublicKeyUnavailable:
        return False