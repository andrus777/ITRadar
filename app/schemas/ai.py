from pydantic import BaseModel, ConfigDict, Field


class AIAnalysisRequest(BaseModel):
    """Stable source data sent to an AI provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    opportunity_id: int
    title: str
    description: str | None
    budget_text: str | None
    customer_name: str | None
    location: str | None
    remote: bool | None
    prompt_version: str


class AIAnalysisResponse(BaseModel):
    """Strict structured result accepted from an AI provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_opportunity: bool
    opportunity_probability: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=2000)
    category: str = Field(min_length=1, max_length=100)
    technologies: list[str] = Field(max_length=50)
    project_type: str = Field(min_length=1, max_length=100)
    complexity: int = Field(ge=1, le=5)
    commercial_score: int = Field(ge=0, le=100)
    risk_flags: list[str] = Field(max_length=50)
    budget_comment: str = Field(max_length=1000)
