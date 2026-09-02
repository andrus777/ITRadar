import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app, get_operations_service


class ReadyOperations:
    async def database_ready(self) -> bool:
        return True


class UnavailableOperations:
    async def database_ready(self) -> bool:
        return False


def test_health_returns_ok() -> None:
    async def request_health():  # type: ignore[no-untyped-def]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    app.dependency_overrides[get_operations_service] = lambda: ReadyOperations()
    try:
        response = asyncio.run(request_health())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_returns_503_when_database_is_unavailable() -> None:
    async def request_health():  # type: ignore[no-untyped-def]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    app.dependency_overrides[get_operations_service] = lambda: UnavailableOperations()
    try:
        response = asyncio.run(request_health())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "down"}
