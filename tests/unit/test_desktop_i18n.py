import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from app.desktop.app import create_application
from app.desktop.i18n import localize_widget_tree, translate
from app.desktop.main_window import MainWindow


def test_translation_supports_russian_and_english() -> None:
    assert translate("Settings", "ru") == "Настройки"
    assert translate("Настройки", "en") == "Settings"
    assert translate("unknown", "ru") == "unknown"


def test_main_window_is_localized_to_russian() -> None:
    create_application(["it-radar-i18n-test"])
    window = MainWindow()

    localize_widget_tree(window, "ru")

    assert window.windowTitle() == "IT Radar — рабочий стол"
    assert window.navigation_list.item(0).text() == "Обзор"
    assert window.settings_view.save_button.text() == "СОХРАНИТЬ НАСТРОЙКИ"
    assert window.tray_icon.contextMenu().actions()[0].text() == "Открыть IT Radar"
