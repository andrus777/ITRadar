import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import create_router
from app.bot.middleware import BrowserServiceMiddleware
from app.db.session import async_session_factory, engine
from app.logging import configure_logging
from app.settings import get_settings


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.telegram_bot_token is None:
        raise RuntimeError("IT_RADAR_TELEGRAM_BOT_TOKEN is required")
    if settings.telegram_default_profile_id is None:
        raise RuntimeError("IT_RADAR_TELEGRAM_DEFAULT_PROFILE_ID is required")

    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    dispatcher = Dispatcher()
    middleware = BrowserServiceMiddleware(
        async_session_factory, profile_id=settings.telegram_default_profile_id
    )
    dispatcher.message.middleware(middleware)
    dispatcher.callback_query.middleware(middleware)
    dispatcher.include_router(create_router())
    logging.getLogger(__name__).info("Telegram bot polling started")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
