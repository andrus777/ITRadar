"""Validation schemas package."""

from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.schemas.browser import OpportunityCard, OpportunityPage, ProfileView
from app.schemas.collector import CollectedItem, NormalizedOpportunity
from app.schemas.dashboard import (
    DashboardMetric,
    DashboardOpportunity,
    DashboardSnapshot,
    DashboardSystemStatus,
)
from app.schemas.matching import MatchReason, MatchResult, UserProfileCreate
from app.schemas.operations import CollectionRunStatus, HealthStatus, ReadinessStatus

__all__ = [
    "AIAnalysisRequest",
    "AIAnalysisResponse",
    "OpportunityCard",
    "OpportunityPage",
    "ProfileView",
    "CollectedItem",
    "DashboardMetric",
    "DashboardOpportunity",
    "DashboardSnapshot",
    "DashboardSystemStatus",
    "NormalizedOpportunity",
    "MatchReason",
    "MatchResult",
    "UserProfileCreate",
    "CollectionRunStatus",
    "HealthStatus",
    "ReadinessStatus",
]
