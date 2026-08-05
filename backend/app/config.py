from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sita:password@localhost:5432/sita"
    redis_url: str = "redis://:password@localhost:6379/0"
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: list[str] = ["RS256"]
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

    class Config:
        env_file = ".env"

settings = Settings()
