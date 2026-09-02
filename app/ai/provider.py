from typing import Protocol

from app.schemas import AIAnalysisRequest


class AIProvider(Protocol):
    """Provider-neutral interface used by the classification service."""

    @property
    def model_name(self) -> str: ...

    async def analyze(self, request: AIAnalysisRequest) -> object: ...
