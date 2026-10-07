"""
Asymmetric Cryptographic Signing Engine (ECDSA NIST P-256) for SITA Platform.
Enables offline verifiable digital signatures for Auditor-General (AG) compliance exports.
"""
from __future__ import annotations

import base64
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

CERTS_DIR = Path(__file__).resolve().parent.parent / "certs"
DEFAULT_KEY_PATH = CERTS_DIR / "ag_signing_key.pem"
DEFAULT_PUB_KEY_PATH = CERTS_DIR / "ag_signing_public_key.pem"

_CACHED_PRIVATE_KEY: Optional[ec.EllipticCurvePrivateKey] = None


def get_ec_private_key() -> ec.EllipticCurvePrivateKey:
    """Retrieve or generate the platform's ECDSA SECP256R1 (NIST P-256) signing key."""
    global _CACHED_PRIVATE_KEY
    if _CACHED_PRIVATE_KEY is not None:
        return _CACHED_PRIVATE_KEY

    # 1. Check environment variable override
    env_key = os.environ.get("AG_SIGNING_PRIVATE_KEY_PEM")
    if env_key:
        _CACHED_PRIVATE_KEY = load_pem_private_key(env_key.encode("utf-8"), password=None)
        return _CACHED_PRIVATE_KEY

    # 2. Check certs directory file
    if DEFAULT_KEY_PATH.exists():
        try:
            with open(DEFAULT_KEY_PATH, "rb") as f:
                _CACHED_PRIVATE_KEY = load_pem_private_key(f.read(), password=None)
                return _CACHED_PRIVATE_KEY
        except Exception:
            pass

    # 3. Generate new keypair and persist locally
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

    with open(DEFAULT_KEY_PATH, "wb") as f:
        f.write(pem_private)
    with open(DEFAULT_PUB_KEY_PATH, "wb") as f:
        f.write(pem_public)

    _CACHED_PRIVATE_KEY = key
    return _CACHED_PRIVATE_KEY


def get_ec_public_key_pem() -> str:
    """Export the platform's public key in standard X.509 SubjectPublicKeyInfo PEM format."""
    key = get_ec_private_key()
    return key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def sign_canonical_payload(canonical_bytes: bytes) -> str:
    """Sign canonical data using ECDSA-SHA256 and return base64-encoded ASN.1 DER signature."""
    private_key = get_ec_private_key()
    signature_bytes = private_key.sign(
        canonical_bytes,
        ec.ECDSA(hashes.SHA256()),
    )
    return base64.b64encode(signature_bytes).decode("ascii")


def verify_canonical_payload(canonical_bytes: bytes, signature_b64: str) -> bool:
    """Verify an ECDSA-SHA256 signature against the platform's public key."""
    try:
        signature_bytes = base64.b64decode(signature_b64.encode("ascii"))
        private_key = get_ec_private_key()
        public_key = private_key.public_key()
        public_key.verify(signature_bytes, canonical_bytes, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
