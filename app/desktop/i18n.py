from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QTableWidget,
    QWidget,
)

TRANSLATIONS = {
    "IT Radar Desktop": "IT Radar — рабочий стол",
    "Desktop Console": "Панель управления",
    "Dashboard": "Обзор",
    "Opportunities": "Возможности",
    "Sources": "Источники",
    "Collection": "Сбор данных",
    "Developer Profile": "Профиль разработчика",
    "Analytics": "Аналитика",
    "Logs": "Журнал",
    "Settings": "Настройки",
    "TOP OPPORTUNITIES": "ЛУЧШИЕ ВОЗМОЖНОСТИ",
    "RUN ALL": "ЗАПУСТИТЬ ВСЕ",
    "RUN SELECTED": "ЗАПУСТИТЬ ВЫБРАННЫЕ",
    "STOP": "ОСТАНОВИТЬ",
    "TECHNOLOGIES AND WEIGHTS": "ТЕХНОЛОГИИ И ВЕСА",
    "Technology": "Технология",
    "Weight 1–10": "Вес 1–10",
    "Add technology": "Добавить технологию",
    "Remove selected": "Удалить выбранное",
    "SAVE PROFILE": "СОХРАНИТЬ ПРОФИЛЬ",
    "MATCHING PREVIEW": "ПРОГНОЗ СООТВЕТСТВИЯ",
    "RECALCULATE SCORES": "ПЕРЕСЧИТАТЬ ОЦЕНКИ",
    "Enable / Disable": "Включить / выключить",
    "Run Source": "Запустить источник",
    "Not checked": "Не проверено",
    "not configured": "не настроено",
    "Not configured": "Не настроено",
    "Configured": "Настроено",
    "Enabled": "Включено",
    "Minimum score": "Минимальная оценка",
    "Minimum budget": "Минимальный бюджет",
    "Maximum items": "Максимум записей",
    "Include international": "Включать зарубежные",
    "Include types": "Типы возможностей",
    "SAVE SETTINGS": "СОХРАНИТЬ НАСТРОЙКИ",
    "CHECK CONNECTION": "ПРОВЕРИТЬ СОЕДИНЕНИЕ",
    "SEND TEST MESSAGE": "ОТПРАВИТЬ ТЕСТ",
    "PREVIEW DIGEST": "ПРЕДПРОСМОТР ДАЙДЖЕСТА",
    "SEND DIGEST NOW": "ОТПРАВИТЬ ДАЙДЖЕСТ",
    "OPPORTUNITIES / DAY": "ВОЗМОЖНОСТИ ПО ДНЯМ",
    "CATEGORIES": "КАТЕГОРИИ",
    "TECHNOLOGIES": "ТЕХНОЛОГИИ",
    "Date": "Дата",
    "Count": "Количество",
    "Category": "Категория",
    "Source": "Источник",
    "Module": "Модуль",
    "All levels": "Все уровни",
    "PAUSE": "ПАУЗА",
    "RESUME": "ПРОДОЛЖИТЬ",
    "CLEAR VIEW": "ОЧИСТИТЬ",
    "Time": "Время",
    "Level": "Уровень",
    "Message": "Сообщение",
    "Live logging active": "Журнал обновляется в реальном времени",
    "Database URL": "Адрес базы данных",
    "Host / Port / DB / User": "Хост / Порт / БД / Пользователь",
    "TEST CONNECTION": "ПРОВЕРИТЬ СОЕДИНЕНИЕ",
    "Provider URL": "Адрес провайдера",
    "Model": "Модель",
    "API key": "Ключ API",
    "Temperature": "Температура",
    "Timeout": "Тайм-аут",
    "Retries": "Повторные попытки",
    "Open IT Radar": "Открыть IT Radar",
    "Run Collection": "Запустить сбор",
    "Send Digest": "Отправить дайджест",
    "Pause Collection": "Остановить сбор",
    "Exit": "Выход",
    "Ready": "Готово",
    "System status and best opportunities": "Состояние системы и лучшие возможности",
    "Search and selection of found opportunities": "Поиск и отбор найденных возможностей",
    "Source status and management": "Состояние и управление источниками данных",
    "Manual launch and collector results": "Ручной запуск и результаты сборщиков",
    "Personal opportunity selection criteria": "Критерии персонального отбора возможностей",
    "Bot status, settings and manual digest delivery": (
        "Статус бота, настройки и ручная отправка дайджеста"
    ),
    "Opportunity dynamics and demand structure": "Динамика возможностей и структура спроса",
    "Real-time application log": "Журнал приложения в реальном времени",
    "PostgreSQL connection and AI provider settings": (
        "Подключение к PostgreSQL и параметры AI-провайдера"
    ),
    "Refresh": "Обновить",
    "Loading…": "Загрузка…",
    "Loading sources…": "Загрузка источников…",
    "Loading profile…": "Загрузка профиля…",
    "Loading settings…": "Загрузка настроек…",
    "Save status": "Сохранить статус",
    "Open source": "Открыть источник",
    "Close": "Закрыть",
    "Status:": "Статус:",
    "Back": "Назад",
    "Next": "Вперёд",
    "Apply": "Применить",
    "Reset": "Сбросить",
    "Name": "Имя",
    "Categories": "Категории",
    "Maximum budget": "Максимальный бюджет",
    "Exclude keywords": "Исключающие слова",
    "Bot": "Бот",
    "Token": "Токен",
    "Last digest": "Последний дайджест",
    "Next digest": "Следующий дайджест",
    "Not set": "Не задано",
    "No source selected": "Источник не выбран",
}


def translate(text: str, language: str) -> str:
    if language == "ru":
        return TRANSLATIONS.get(text, text)
    reverse = {value: key for key, value in TRANSLATIONS.items()}
    return reverse.get(text, text)


def current_language() -> str:
    application = QApplication.instance()
    value = application.property("itRadarLanguage") if application else None
    return value if value in ("ru", "en") else "ru"


def tr(text: str) -> str:
    return translate(text, current_language())


def localize_widget_tree(root: QWidget, language: str) -> None:
    objects = [root, *root.findChildren(QWidget), *root.findChildren(QAction)]
    for obj in objects:
        if isinstance(obj, QMainWindow):
            obj.setWindowTitle(translate(obj.windowTitle(), language))
        if isinstance(obj, (QLabel, QAbstractButton, QAction)):
            obj.setText(translate(obj.text(), language))
        if isinstance(obj, QLineEdit):
            obj.setPlaceholderText(translate(obj.placeholderText(), language))
        if isinstance(obj, QComboBox):
            for index in range(obj.count()):
                obj.setItemText(index, translate(obj.itemText(index), language))
        if isinstance(obj, QListWidget):
            for index in range(obj.count()):
                item = obj.item(index)
                item.setText(translate(item.text(), language))
        if isinstance(obj, QTableWidget):
            for column in range(obj.columnCount()):
                item = obj.horizontalHeaderItem(column)
                if item is not None:
                    item.setText(translate(item.text(), language))
