from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.presentation import card_keyboard, render_card, render_profile
from app.services import OpportunityBrowserService

HELP_TEXT = (
    "Команды IT Radar:\n"
    "/profile — текущий профиль интересов\n"
    "/latest — свежие возможности\n"
    "/top — лучшие совпадения по score\n"
    "/help — эта справка"
)


def create_router() -> Router:
    router = Router(name="opportunity-browser")

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        await message.answer("Добро пожаловать в IT Radar.\n\n" + HELP_TEXT)

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(HELP_TEXT)

    @router.message(Command("profile"))
    async def profile(message: Message, browser: OpportunityBrowserService) -> None:
        await message.answer(render_profile(await browser.profile()), parse_mode="HTML")

    @router.message(Command("latest"))
    async def latest(message: Message, browser: OpportunityBrowserService) -> None:
        page = await browser.latest()
        await message.answer(
            render_card(page), parse_mode="HTML", reply_markup=card_keyboard(page, mode="latest")
        )

    @router.message(Command("top"))
    async def top(message: Message, browser: OpportunityBrowserService) -> None:
        page = await browser.top()
        await message.answer(
            render_card(page), parse_mode="HTML", reply_markup=card_keyboard(page, mode="top")
        )

    @router.callback_query(F.data.startswith("browse:"))
    async def browse(callback: CallbackQuery, browser: OpportunityBrowserService) -> None:
        if callback.data is None or callback.message is None:
            await callback.answer()
            return
        _, mode, raw_page = callback.data.split(":", maxsplit=2)
        page_number = max(int(raw_page), 0)
        page = await (browser.top(page_number) if mode == "top" else browser.latest(page_number))
        await callback.message.edit_text(
            render_card(page),
            parse_mode="HTML",
            reply_markup=card_keyboard(page, mode=mode),
        )
        await callback.answer()

    return router
