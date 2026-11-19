from datetime import datetime, timezone
from typing import Any, Callable

import requests

from backend.shared.models import NormalizedEvent
from backend.shared.config import settings


class EventProviderError(RuntimeError):
    pass


def _get_json(url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any] | list[dict[str, Any]]:
    try:
        response = requests.get(url, params=params, headers=headers or {}, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise EventProviderError(f"event provider request failed: {exc}") from exc
    if not isinstance(payload, (dict, list)):
        raise EventProviderError("event provider returned unsupported payload")
    return payload


def _parse_ts(value: str | int | float | None) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def fetch_news(symbol: str) -> list[NormalizedEvent]:
    events = []
    if settings.finnhub_api_key:
        events.extend(_fetch_finnhub_news(symbol))
    if settings.newscatcher_api_key:
        events.extend(_fetch_newscatcher_news(symbol))
    if events:
        return events
    return [
        NormalizedEvent(
            source="newsapi_sample",
            event_type="news",
            symbol=symbol.upper(),
            timestamp=datetime.now(timezone.utc),
            confidence=0.65,
            payload={"headline": "Provider connector ready", "sentiment": "neutral"},
        )
    ]


def fetch_social_sentiment(symbol: str) -> list[NormalizedEvent]:
    events = []
    if settings.reddit_client_id and settings.reddit_client_secret:
        events.append(
            NormalizedEvent(
                source="reddit",
                event_type="social_sentiment",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.65,
                payload={"status": "credentials_configured", "score": 0.0},
            )
        )
    if settings.twitter_bearer_token:
        events.append(
            NormalizedEvent(
                source="twitter_x",
                event_type="social_sentiment",
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                confidence=0.65,
                payload={"status": "credentials_configured", "score": 0.0},
            )
        )
    if events:
        return events
    return [
        NormalizedEvent(
            source="reddit_x_sample",
            event_type="social_sentiment",
            symbol=symbol.upper(),
            timestamp=datetime.now(timezone.utc),
            confidence=0.55,
            payload={"score": 0.52},
        )
    ]


def fetch_insider_transactions(symbol: str) -> list[NormalizedEvent]:
    if settings.finnhub_api_key:
        payload = _get_json(
            "https://finnhub.io/api/v1/stock/insider-transactions",
            {"symbol": symbol.upper(), "token": settings.finnhub_api_key},
        )
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        return [
            NormalizedEvent(
                source="finnhub",
                event_type="insider_transaction",
                symbol=symbol.upper(),
                timestamp=_parse_ts(row.get("transactionDate")),
                confidence=0.75,
                payload=row,
            )
            for row in rows
        ]
    return [
        NormalizedEvent(
            source="insider_sample",
            event_type="insider_transaction",
            symbol=symbol.upper(),
            timestamp=datetime.now(timezone.utc),
            confidence=0.5,
            payload={"activity": "none"},
        )
    ]


def fetch_economic_calendar(symbol: str | None = None) -> list[NormalizedEvent]:
    if settings.macro_calendar_api_key:
        payload = _get_json(
            "https://api.tradingeconomics.com/calendar",
            {"c": settings.macro_calendar_api_key, "importance": "2,3"},
        )
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        return [
            NormalizedEvent(
                source="macro_calendar",
                event_type="economic_calendar",
                symbol=symbol.upper() if symbol else None,
                timestamp=_parse_ts(row.get("date") or row.get("Date")),
                confidence=0.7,
                payload=row,
            )
            for row in rows
        ]
    return [
        NormalizedEvent(
            source="macro_calendar_sample",
            event_type="economic_calendar",
            symbol=symbol.upper() if symbol else None,
            timestamp=datetime.now(timezone.utc),
            confidence=0.55,
            payload={"event": "calendar connector ready", "impact": "medium"},
        )
    ]


def ingest_recent_news(db=None, days_back: int = 30, symbols: list[str] | None = None) -> dict[str, int]:
    events = []
    for symbol in symbols or ["AAPL", "MSFT", "NVDA"]:
        events.extend(fetch_news(symbol))
    return {"events_ingested": len(events), "days_back": days_back}


def _fetch_finnhub_news(
    symbol: str,
    transport: Callable[[str, dict[str, Any], dict[str, str] | None], dict[str, Any] | list[dict[str, Any]]] = _get_json,
) -> list[NormalizedEvent]:
    payload = transport(
        "https://finnhub.io/api/v1/company-news",
        {"symbol": symbol.upper(), "token": settings.finnhub_api_key},
        None,
    )
    rows = payload if isinstance(payload, list) else payload.get("articles", payload.get("data", []))
    return [
        NormalizedEvent(
            source="finnhub",
            event_type="news",
            symbol=symbol.upper(),
            timestamp=_parse_ts(row.get("datetime") or row.get("publishedAt")),
            confidence=0.75,
            payload=row,
        )
        for row in rows
    ]


def _fetch_newscatcher_news(
    symbol: str,
    transport: Callable[[str, dict[str, Any], dict[str, str] | None], dict[str, Any] | list[dict[str, Any]]] = _get_json,
) -> list[NormalizedEvent]:
    payload = transport(
        "https://api.newscatcherapi.com/v2/search",
        {"q": symbol.upper(), "lang": "en", "sort_by": "date"},
        {"x-api-key": settings.newscatcher_api_key or ""},
    )
    rows = payload.get("articles", []) if isinstance(payload, dict) else payload
    return [
        NormalizedEvent(
            source="newscatcher",
            event_type="news",
            symbol=symbol.upper(),
            timestamp=_parse_ts(row.get("published_date")),
            confidence=0.7,
            payload=row,
        )
        for row in rows
    ]
