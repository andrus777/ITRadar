"""Application services package."""

from app.services.ai_classifier import AIClassificationOutcome, AIClassifierService
from app.services.collector import CollectorService
from app.services.dashboard import DashboardService
from app.services.deduplication import DeduplicationService
from app.services.digest import DigestSender, DigestService
from app.services.matching import MatchingEngine
from app.services.matching_recalculation import MatchingRecalculationService
from app.services.normalization import OpportunityNormalizationService
from app.services.operations import OperationsService
from app.services.opportunity_browser import OpportunityBrowserService
from app.services.opportunity_details import OpportunityDetailsService
from app.services.opportunity_management import OpportunityManagementService
from app.services.opportunity_storage import OpportunityStorageService
from app.services.pipeline import PipelineReport, PipelineService
from app.services.source_management import SourceManagementService

__all__ = [
    "AIClassificationOutcome",
    "AIClassifierService",
    "CollectorService",
    "DashboardService",
    "DeduplicationService",
    "DigestSender",
    "DigestService",
    "MatchingEngine",
    "MatchingRecalculationService",
    "OpportunityNormalizationService",
    "OpportunityStorageService",
    "OperationsService",
    "OpportunityBrowserService",
    "OpportunityDetailsService",
    "OpportunityManagementService",
    "PipelineReport",
    "PipelineService",
    "SourceManagementService",
]
