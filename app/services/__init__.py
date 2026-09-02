"""Application services package."""

from app.services.ai_classifier import AIClassificationOutcome, AIClassifierService
from app.services.collector import CollectorService
from app.services.deduplication import DeduplicationService
from app.services.matching import MatchingEngine
from app.services.normalization import OpportunityNormalizationService
from app.services.opportunity_browser import OpportunityBrowserService
from app.services.opportunity_storage import OpportunityStorageService

__all__ = [
    "AIClassificationOutcome",
    "AIClassifierService",
    "CollectorService",
    "DeduplicationService",
    "MatchingEngine",
    "OpportunityNormalizationService",
    "OpportunityStorageService",
    "OpportunityBrowserService",
]
