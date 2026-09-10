import asyncio
from collections.abc import Callable
from threading import Event
from typing import Literal, Protocol

from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.bot.digest import TelegramDigestSender
from app.bot.presentation import render_card
from app.db.session import async_session_factory
from app.schemas import (
    OpportunityPage,
    TelegramActionResult,
    TelegramConfiguration,
    TelegramOverview,
)
from app.services import TelegramManagementService
from app.settings import Settings, get_settings

TelegramAction = Literal["status", "test", "preview", "send"]


class TelegramProvider(Protocol):
    async def overview(self) -> TelegramOverview: ...

    async def save(self, configuration: TelegramConfiguration) -> TelegramOverview: ...

    def run_action(
        self,
        action: TelegramAction,
        configuration: TelegramConfiguration,
        progress: Callable[[object], None],
        cancel_event: Event,
    ) -> TelegramActionResult: ...


class LocalTelegramProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def overview(self) -> TelegramOverview:
        async with async_session_factory() as session:
            result = await TelegramManagementService(session, self.settings).overview()
            await session.commit()
            return result

    async def save(self, configuration: TelegramConfiguration) -> TelegramOverview:
        async with async_session_factory() as session:
            result = await TelegramManagementService(session, self.settings).save(configuration)
            await session.commit()
            return result

    def run_action(
        self,
        action: TelegramAction,
        configuration: TelegramConfiguration,
        progress: Callable[[object], None],
        cancel_event: Event,
    ) -> TelegramActionResult:
        del progress, cancel_event
        return asyncio.run(self._run_action(action, configuration))

    async def _run_action(
        self, action: TelegramAction, configuration: TelegramConfiguration
    ) -> TelegramActionResult:
        if action == "preview":
            return await self._preview(configuration)
        bot = self._bot(configuration, require_chat=action != "status")
        try:
            if action == "status":
                identity = await bot.get_me()
                return TelegramActionResult(message=f"Connected: @{identity.username}")
            if action == "test":
                await bot.send_message(
                    chat_id=configuration.chat_id,
                    text="IT Radar: тестовое сообщение доставлено.",
                )
                return TelegramActionResult(message="Test message sent", sent_count=1)
            if action == "send":
                return await self._send(configuration, bot)
            raise ValueError(f"unsupported Telegram action: {action}")
        finally:
            await bot.session.close()

    async def _preview(self, configuration: TelegramConfiguration) -> TelegramActionResult:
        engine = create_async_engine(self.settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                cards = await TelegramManagementService(session, self.settings).preview(
                    configuration
                )
                rendered = [
                    render_card(
                        OpportunityPage(card=card, page=0, has_previous=False, has_next=False)
                    )
                    for card in cards
                ]
                return TelegramActionResult(
                    message=f"Preview: {len(rendered)} opportunities", preview=rendered
                )
        finally:
            await engine.dispose()

    async def _send(self, configuration: TelegramConfiguration, bot: Bot) -> TelegramActionResult:
        engine = create_async_engine(self.settings.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                service = TelegramManagementService(session, self.settings)
                try:
                    sent = await service.send_digest(
                        configuration,
                        TelegramDigestSender(bot, chat_id=configuration.chat_id),
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            return TelegramActionResult(message=f"Digest sent: {sent}", sent_count=sent)
        finally:
            await engine.dispose()

    def _bot(self, configuration: TelegramConfiguration, *, require_chat: bool) -> Bot:
        if self.settings.telegram_bot_token is None:
            raise ValueError("Telegram Bot Token is not configured")
        if require_chat and configuration.chat_id is None:
            raise ValueError("Telegram Chat ID is not configured")
        return Bot(token=self.settings.telegram_bot_token.get_secret_value())
