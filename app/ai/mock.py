from collections.abc import Iterable

from app.schemas import AIAnalysisRequest


class MockAIProvider:
    """Deterministic provider for tests; never performs network requests."""

    def __init__(self, responses: Iterable[object], *, model_name: str = "mock-ai") -> None:
        self.responses = list(responses)
        self.model_name = model_name
        self.call_count = 0

    async def analyze(self, request: AIAnalysisRequest) -> object:
        del request
        if self.call_count >= len(self.responses):
            raise RuntimeError("MockAIProvider has no response configured")
        response = self.responses[self.call_count]
        self.call_count += 1
        if isinstance(response, Exception):
            raise response
        return response
