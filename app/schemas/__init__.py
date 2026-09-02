"""Validation schemas package."""

from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.schemas.collector import CollectedItem, NormalizedOpportunity
from app.schemas.matching import MatchReason, MatchResult, UserProfileCreate

__all__ = [
    "AIAnalysisRequest",
    "AIAnalysisResponse",
    "CollectedItem",
    "NormalizedOpportunity",
    "MatchReason",
    "MatchResult",
    "UserProfileCreate",
]
