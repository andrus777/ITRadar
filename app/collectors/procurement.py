from abc import ABC

from app.collectors.base import CollectorAdapter


class ProcurementCollectorAdapter(CollectorAdapter, ABC):
    """Base contract for public procurement and commercial tender sources."""

    source_type = "procurement"
    collection_method = "html"
    market = "ru"
    priority = "P1"
    default_opportunity_type = "tender"
