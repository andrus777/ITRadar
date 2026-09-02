import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity


class RemoteOKCollector(CollectorAdapter):
    """Collect opportunities from Remote OK's official public JSON feed."""

    source_code = "remoteok"
    source_name = "Remote OK"
    base_url = "https://remoteok.com"
    endpoint = "https://remoteok.com/api"
    market = "international"
    priority = "P2"
    source_type = "api"
    collection_method = "api"
    default_opportunity_type = "vacancy"

    def __init__(
        self,
        *,
        count: int = 20,
        tag: str | None = None,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        self.count = count
        self.tag = tag
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        params = {"tag": self.tag} if self.tag else None
        if self.client is not None:
            response = await request_with_retry(
                self.client,
                "GET",
                self.endpoint,
                params=params,
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
        else:
            headers = {"User-Agent": "ITRadar/0.1 (+https://github.com/andrus777/ITRadar)"}
            async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
                response = await request_with_retry(
                    client,
                    "GET",
                    self.endpoint,
                    params=params,
                    attempts=self.retry_attempts,
                    backoff_seconds=self.retry_backoff_seconds,
                )
        return self._parse_response(response)[: self.count]

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = self._text(item.payload.get("position"))
        if not title:
            raise ValueError(f"Remote OK item {item.external_id!r} has no position")
        description_html = self._text(item.payload.get("description"))
        description = (
            BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)
            if description_html
            else None
        )
        salary_min = self._positive_decimal(item.payload.get("salary_min"))
        salary_max = self._positive_decimal(item.payload.get("salary_max"))
        fingerprint_source = "\n".join((title.casefold(), description or "", item.url))

        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            budget_from=salary_min,
            budget_to=salary_max,
            currency="USD" if salary_min is not None or salary_max is not None else None,
            budget_text=self._budget_text(salary_min, salary_max),
            published_at=self._datetime(item.payload.get("date")),
            fetched_at=item.fetched_at,
            customer_name=self._text(item.payload.get("company")),
            location=self._text(item.payload.get("location")),
            remote=True,
            fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        )

    @staticmethod
    def _parse_response(response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Remote OK response must be a list")
        items: list[CollectedItem] = []
        for entry in data:
            if not isinstance(entry, dict) or "legal" in entry:
                continue
            external_id = entry.get("id")
            url = entry.get("url")
            if external_id is None or not isinstance(url, str) or not url:
                raise ValueError("Remote OK job requires id and url")
            items.append(CollectedItem(external_id=str(external_id), url=url, payload=entry))
        return items

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _positive_decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        number = Decimal(str(value))
        return number if number > 0 else None

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def _budget_text(minimum: Decimal | None, maximum: Decimal | None) -> str | None:
        if minimum is None and maximum is None:
            return None
        if minimum is not None and maximum is not None:
            return f"{minimum:g}-{maximum:g} USD"
        if minimum is not None:
            return f"from {minimum:g} USD"
        return f"up to {maximum:g} USD"
