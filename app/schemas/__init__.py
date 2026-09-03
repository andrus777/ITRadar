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
from app.schemas.opportunity_details import OpportunityDetails, OpportunityUserStatus
from app.schemas.opportunity_management import (
    OpportunityFilters,
    OpportunityListItem,
    OpportunityListPage,
    OpportunitySortField,
)
from app.schemas.source_management import SourceRunResult, SourceSummary

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
    "OpportunityFilters",
    "OpportunityListItem",
    "OpportunityListPage",
    "OpportunitySortField",
    "OpportunityDetails",
    "OpportunityUserStatus",
    "SourceRunResult",
    "SourceSummary",
]
