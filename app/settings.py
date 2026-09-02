from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="IT_RADAR_",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "IT Radar"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://it_radar:it_radar@localhost:5432/it_radar"
    )
    jobicy_enabled: bool = True
    jobicy_timeout_seconds: float = Field(default=30, gt=0)
    remoteok_enabled: bool = True
    remoteok_timeout_seconds: float = Field(default=30, gt=0)
    weworkremotely_enabled: bool = True
    weworkremotely_timeout_seconds: float = Field(default=30, gt=0)
    ai_api_key: SecretStr | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5-mini"
    ai_prompt_version: str = "v1"
    ai_timeout_seconds: float = Field(default=60, gt=0)
    telegram_bot_token: SecretStr | None = None
    telegram_default_profile_id: int | None = Field(default=None, gt=0)
    telegram_digest_chat_id: int | None = None
    digest_min_score: int = Field(default=70, ge=0, le=100)
    digest_batch_size: int = Field(default=20, gt=0, le=100)
    scheduler_enabled: bool = True
    scheduler_cron: str = "0 9 * * *"
    scheduler_timezone: str = "Europe/Moscow"
    http_retry_attempts: int = Field(default=3, ge=1, le=10)
    http_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=60)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
