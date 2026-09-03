import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai import OpenAICompatibleProvider
from app.schemas import AIAnalysisRequest, AIAnalysisResponse


def response_payload() -> dict[str, object]:
    return {
        "is_opportunity": True,
        "opportunity_probability": 0.95,
        "summary": "Разработка API",
        "category": "backend",
        "technologies": ["Python", "FastAPI"],
        "project_type": "development",
        "complexity": 3,
        "commercial_score": 78,
        "risk_flags": [],
        "budget_comment": "Бюджет не указан",
    }


@pytest.mark.asyncio
async def test_openai_compatible_provider_uses_strict_json_schema() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(response_payload())}
                        ],
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(
            api_key="secret", model="test-model", base_url="https://ai.test/v1", client=client
        )
        result = await provider.analyze(
            AIAnalysisRequest(
                opportunity_id=1,
                title="API",
                description=None,
                budget_text=None,
                customer_name=None,
                location=None,
                remote=True,
                prompt_version="v1",
            )
        )

    assert AIAnalysisResponse.model_validate_json(result).commercial_score == 78
    assert captured["store"] is False
    text_format = captured["text"]["format"]  # type: ignore[index]
    assert text_format["type"] == "json_schema"
    assert text_format["strict"] is True


def test_ai_response_rejects_invalid_score_and_extra_fields() -> None:
    invalid = response_payload() | {"commercial_score": 101, "unexpected": True}

    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(invalid)
