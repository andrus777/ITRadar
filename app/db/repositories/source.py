from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_code(self, code: str) -> Source | None:
        return await self.session.scalar(select(Source).where(Source.code == code))

    async def create(self, *, code: str, name: str, base_url: str) -> Source:
        source = Source(code=code, name=name, base_url=base_url)
        self.session.add(source)
        await self.session.flush()
        return source
