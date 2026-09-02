import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.logging import configure_logging
from app.schemas import HealthStatus, ReadinessStatus
from app.services import OperationsService
from app.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


def get_operations_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OperationsService:
    return OperationsService(session)


@app.get("/health", response_model=HealthStatus, tags=["system"])
async def health(
    response: Response,
    operations: Annotated[OperationsService, Depends(get_operations_service)],
) -> HealthStatus:
    """Report application and database connectivity."""
    database_ready = await operations.database_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.error("database health check failed", extra={"error": "database unavailable"})
    return HealthStatus(
        status="ok" if database_ready else "degraded",
        database="up" if database_ready else "down",
    )


@app.get("/ready", response_model=ReadinessStatus, tags=["system"])
async def ready(
    response: Response,
    operations: Annotated[OperationsService, Depends(get_operations_service)],
) -> ReadinessStatus:
    """Report readiness and the latest collection run for every source."""
    database_ready = await operations.database_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessStatus(status="degraded", database="down", collection_runs=[])
    runs = await operations.latest_collection_runs()
    return ReadinessStatus(status="ok", database="up", collection_runs=runs)
