import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIProvider
from app.db.repositories import AIAnalysisRepository
from app.models import AIAnalysis, Opportunity
from app.schemas import AIAnalysisRequest, AIAnalysisResponse


@dataclass(frozen=True, slots=True)
class AIClassificationOutcome:
    analysis: AIAnalysis
    skipped: bool


class AIClassifierService:
    """Validate and persist AI output while keeping provider details isolated."""

    def __init__(self, session: AsyncSession, provider: AIProvider, *, prompt_version: str) -> None:
        self.repository = AIAnalysisRepository(session)
        self.provider = provider
        self.prompt_version = prompt_version

    async def classify(self, opportunity: Opportunity) -> AIClassificationOutcome:
        request = self._build_request(opportunity)
        input_hash = self._input_hash(request)
        existing = await self.repository.get_existing(
            opportunity_id=opportunity.id,
            prompt_version=self.prompt_version,
            input_hash=input_hash,
        )
        if existing is not None:
            return AIClassificationOutcome(analysis=existing, skipped=True)

        try:
            raw_result = await self.provider.analyze(request)
            if isinstance(raw_result, (str, bytes, bytearray)):
                result = AIAnalysisResponse.model_validate_json(raw_result)
            else:
                result = AIAnalysisResponse.model_validate(raw_result)
        except Exception as exc:
            analysis = await self.repository.create_failure(
                opportunity_id=opportunity.id,
                model=self.provider.model_name,
                prompt_version=self.prompt_version,
                input_hash=input_hash,
                error=f"{type(exc).__name__}: {exc}"[:4000],
            )
        else:
            analysis = await self.repository.create_success(
                opportunity_id=opportunity.id,
                model=self.provider.model_name,
                prompt_version=self.prompt_version,
                input_hash=input_hash,
                result=result,
            )
        return AIClassificationOutcome(analysis=analysis, skipped=False)

    async def classify_many(
        self, opportunities: list[Opportunity]
    ) -> list[AIClassificationOutcome]:
        return [await self.classify(opportunity) for opportunity in opportunities]

    def _build_request(self, opportunity: Opportunity) -> AIAnalysisRequest:
        return AIAnalysisRequest(
            opportunity_id=opportunity.id,
            title=opportunity.title,
            description=opportunity.description,
            budget_text=opportunity.budget_text,
            customer_name=opportunity.customer_name,
            location=opportunity.location,
            remote=opportunity.remote,
            prompt_version=self.prompt_version,
        )

    @staticmethod
    def _input_hash(request: AIAnalysisRequest) -> str:
        payload = request.model_dump(exclude={"opportunity_id", "prompt_version"})
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()
