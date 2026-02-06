from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """ADSB Sync service settings."""

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_ttl: int = 60

    # Polling
    poll_interval: int = 30
    max_backoff: int = 300

    # Metrics
    metrics_port: int = 9090

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
