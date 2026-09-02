from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.schemas import OpportunityPage, ProfileView


def render_card(page: OpportunityPage) -> str:
    if page.card is None:
        return "Подходящих возможностей пока нет."
    card = page.card
    date = card.published_at.strftime("%d.%m.%Y") if card.published_at else "не указана"
    summary = _shorten(card.summary or "Краткое описание отсутствует", 700)
    score = f"{card.score}/100" if card.score is not None else "ещё не рассчитан"
    reasons = "\n".join(f"• {escape(_shorten(reason, 250))}" for reason in card.reasons[:4])
    if not reasons:
        reasons = "• Причины пока не рассчитаны"
    return (
        f"<b>{escape(card.title)}</b>\n\n"
        f"<b>Бюджет:</b> {escape(card.budget or 'не указан')}\n"
        f"<b>Источник:</b> {escape(card.source_name)}\n"
        f"<b>Дата:</b> {date}\n"
        f"<b>Score:</b> {score}\n\n"
        f"<b>Кратко:</b> {escape(summary)}\n\n"
        f"<b>Почему:</b>\n{reasons}"
    )


def card_keyboard(page: OpportunityPage, *, mode: str) -> InlineKeyboardMarkup | None:
    if page.card is None:
        return None
    navigation: list[InlineKeyboardButton] = []
    if page.has_previous:
        navigation.append(
            InlineKeyboardButton(text="← Назад", callback_data=f"browse:{mode}:{page.page - 1}")
        )
    if page.has_next:
        navigation.append(
            InlineKeyboardButton(text="Следующая →", callback_data=f"browse:{mode}:{page.page + 1}")
        )
    rows = [navigation] if navigation else []
    rows.append([InlineKeyboardButton(text="Открыть источник", url=page.card.source_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_profile(profile: ProfileView | None) -> str:
    if profile is None:
        return "Профиль не найден. Проверьте TELEGRAM_DEFAULT_PROFILE_ID."
    technologies = ", ".join(profile.technologies) or "любые"
    categories = ", ".join(profile.categories) or "любые"
    excluded = ", ".join(profile.exclude_keywords) or "нет"
    budget = _budget_range(profile.min_budget, profile.max_budget)
    remote = "только удалённо" if profile.remote_only else "любой формат"
    return (
        f"<b>{escape(profile.name)}</b>\n\n"
        f"<b>Технологии:</b> {escape(technologies)}\n"
        f"<b>Категории:</b> {escape(categories)}\n"
        f"<b>Бюджет:</b> {escape(budget)}\n"
        f"<b>Исключить:</b> {escape(excluded)}\n"
        f"<b>Формат:</b> {remote}"
    )


def _budget_range(minimum: str | None, maximum: str | None) -> str:
    if minimum and maximum:
        return f"{minimum}–{maximum}"
    if minimum:
        return f"от {minimum}"
    if maximum:
        return f"до {maximum}"
    return "без ограничений"


def _shorten(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1].rstrip()}…"
