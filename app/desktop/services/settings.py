from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.settings import Settings, get_settings


@dataclass(slots=True)
class DesktopSettings:
    database_url: str
    ai_base_url: str
    ai_model: str
    ai_api_key: str
    ai_temperature: float
    ai_timeout_seconds: float
    retry_attempts: int
    language: str


class SettingsProvider:
    """Read, validate and persist the desktop-editable environment settings."""

    KEYS = {
        "database_url": "IT_RADAR_DATABASE_URL",
        "ai_base_url": "IT_RADAR_AI_BASE_URL",
        "ai_model": "IT_RADAR_AI_MODEL",
        "ai_api_key": "IT_RADAR_AI_API_KEY",
        "ai_temperature": "IT_RADAR_AI_TEMPERATURE",
        "ai_timeout_seconds": "IT_RADAR_AI_TIMEOUT_SECONDS",
        "retry_attempts": "IT_RADAR_HTTP_RETRY_ATTEMPTS",
        "language": "IT_RADAR_DESKTOP_LANGUAGE",
    }

    def __init__(self, settings: Settings | None = None, env_path: Path | None = None) -> None:
        self.settings = settings or get_settings()
        self.env_path = env_path or Path(".env")

    def load(self) -> DesktopSettings:
        key = self.settings.ai_api_key
        return DesktopSettings(
            database_url=self.settings.database_url,
            ai_base_url=self.settings.ai_base_url,
            ai_model=self.settings.ai_model,
            ai_api_key=key.get_secret_value() if key else "",
            ai_temperature=self.settings.ai_temperature,
            ai_timeout_seconds=self.settings.ai_timeout_seconds,
            retry_attempts=self.settings.http_retry_attempts,
            language=self.settings.desktop_language,
        )

    async def test_database(self, database_url: str) -> None:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        finally:
            await engine.dispose()

    def save(self, value: DesktopSettings) -> None:
        make_url(value.database_url)
        current = (
            self.env_path.read_text(encoding="utf-8").splitlines() if self.env_path.exists() else []
        )
        replacements = {
            self.KEYS["database_url"]: value.database_url,
            self.KEYS["ai_base_url"]: value.ai_base_url,
            self.KEYS["ai_model"]: value.ai_model,
            self.KEYS["ai_api_key"]: value.ai_api_key,
            self.KEYS["ai_temperature"]: str(value.ai_temperature),
            self.KEYS["ai_timeout_seconds"]: str(value.ai_timeout_seconds),
            self.KEYS["retry_attempts"]: str(value.retry_attempts),
            self.KEYS["language"]: value.language,
        }
        result: list[str] = []
        seen: set[str] = set()
        for line in current:
            key = line.split("=", 1)[0].strip() if "=" in line else ""
            if key in replacements:
                result.append(f"{key}={replacements[key]}")
                seen.add(key)
            else:
                result.append(line)
        result.extend(f"{key}={value}" for key, value in replacements.items() if key not in seen)
        self.env_path.write_text("\n".join(result) + "\n", encoding="utf-8")

    @staticmethod
    def database_parts(database_url: str) -> URL:
        return make_url(database_url)
