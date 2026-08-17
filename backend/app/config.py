from pydantic import model_validator
from pydantic_settings import BaseSettings

DEV_JWT_SECRET = "sita-local-dev-secret-change-me"  # nosec B105


class Settings(BaseSettings):
    environment: str = "dev"
    database_url: str = "postgresql+asyncpg://sita:password@localhost:5432/sita"
    redis_url: str = "redis://:password@localhost:6379/0"
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: list[str] = ["RS256"]
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_seconds: int = 12 * 3600
    seed_demo_users_enabled: bool = True
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "admin123"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    teams_webhook_url: str = ""
    pagerduty_routing_key: str = ""

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
    def _guard_non_dev_defaults(self):
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must not be empty")
        if self.environment.lower() not in ("dev", "development", "test", "testing"):
            if self.jwt_secret == DEV_JWT_SECRET:
                raise ValueError("JWT_SECRET is still the default dev value; set a strong secret for non-dev environments")
            if not self.bootstrap_admin_password or self.bootstrap_admin_password == "admin123":  # nosec B105
                raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be a strong, non-default value in non-dev environments")
            if self.seed_demo_users_enabled:
                raise ValueError("SEED_DEMO_USERS_ENABLED must be false in non-dev environments")
        return self

    class Config:
        env_file = ".env"

settings = Settings()
