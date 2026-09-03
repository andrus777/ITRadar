import json

import httpx

from app.http import request_with_retry
from app.schemas import AIAnalysisRequest, AIAnalysisResponse

INSTRUCTIONS = """You classify IT work opportunities for a developer.
First decide whether the text is a real commercial opportunity rather than advertising,
editorial content, a service offer, or unrelated discussion, and assign a probability.
Extract only evidence supported by the supplied opportunity. Keep the summary concise.
Return technologies and risk flags as short strings. Do not invent a budget.
Follow the supplied JSON Schema exactly."""


class OpenAICompatibleProvider:
    """Responses API provider using strict JSON Schema Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not api_key:
            raise ValueError("AI API key is required")
        self.api_key = api_key
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def analyze(self, request: AIAnalysisRequest) -> object:
        body = {
            "model": self.model_name,
            "instructions": INSTRUCTIONS,
            "input": json.dumps(request.model_dump(), ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "opportunity_analysis",
                    "schema": AIAnalysisResponse.model_json_schema(),
                    "strict": True,
                }
            },
            "store": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.client is not None:
            response = await request_with_retry(
                self.client,
                "POST",
                f"{self.base_url}/responses",
                json=body,
                headers=headers,
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await request_with_retry(
                    client,
                    "POST",
                    f"{self.base_url}/responses",
                    json=body,
                    headers=headers,
                    attempts=self.retry_attempts,
                    backoff_seconds=self.retry_backoff_seconds,
                )
        response.raise_for_status()
        return self._extract_output_text(response.json())

    @staticmethod
    def _extract_output_text(payload: object) -> str:
        if not isinstance(payload, dict):
            raise ValueError("AI response must be an object")
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct:
            return direct
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                    ):
                        return part["text"]
        raise ValueError("AI response contains no output text")
