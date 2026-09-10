from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, TelegramSettings
from app.schemas import TelegramConfiguration


class TelegramManagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def settings(self) -> TelegramSettings | None:
        return await self.session.get(TelegramSettings, 1)

    async def create(self, configuration: TelegramConfiguration) -> TelegramSettings:
        row = TelegramSettings(id=1, **configuration.model_dump())
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(
        self, row: TelegramSettings, configuration: TelegramConfiguration
    ) -> TelegramSettings:
        for field, value in configuration.model_dump().items():
            setattr(row, field, value)
        await self.session.flush()
        return row

    async def last_digest_at(self, profile_id: int) -> datetime | None:
        return await self.session.scalar(
            select(func.max(Match.notified_at)).where(Match.user_profile_id == profile_id)
        )
