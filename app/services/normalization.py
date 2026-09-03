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
    budget_type: str = "unknown"

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
    if any(
        marker in text
        for marker in (
            "договор",
            "по договор",
            "negotiable",
            "обсуждается",
            "по согласованию",
            "по запросу",
        )
    ):
        return BudgetRange(None, None, currency, negotiable=True, budget_type="negotiable")

    matches = list(NUMBER_PATTERN.finditer(text))
    if not matches:
        return BudgetRange(None, None, currency)
    budget_type = _budget_type(text)
    numbers = [_scaled_number(match.group("number"), match.group("scale")) for match in matches]
    if len(numbers) >= 2:
        first_scale = _scale(matches[0].group("scale"))
        second_scale = _scale(matches[1].group("scale"))
        if first_scale == 1 and second_scale > 1:
            numbers[0] *= second_scale
        return BudgetRange(
            min(numbers[0], numbers[1]),
            max(numbers[0], numbers[1]),
            currency,
            budget_type=budget_type,
        )
    if re.search(r"\bдо\b|up to", text):
        return BudgetRange(None, numbers[0], currency, budget_type=budget_type)
    return BudgetRange(numbers[0], None, currency, budget_type=budget_type)


def _budget_type(text: str) -> str:
    if re.search(r"(?:/|\b(?:за|в)\b)\s*(?:час|hour)|почас", text):
        return "hourly"
    if re.search(r"(?:/|\b(?:за|в)\b)\s*(?:месяц|month)|ежемесяч", text):
        return "monthly"
    return "fixed"


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
                opportunity.budget_type,
            )
        classification_text = " ".join(
            part for part in (title, description, opportunity.source_category) if part
        ).casefold()
        technologies = normalize_technologies(opportunity.technologies, classification_text)
        category = normalize_category(opportunity.category, classification_text)
        customer_type = normalize_customer_type(
            opportunity.customer_type,
            " ".join(part for part in (opportunity.customer_name, classification_text) if part),
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
                "budget_type": budget.budget_type,
                "source_category": normalize_text(opportunity.source_category),
                "category": category,
                "technologies": technologies,
                "customer_name": normalize_text(opportunity.customer_name),
                "customer_type": customer_type,
                "location": normalize_text(opportunity.location),
                "fingerprint": hashlib.sha256(fingerprint_input.encode()).hexdigest(),
            }
        )


CATEGORY_PATTERNS = (
    ("telegram", re.compile(r"\btelegram\b|телеграм", re.I)),
    ("1c", re.compile(r"(?:\b1c\b|\b1с\b)", re.I)),
    ("crm", re.compile(r"\bcrm\b", re.I)),
    ("erp", re.compile(r"\berp\b", re.I)),
    ("ai", re.compile(r"искусственн\w* интеллект|\bai\b|\bllm\b", re.I)),
    ("ml", re.compile(r"машинн\w* обучен|machine learning|\bml\b", re.I)),
    ("parsing", re.compile(r"парсинг|scrap(?:e|ing)|crawler", re.I)),
    ("devops", re.compile(r"\bdevops\b|ci/cd|kubernetes", re.I)),
    ("mobile", re.compile(r"мобильн\w* приложен|\bandroid\b|\bios\b", re.I)),
    ("frontend", re.compile(r"\bfront[ -]?end\b|фронтенд", re.I)),
    ("fullstack", re.compile(r"\bfull[ -]?stack\b|фуллст[еэ]к", re.I)),
    ("backend", re.compile(r"\bback[ -]?end\b|бэкенд|бекенд", re.I)),
    ("integration", re.compile(r"интеграц|integration", re.I)),
    ("api", re.compile(r"\bapi\b", re.I)),
    ("automation", re.compile(r"автоматизац|automation|\bn8n\b", re.I)),
    ("testing", re.compile(r"тестирован|\bqa\b|testing", re.I)),
    ("infrastructure", re.compile(r"инфраструктур|администрирован", re.I)),
    ("desktop", re.compile(r"desktop|настольн\w* приложен", re.I)),
    ("embedded", re.compile(r"embedded|встраиваем", re.I)),
    ("data", re.compile(r"данн\w*|analytics|аналитик", re.I)),
)

TECHNOLOGY_PATTERNS = (
    ("python", re.compile(r"\bpython\b", re.I)),
    ("fastapi", re.compile(r"\bfastapi\b", re.I)),
    ("django", re.compile(r"\bdjango\b", re.I)),
    ("flask", re.compile(r"\bflask\b", re.I)),
    ("javascript", re.compile(r"\bjavascript\b|\bjs\b", re.I)),
    ("typescript", re.compile(r"\btypescript\b", re.I)),
    ("react", re.compile(r"\breact(?:\.js)?\b", re.I)),
    ("vue", re.compile(r"\bvue(?:\.js)?\b", re.I)),
    ("node.js", re.compile(r"\bnode(?:\.js|js)?\b", re.I)),
    ("php", re.compile(r"\bphp\b", re.I)),
    ("java", re.compile(r"\bjava\b", re.I)),
    ("c#", re.compile(r"(?<!\w)c#(?!\w)", re.I)),
    (".net", re.compile(r"(?<!\w)\.net\b", re.I)),
    ("1c", re.compile(r"(?:\b1c\b|\b1с\b)", re.I)),
    ("postgresql", re.compile(r"\bpostgres(?:ql)?\b", re.I)),
    ("mysql", re.compile(r"\bmysql\b", re.I)),
    ("redis", re.compile(r"\bredis\b", re.I)),
    ("docker", re.compile(r"\bdocker\b", re.I)),
    ("kubernetes", re.compile(r"\bkubernetes\b|\bk8s\b", re.I)),
    ("telegram", re.compile(r"\btelegram\b|телеграм", re.I)),
    ("n8n", re.compile(r"\bn8n\b", re.I)),
)


def normalize_category(value: str | None, text: str) -> str:
    candidate = (value or "").casefold().strip()
    known = {category for category, _ in CATEGORY_PATTERNS} | {"bots", "other"}
    if candidate in known and candidate != "other":
        return candidate
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return "other"


def normalize_technologies(values: list[str], text: str) -> list[str]:
    detected = {name for name, pattern in TECHNOLOGY_PATTERNS if pattern.search(text)}
    for value in values:
        normalized = normalize_text(value)
        if normalized:
            detected.add(normalized.casefold())
    return sorted(detected)


def normalize_customer_type(value: str, text: str) -> str:
    candidate = value.casefold().strip()
    if candidate != "unknown":
        return candidate
    normalized = text.casefold()
    if re.search(
        r"гос(?:ударственн|закуп)|министерств|муниципальн|бюджетн\w* учрежден", normalized
    ):
        return "government"
    if re.search(r"компан|бизнес|ооо|заказчик\s*[-—:]?\s*(?:юр|организац)", normalized):
        return "business"
    if re.search(r"частн\w* лиц|физическ\w* лиц", normalized):
        return "individual"
    return "unknown"
