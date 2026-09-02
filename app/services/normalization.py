import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.schemas import NormalizedOpportunity

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "yclid",
}
CURRENCY_MARKERS = (
    (re.compile(r"(?:₽|\bруб(?:\.|лей|ля)?\b|\brub\b)", re.IGNORECASE), "RUB"),
    (re.compile(r"(?:\$|\busd\b)", re.IGNORECASE), "USD"),
    (re.compile(r"(?:€|\beur\b)", re.IGNORECASE), "EUR"),
)
NUMBER_PATTERN = re.compile(
    r"(?P<number>\d[\d\s\u00a0]*(?:[.,]\d+)?)\s*(?P<scale>тыс\.?|k|млн\.?|m)?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class BudgetRange:
    minimum: Decimal | None
    maximum: Decimal | None
    currency: str | None
    negotiable: bool = False

    @property
    def text(self) -> str | None:
        if self.negotiable:
            return "negotiable"
        if self.minimum is None and self.maximum is None:
            return None
        if self.minimum is not None and self.maximum is not None:
            amount = f"{self.minimum:g}-{self.maximum:g}"
        elif self.minimum is not None:
            amount = f"from {self.minimum:g}"
        else:
            amount = f"up to {self.maximum:g}"
        return " ".join(part for part in (amount, self.currency) if part)


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        hostname = f"{hostname}:{port}"
    path = quote(unquote(parts.path), safe="/%:@")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        )
    )
    return urlunsplit((scheme, hostname, path, query, ""))


def normalize_currency(value: str | None) -> str | None:
    if not value:
        return None
    for pattern, code in CURRENCY_MARKERS:
        if pattern.search(value):
            return code
    candidate = value.strip().upper()
    return candidate if len(candidate) == 3 and candidate.isalpha() else None


def parse_budget(value: str | None) -> BudgetRange:
    if not value:
        return BudgetRange(None, None, None)
    text = re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip().casefold()
    currency = normalize_currency(text)
    if any(marker in text for marker in ("договор", "по договор", "negotiable")):
        return BudgetRange(None, None, currency, negotiable=True)

    matches = list(NUMBER_PATTERN.finditer(text))
    if not matches:
        return BudgetRange(None, None, currency)
    numbers = [_scaled_number(match.group("number"), match.group("scale")) for match in matches]
    if len(numbers) >= 2:
        first_scale = _scale(matches[0].group("scale"))
        second_scale = _scale(matches[1].group("scale"))
        if first_scale == 1 and second_scale > 1:
            numbers[0] *= second_scale
        return BudgetRange(min(numbers[0], numbers[1]), max(numbers[0], numbers[1]), currency)
    if re.search(r"\bдо\b|up to", text):
        return BudgetRange(None, numbers[0], currency)
    return BudgetRange(numbers[0], None, currency)


def _scaled_number(value: str, scale: str | None) -> Decimal:
    compact = re.sub(r"[\s\u00a0]", "", value).replace(",", ".")
    return Decimal(compact) * _scale(scale)


def _scale(value: str | None) -> Decimal:
    normalized = (value or "").casefold().rstrip(".")
    if normalized in {"тыс", "k"}:
        return Decimal(1000)
    if normalized in {"млн", "m"}:
        return Decimal(1_000_000)
    return Decimal(1)


class OpportunityNormalizationService:
    """Apply source-independent normalization and fingerprinting."""

    def normalize(self, opportunity: NormalizedOpportunity) -> NormalizedOpportunity:
        title = normalize_text(opportunity.title)
        if not title:
            raise ValueError("normalized title is empty")
        description = normalize_text(opportunity.description)
        normalized_title = title.casefold()
        normalized_url = normalize_url(opportunity.url)

        if opportunity.budget_text:
            budget = parse_budget(opportunity.budget_text)
        else:
            budget = BudgetRange(
                opportunity.budget_from,
                opportunity.budget_to,
                normalize_currency(opportunity.currency),
                opportunity.budget_negotiable,
            )
        fingerprint_input = "\n".join((normalized_title, (description or "").casefold()))

        return opportunity.model_copy(
            update={
                "title": title,
                "description": description,
                "url": normalized_url,
                "normalized_url": normalized_url,
                "normalized_title": normalized_title,
                "budget_from": budget.minimum,
                "budget_to": budget.maximum,
                "currency": budget.currency,
                "budget_text": budget.text,
                "budget_negotiable": budget.negotiable,
                "customer_name": normalize_text(opportunity.customer_name),
                "location": normalize_text(opportunity.location),
                "fingerprint": hashlib.sha256(fingerprint_input.encode()).hexdigest(),
            }
        )
