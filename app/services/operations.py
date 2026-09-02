from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import OperationsRepository
from app.schemas import CollectionRunStatus


class OperationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = OperationsRepository(session)

    async def database_ready(self) -> bool:
        try:
            await self.repository.ping()
        except Exception:
            return False
        return True

    async def latest_collection_runs(self) -> list[CollectionRunStatus]:
        return await self.repository.latest_collection_runs()
