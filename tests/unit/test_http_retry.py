import httpx
import pytest

from app.http import request_with_retry


async def no_sleep(_: float) -> None:
    return None


@pytest.mark.asyncio
async def test_temporary_http_error_retries_then_succeeds() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls < 3 else 200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await request_with_retry(
            client,
            "GET",
            "https://example.test",
            attempts=3,
            backoff_seconds=0,
            sleep=no_sleep,
        )

    assert response.status_code == 200
    assert calls == 3


@pytest.mark.asyncio
async def test_retry_stops_after_configured_attempts() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await request_with_retry(
                client,
                "GET",
                "https://example.test",
                attempts=2,
                backoff_seconds=0,
                sleep=no_sleep,
            )

    assert calls == 2


@pytest.mark.asyncio
async def test_non_retryable_http_error_is_returned_immediately() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await request_with_retry(
            client, "GET", "https://example.test", attempts=5, sleep=no_sleep
        )

    assert response.status_code == 404
    assert calls == 1
