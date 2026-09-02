import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_health_returns_ok() -> None:
    async def request_health():  # type: ignore[no-untyped-def]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
