from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="IT_RADAR_",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
