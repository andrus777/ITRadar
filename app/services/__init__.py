"""Application services package."""

from app.services.collector import CollectorService
from app.services.opportunity_storage import OpportunityStorageService

__all__ = ["CollectorService", "OpportunityStorageService"]
