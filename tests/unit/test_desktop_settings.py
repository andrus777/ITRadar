import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pydantic import SecretStr

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.services.settings import DesktopSettings, SettingsProvider
from app.desktop.views.settings_view import SettingsView
from app.settings import Settings


def configuration() -> DesktopSettings:
    return DesktopSettings(
        database_url="postgresql+asyncpg://radar:new-secret@db.example:5433/radar",
        ai_base_url="https://ai.example/v1",
        ai_model="radar-model",
        ai_api_key="new-key",
        ai_temperature=0.4,
        ai_timeout_seconds=45,
        retry_attempts=4,
    )


def test_settings_provider_preserves_unrelated_env_and_updates_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("UNRELATED=value\nIT_RADAR_AI_MODEL=old\n", encoding="utf-8")
    provider = SettingsProvider(Settings(ai_api_key=SecretStr("secret")), env_path)

    provider.save(configuration())

    saved = env_path.read_text(encoding="utf-8")
    assert "UNRELATED=value" in saved
    assert "IT_RADAR_AI_MODEL=radar-model" in saved
    assert "IT_RADAR_AI_API_KEY=new-key" in saved
    assert "new-secret" in saved


def test_settings_view_masks_secrets_and_exposes_database_parts(tmp_path: Path) -> None:
    create_application(["it-radar-settings-test"])
    provider = SettingsProvider(
        Settings(
            database_url="postgresql+asyncpg://radar:secret@localhost:5432/radar",
            ai_api_key=SecretStr("api-secret"),
        ),
        tmp_path / ".env",
    )
    view = SettingsView(provider)

    assert view.database_url.echoMode() == view.database_url.EchoMode.PasswordEchoOnEdit
    assert view.ai_api_key.echoMode() == view.ai_api_key.EchoMode.Password
    assert view.ai_api_key.text() == "api-secret"
    url = provider.database_parts(view.database_url.text())
    assert (url.host, url.port, url.database, url.username) == (
        "localhost",
        5432,
        "radar",
        "radar",
    )
