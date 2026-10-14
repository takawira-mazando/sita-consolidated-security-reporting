import hashlib
from pydantic import model_validator
from pydantic_settings import BaseSettings

DEV_JWT_SECRET = "sita-local-dev-token-key-ephemeral"  # nosec B105

#: Dev-only data key so encryption at rest is exercised locally rather than
#: silently disabled. Any other environment must supply a real key. Published
#: in source on purpose: it protects nothing outside a development machine, and
#: ``Settings`` refuses to start if it is still in use elsewhere.
DEV_PII_KEY = "6h5qq5QWVyBBx4CiSGJiTksg+XfT9ppFDWWEt+Xr++A="


DEV_ENVS = ("dev", "development", "test", "testing")

# SHA-256 digests of known default/weak passwords — no plaintext secrets in source code
_BANNED_HASHES = frozenset({
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # weak admin default
    "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # generic password
    "ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f",  # sequential digits
    "f0689b09a56317bc2d4a7bfd62ff1b06da8d12d6a5960d70eb06b72a43063529",  # weak demo default
})


def is_disallowed_credential(candidate: str | None) -> bool:
    """Validate that candidate is non-empty, meets minimum length, and not a known default."""
    if not candidate or len(candidate) < 8:
        return True
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    return digest in _BANNED_HASHES


# Backward-compatibility alias
DISALLOWED_DEV_PASSWORDS = _BANNED_HASHES


class Settings(BaseSettings):
    environment: str = "dev"
    database_url: str = "postgresql+asyncpg://sita@localhost:5432/sita"
    redis_url: str = "redis://localhost:6379/0"
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: list[str] = ["RS256"]
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_seconds: int = 12 * 3600

    #: base64-encoded 32-byte key used to encrypt personal data at rest
    #: (see app.pii_crypto). Must be supplied outside development.
    pii_encryption_key: str = DEV_PII_KEY

    #: Refuse to auto-generate an AG attestation signing key. A generated key
    #: changes on every deploy, which silently invalidates every attestation
    #: already issued under the previous key_id. Defaults to True outside
    #: development; leave unset to get the environment-appropriate default.
    require_static_signing_key: bool | None = None
    seed_demo_users_enabled: bool = True
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    teams_webhook_url: str = ""
    pagerduty_routing_key: str = ""

    # AppScan Cloud
    appscan_key_id: str = ""
    appscan_key_secret: str = ""
    appscan_account_id: str = ""
    appscan_application_id: str = ""
    appscan_base_url: str = "https://cloud.appscan.com"
    appscan_page_size: int = 200
    appscan_scope: str = "application"

    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_echo: bool = False

    processing_batch_size: int = 100
    processing_consumers: int = 4
    processing_max_concurrent_evals: int = 20
    dispatch_max_workers: int = 10
    dispatch_consumers: int = 2
    analytics_aggregate_rules_interval: int = 60
    analytics_risk_interval: int = 300

    @model_validator(mode="after")
    def _default_static_signing_key(self):
        """Require static signing material outside development.

        Development is exempted because it has no attestations to invalidate and
        a locally generated key keeps the demo path working. Everywhere else a
        missing key is a startup failure rather than a silent rotation.
        """
        if self.require_static_signing_key is None:
            object.__setattr__(
                self,
                "require_static_signing_key",
                self.environment.lower() not in DEV_ENVS,
            )
        return self

    @model_validator(mode="after")
    def _guard_non_dev_defaults(self):
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must not be empty")
        if self.environment.lower() not in DEV_ENVS:
            if self.jwt_secret == DEV_JWT_SECRET:
                raise ValueError("JWT_SECRET is still the default dev value; set a strong secret for non-dev environments")
            if is_disallowed_credential(self.bootstrap_admin_password):
                raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be a strong, non-default value in non-dev environments")
            if self.seed_demo_users_enabled:
                raise ValueError("SEED_DEMO_USERS_ENABLED must be false in non-dev environments")
            if self.pii_encryption_key == DEV_PII_KEY or not self.pii_encryption_key:
                raise ValueError(
                    "PII_ENCRYPTION_KEY must be set to a real base64-encoded 32-byte key "
                    "in non-dev environments; the dev key encrypts personal data with a "
                    "value published in source control"
                )
        return self

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
