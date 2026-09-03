from pydantic import BaseModel, ConfigDict, Field


class MatchDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    excellent: int = Field(ge=0, description="Score 90–100")
    strong: int = Field(ge=0, description="Score 80–89")
    possible: int = Field(ge=0, description="Score 70–79")
    low: int = Field(ge=0, description="Score below 70")

    @property
    def total(self) -> int:
        return self.excellent + self.strong + self.possible + self.low


class MatchingRecalculationProgress(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    processed: int = Field(ge=0)
    total: int = Field(ge=0)


class MatchingRecalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    processed: int = Field(ge=0)
    total: int = Field(ge=0)
    cancelled: bool
    distribution: MatchDistribution
