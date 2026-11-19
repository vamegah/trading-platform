from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable

import requests

from backend.shared.config import settings
from backend.shared.models import OHLCVBar, QuoteTick


class MarketDataProviderError(RuntimeError):
    pass


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        raise NotImplementedError

    @abstractmethod
    def latest_quote(self, symbol: str) -> QuoteTick:
        raise NotImplementedError


class PolygonProvider(MarketDataProvider):
    name = "polygon"
    base_url = "https://api.polygon.io"

    def __init__(
        self,
        api_key: str | None = None,
        fail: bool = False,
        transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.api_key = api_key
        self.fail = fail
        self.transport = transport or _requests_get_json

    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        if self.fail:
            raise MarketDataProviderError("polygon unavailable")
        if self.api_key:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}"
            payload = self.transport(
                url,
                {"adjusted": "true", "sort": "asc", "limit": 5000, "apiKey": self.api_key},
            )
            bars = []
            for row in payload.get("results", []):
                timestamp = datetime.fromtimestamp(row["t"] / 1000, tz=timezone.utc)
                bars.append(
                    OHLCVBar(
                        symbol=symbol.upper(),
                        timestamp=timestamp,
                        open=float(row["o"]),
                        high=float(row["h"]),
                        low=float(row["l"]),
                        close=float(row["c"]),
                        volume=float(row.get("v", 0)),
                        adjusted_close=float(row["c"]),
                        source=self.name,
                    )
                )
            if not bars:
                raise MarketDataProviderError("polygon returned no historical bars")
            return bars
        return _fallback_bars(symbol, self.name)

    def latest_quote(self, symbol: str) -> QuoteTick:
        if self.fail:
            raise MarketDataProviderError("polygon unavailable")
        if self.api_key:
            payload = self.transport(
                f"{self.base_url}/v2/last/nbbo/{symbol.upper()}",
                {"apiKey": self.api_key},
            )
            result = payload.get("results") or {}
            if not result:
                raise MarketDataProviderError("polygon returned no quote")
            timestamp_value = result.get("sip_timestamp") or result.get("participant_timestamp")
            timestamp = (
                datetime.fromtimestamp(timestamp_value / 1_000_000_000, tz=timezone.utc)
                if timestamp_value
                else datetime.now(timezone.utc)
            )
            return QuoteTick(
                symbol=symbol.upper(),
                timestamp=timestamp,
                bid=float(result.get("bid_price", 0)),
                ask=float(result.get("ask_price", 0)),
                bid_size=float(result.get("bid_size", 0)),
                ask_size=float(result.get("ask_size", 0)),
                source=self.name,
            )
        return _fallback_quote(symbol, self.name)


class AlphaVantageProvider(MarketDataProvider):
    name = "alpha_vantage"
    base_url = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: str | None = None,
        fail: bool = False,
        transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.api_key = api_key
        self.fail = fail
        self.transport = transport or _requests_get_json

    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        if self.fail:
            raise MarketDataProviderError("alpha_vantage unavailable")
        if self.api_key:
            payload = self.transport(
                self.base_url,
                {
                    "function": "TIME_SERIES_DAILY_ADJUSTED",
                    "symbol": symbol.upper(),
                    "apikey": self.api_key,
                    "outputsize": "full",
                },
            )
            series = payload.get("Time Series (Daily)") or {}
            bars = []
            start_dt = _parse_date(start)
            end_dt = _parse_date(end)
            for date_str, row in sorted(series.items()):
                date_value = _parse_date(date_str)
                if start_dt and date_value < start_dt:
                    continue
                if end_dt and date_value > end_dt:
                    continue
                bars.append(
                    OHLCVBar(
                        symbol=symbol.upper(),
                        timestamp=datetime.combine(date_value, datetime.min.time(), tzinfo=timezone.utc),
                        open=float(row["1. open"]),
                        high=float(row["2. high"]),
                        low=float(row["3. low"]),
                        close=float(row["4. close"]),
                        volume=float(row.get("6. volume", 0)),
                        adjusted_close=float(row.get("5. adjusted close", row["4. close"])),
                        source=self.name,
                    )
                )
            if not bars:
                raise MarketDataProviderError("alpha_vantage returned no historical bars")
            return bars
        return _fallback_bars(symbol, self.name)

    def latest_quote(self, symbol: str) -> QuoteTick:
        if self.fail:
            raise MarketDataProviderError("alpha_vantage unavailable")
        if self.api_key:
            payload = self.transport(
                self.base_url,
                {"function": "GLOBAL_QUOTE", "symbol": symbol.upper(), "apikey": self.api_key},
            )
            quote = payload.get("Global Quote") or {}
            if not quote:
                raise MarketDataProviderError("alpha_vantage returned no quote")
            price = float(quote.get("05. price", 0))
            return QuoteTick(
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                bid=price,
                ask=price,
                bid_size=0,
                ask_size=0,
                source=self.name,
            )
        return _fallback_quote(symbol, self.name)


class FinancialModelingPrepProvider(MarketDataProvider):
    name = "financial_modeling_prep"
    base_url = "https://financialmodelingprep.com/api/v3"

    def __init__(
        self,
        api_key: str | None = None,
        fail: bool = False,
        transport: Callable[[str, dict[str, Any]], dict[str, Any] | list[dict[str, Any]]] | None = None,
    ):
        self.api_key = api_key
        self.fail = fail
        self.transport = transport or _requests_get_json

    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        if self.fail:
            raise MarketDataProviderError("financial_modeling_prep unavailable")
        if self.api_key:
            payload = self.transport(
                f"{self.base_url}/historical-price-full/{symbol.upper()}",
                {"from": start, "to": end, "apikey": self.api_key},
            )
            rows = payload.get("historical", []) if isinstance(payload, dict) else []
            bars = [
                OHLCVBar(
                    symbol=symbol.upper(),
                    timestamp=datetime.combine(_parse_date(row["date"]), datetime.min.time(), tzinfo=timezone.utc),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
                    adjusted_close=float(row.get("adjClose", row["close"])),
                    source=self.name,
                )
                for row in sorted(rows, key=lambda item: item["date"])
            ]
            if not bars:
                raise MarketDataProviderError("financial_modeling_prep returned no historical bars")
            return bars
        return _fallback_bars(symbol, self.name)

    def latest_quote(self, symbol: str) -> QuoteTick:
        if self.fail:
            raise MarketDataProviderError("financial_modeling_prep unavailable")
        if self.api_key:
            payload = self.transport(
                f"{self.base_url}/quote/{symbol.upper()}",
                {"apikey": self.api_key},
            )
            rows = payload if isinstance(payload, list) else []
            if not rows:
                raise MarketDataProviderError("financial_modeling_prep returned no quote")
            price = float(rows[0].get("price", 0))
            return QuoteTick(
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                bid=price,
                ask=price,
                bid_size=0,
                ask_size=0,
                source=self.name,
            )
        return _fallback_quote(symbol, self.name)


class TwelveDataProvider(MarketDataProvider):
    name = "twelve_data"
    base_url = "https://api.twelvedata.com"

    def __init__(
        self,
        api_key: str | None = None,
        fail: bool = False,
        transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.api_key = api_key
        self.fail = fail
        self.transport = transport or _requests_get_json

    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        if self.fail:
            raise MarketDataProviderError("twelve_data unavailable")
        if self.api_key:
            payload = self.transport(
                f"{self.base_url}/time_series",
                {
                    "symbol": symbol.upper(),
                    "interval": "1day",
                    "start_date": start,
                    "end_date": end,
                    "apikey": self.api_key,
                },
            )
            values = payload.get("values", [])
            bars = [
                OHLCVBar(
                    symbol=symbol.upper(),
                    timestamp=datetime.strptime(row["datetime"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0),
                    adjusted_close=float(row["close"]),
                    source=self.name,
                )
                for row in sorted(values, key=lambda item: item["datetime"])
            ]
            if not bars:
                raise MarketDataProviderError("twelve_data returned no historical bars")
            return bars
        return _fallback_bars(symbol, self.name)

    def latest_quote(self, symbol: str) -> QuoteTick:
        if self.fail:
            raise MarketDataProviderError("twelve_data unavailable")
        if self.api_key:
            payload = self.transport(
                f"{self.base_url}/quote",
                {"symbol": symbol.upper(), "apikey": self.api_key},
            )
            price = float(payload.get("close") or payload.get("price") or 0)
            if price <= 0:
                raise MarketDataProviderError("twelve_data returned no quote")
            return QuoteTick(
                symbol=symbol.upper(),
                timestamp=datetime.now(timezone.utc),
                bid=price,
                ask=price,
                bid_size=0,
                ask_size=0,
                source=self.name,
            )
        return _fallback_quote(symbol, self.name)


class MarketDataManager:
    def __init__(self, providers: list[MarketDataProvider]):
        self.providers = providers
        self.last_used_provider: str | None = None
        self.provider_errors: list[str] = []
        self.attempted_providers: list[str] = []

    def historical_bars(self, symbol: str, start: str, end: str) -> list[OHLCVBar]:
        self.provider_errors = []
        self.attempted_providers = []
        for provider in self.providers:
            self.attempted_providers.append(provider.name)
            try:
                bars = provider.historical_bars(symbol, start, end)
                if bars:
                    self.last_used_provider = provider.name
                    return bars
            except Exception as exc:
                self.provider_errors.append(f"{provider.name}: {exc}")
        raise MarketDataProviderError("; ".join(self.provider_errors) or "no providers configured")

    def latest_quote(self, symbol: str) -> QuoteTick:
        self.provider_errors = []
        self.attempted_providers = []
        for provider in self.providers:
            self.attempted_providers.append(provider.name)
            try:
                quote = provider.latest_quote(symbol)
                self.last_used_provider = provider.name
                return quote
            except Exception as exc:
                self.provider_errors.append(f"{provider.name}: {exc}")
        raise MarketDataProviderError("; ".join(self.provider_errors) or "no providers configured")

    def status(self) -> dict[str, object]:
        return {
            "providers": [provider.name for provider in self.providers],
            "attempted_providers": list(self.attempted_providers),
            "last_used_provider": self.last_used_provider,
            "provider_errors": list(self.provider_errors),
            "failover_used": bool(self.provider_errors and self.last_used_provider),
        }


def _sample_bars(symbol: str, source: str) -> list[OHLCVBar]:
    now = datetime.now(timezone.utc)
    return [
        OHLCVBar(
            symbol=symbol.upper(),
            timestamp=now,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=1000000,
            adjusted_close=101.0,
            source=source,
        )
    ]


def _sample_quote(symbol: str, source: str) -> QuoteTick:
    return QuoteTick(
        symbol=symbol.upper(),
        timestamp=datetime.now(timezone.utc),
        bid=100.95,
        ask=101.05,
        bid_size=500,
        ask_size=450,
        source=source,
    )


def _fallback_bars(symbol: str, source: str) -> list[OHLCVBar]:
    if _sample_data_allowed():
        return _sample_bars(symbol, source)
    raise MarketDataProviderError(f"{source} API key is required in production mode")


def _fallback_quote(symbol: str, source: str) -> QuoteTick:
    if _sample_data_allowed():
        return _sample_quote(symbol, source)
    raise MarketDataProviderError(f"{source} API key is required in production mode")


def _sample_data_allowed() -> bool:
    return not (
        settings.is_production
        or settings.live_trading_enabled
        or settings.require_live_integrations
    )


def _requests_get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise MarketDataProviderError(f"provider request failed: {exc}") from exc
    if isinstance(payload, dict) and ("Error Message" in payload or "Note" in payload):
        raise MarketDataProviderError(str(payload.get("Error Message") or payload.get("Note")))
    if not isinstance(payload, (dict, list)):
        raise MarketDataProviderError("provider returned unsupported payload")
    return payload


def _parse_date(value: str):
    if value in {"latest", ""}:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_market_data_manager(
    primary_failed: bool = False,
    secondary_failed: bool = False,
) -> MarketDataManager:
    return MarketDataManager(
        [
            PolygonProvider(api_key=settings.polygon_api_key, fail=primary_failed),
            FinancialModelingPrepProvider(api_key=settings.fmp_api_key),
            TwelveDataProvider(api_key=settings.twelve_data_api_key),
            AlphaVantageProvider(api_key=settings.alpha_vantage_api_key, fail=secondary_failed),
        ]
    )
