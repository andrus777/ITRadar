from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services import OpportunityBrowserService


class BrowserServiceMiddleware(BaseMiddleware):
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], *, profile_id: int
    ) -> None:
        self.session_factory = session_factory
        self.profile_id = profile_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["browser"] = OpportunityBrowserService(session, profile_id=self.profile_id)
            return await handler(event, data)
