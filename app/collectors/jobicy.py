import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import CollectorAdapter
from app.http import request_with_retry
from app.schemas import CollectedItem, NormalizedOpportunity


class JobicyCollector(CollectorAdapter):
    """Collect remote work opportunities from Jobicy's public JSON API."""

    source_code = "jobicy"
    source_name = "Jobicy"
    base_url = "https://jobicy.com"
    endpoint = "https://jobicy.com/api/v2/remote-jobs"

    def __init__(
        self,
        *,
        count: int = 20,
        geo: str | None = None,
        industry: str | None = None,
        tag: str | None = None,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        if not 1 <= count <= 200:
            raise ValueError("count must be between 1 and 200")
        self.count = count
        self.geo = geo
        self.industry = industry
        self.tag = tag
        self.timeout_seconds = timeout_seconds
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

    async def fetch(self) -> list[CollectedItem]:
        params = {
            key: value
            for key, value in {
                "count": self.count,
                "geo": self.geo,
                "industry": self.industry,
                "tag": self.tag,
            }.items()
            if value is not None
        }
        if self.client is not None:
            response = await request_with_retry(
                self.client,
                "GET",
                self.endpoint,
                params=params,
                attempts=self.retry_attempts,
                backoff_seconds=self.retry_backoff_seconds,
            )
            return self._parse_response(response)

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
            return self._parse_response(response)

    def normalize(self, item: CollectedItem) -> NormalizedOpportunity:
        title = self._text(item.payload.get("jobTitle"))
        if not title:
            raise ValueError(f"Jobicy item {item.external_id!r} has no jobTitle")

        description_html = self._text(item.payload.get("jobDescription"))
        description = self._html_to_text(description_html) if description_html else None
        salary_min = self._decimal(item.payload.get("salaryMin"))
        salary_max = self._decimal(item.payload.get("salaryMax"))
        currency = self._text(item.payload.get("salaryCurrency"))
        salary_period = self._text(item.payload.get("salaryPeriod"))
        published_at = self._datetime(item.payload.get("pubDate"))
        fingerprint_source = "\n".join((title.casefold(), description or "", item.url))

        return NormalizedOpportunity(
            external_id=item.external_id,
            title=title,
            description=description,
            url=item.url,
            budget_from=salary_min,
            budget_to=salary_max,
            currency=currency,
            budget_text=self._budget_text(salary_min, salary_max, currency, salary_period),
            published_at=published_at,
            fetched_at=item.fetched_at,
            customer_name=self._text(item.payload.get("companyName")),
            location=self._text(item.payload.get("jobGeo")),
            remote=True,
            fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        )

    @staticmethod
    def _parse_response(response: httpx.Response) -> list[CollectedItem]:
        response.raise_for_status()
        data = response.json()
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            raise ValueError("Jobicy response must contain a jobs list")

        items: list[CollectedItem] = []
        for job in jobs:
            if not isinstance(job, dict):
                raise ValueError("Jobicy job must be an object")
            external_id = job.get("id")
            url = job.get("url")
            if external_id is None or not isinstance(url, str) or not url:
                raise ValueError("Jobicy job requires id and url")
            items.append(CollectedItem(external_id=str(external_id), url=url, payload=job))
        return items

    @staticmethod
    def _html_to_text(value: str) -> str:
        return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f"invalid salary value: {value!r}") from exc

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def _budget_text(
        minimum: Decimal | None,
        maximum: Decimal | None,
        currency: str | None,
        period: str | None,
    ) -> str | None:
        if minimum is None and maximum is None:
            return None
        if minimum is not None and maximum is not None:
            amount = f"{minimum:g}-{maximum:g}"
        elif minimum is not None:
            amount = f"from {minimum:g}"
        else:
            amount = f"up to {maximum:g}"
        return " ".join(part for part in (amount, currency, period) if part)
