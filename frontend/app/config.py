from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Frontend application settings."""

    api_server_url: str = "http://localhost:8000"
    grafana_url: str = "http://localhost:3000"
    # A model on processor cores can take tens of seconds. Keep this above the API server's
    # LLM_TIMEOUT, so a slow model surfaces as the API's error rather than a bare timeout here.
    ask_timeout: float = 150.0
    debug: bool = False
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
