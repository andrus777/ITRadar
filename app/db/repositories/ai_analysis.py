from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIAnalysis
from app.schemas import AIAnalysisResponse


class AIAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_existing(
        self, *, opportunity_id: int, prompt_version: str, input_hash: str
    ) -> AIAnalysis | None:
        query = select(AIAnalysis).where(
            AIAnalysis.opportunity_id == opportunity_id,
            AIAnalysis.prompt_version == prompt_version,
            AIAnalysis.input_hash == input_hash,
        )
        return (await self.session.scalars(query)).one_or_none()

    async def create_success(
        self,
        *,
        opportunity_id: int,
        model: str,
        prompt_version: str,
        input_hash: str,
        result: AIAnalysisResponse,
    ) -> AIAnalysis:
        analysis = AIAnalysis(
            opportunity_id=opportunity_id,
            status="success",
            model=model,
            prompt_version=prompt_version,
            input_hash=input_hash,
            **result.model_dump(),
        )
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def create_failure(
        self,
        *,
        opportunity_id: int,
        model: str,
        prompt_version: str,
        input_hash: str,
        error: str,
    ) -> AIAnalysis:
        analysis = AIAnalysis(
            opportunity_id=opportunity_id,
            status="failed",
            model=model,
            prompt_version=prompt_version,
            input_hash=input_hash,
            error=error,
        )
        self.session.add(analysis)
        await self.session.flush()
        return analysis
