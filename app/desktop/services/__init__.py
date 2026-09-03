from app.desktop.services.collection import LocalCollectionRunner
from app.desktop.services.dashboard import DashboardProvider, LocalDashboardProvider
from app.desktop.services.opportunities import LocalOpportunityProvider, OpportunityProvider
from app.desktop.services.profile import DeveloperProfileProvider, LocalDeveloperProfileProvider
from app.desktop.services.sources import LocalSourceProvider, SourceProvider

__all__ = [
    "DashboardProvider",
    "LocalDashboardProvider",
    "LocalOpportunityProvider",
    "OpportunityProvider",
    "DeveloperProfileProvider",
    "LocalDeveloperProfileProvider",
    "LocalSourceProvider",
    "SourceProvider",
    "LocalCollectionRunner",
]
