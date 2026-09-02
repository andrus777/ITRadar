"""Validation schemas package."""

from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.schemas.browser import OpportunityCard, OpportunityPage, ProfileView
from app.schemas.collector import CollectedItem, NormalizedOpportunity
from app.schemas.matching import MatchReason, MatchResult, UserProfileCreate

__all__ = [
    "AIAnalysisRequest",
    "AIAnalysisResponse",
    "OpportunityCard",
    "OpportunityPage",
    "ProfileView",
    "CollectedItem",
    "NormalizedOpportunity",
    "MatchReason",
    "MatchResult",
    "UserProfileCreate",
]
