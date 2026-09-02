import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

Sleep = Callable[[float], Awaitable[None]]
RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.5,
    sleep: Sleep = asyncio.sleep,
    **kwargs: Any,
) -> httpx.Response:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for attempt in range(1, attempts + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in RETRY_STATUS_CODES:
                return response
            response.raise_for_status()
        except (httpx.TransportError, httpx.HTTPStatusError):
            if attempt == attempts:
                raise
            await sleep(backoff_seconds * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable retry state")
