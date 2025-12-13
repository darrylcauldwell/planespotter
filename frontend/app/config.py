from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Frontend application settings."""

    api_server_url: str = "http://localhost:8000"
    debug: bool = False
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
