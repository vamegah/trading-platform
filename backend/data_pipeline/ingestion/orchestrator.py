import asyncio
from typing import Any

from backend.data_pipeline.ingestion.news import fetch_news
from backend.data_pipeline.ingestion.providers import (
    AlphaVantageProvider,
    FinancialModelingPrepProvider,
    MarketDataProvider,
    PolygonProvider,
    TwelveDataProvider,
)
from backend.shared.config import settings
from backend.shared.external_api.cache import stale_while_revalidate
from backend.shared.external_api.config_loader import load_external_api_config
from backend.shared.external_api.router import ExternalAPIRouter, external_api_router


class AllProvidersFailedError(RuntimeError):
    pass


class DataOrchestrator:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        router: ExternalAPIRouter | None = None,
        providers: dict[str, MarketDataProvider] | None = None,
    ) -> None:
        self.config = config or load_external_api_config()
        self.router = router or external_api_router
        self.providers = providers or {
            "polygon": PolygonProvider(api_key=settings.polygon_api_key),
            "financial_modeling_prep": FinancialModelingPrepProvider(api_key=settings.fmp_api_key),
            "twelve_data": TwelveDataProvider(api_key=settings.twelve_data_api_key),
            "alpha_vantage": AlphaVantageProvider(api_key=settings.alpha_vantage_api_key),
        }

    async def get_quote(self, symbol: str, asset_class: str = "equity") -> dict[str, Any]:
        section = self.config.get(f"{asset_class}_market_data", self.config.get("equity_market_data", {}))
        ttl = int(section.get("ttl_seconds", 5))
        stale_ttl = int(section.get("stale_ttl_seconds", 60))
        cache_key = f"quote:{asset_class}:{symbol.upper()}"

        async def producer() -> dict[str, Any]:
            result = await self._fetch_quote_from_chain(symbol, section)
            return result

        cached = await stale_while_revalidate(cache_key, ttl, stale_ttl, producer)
        value = dict(cached.value)
        value["cache"] = {"hit": cached.hit, "stale": cached.stale}
        return value

    async def get_news(self, symbol: str) -> dict[str, Any]:
        section = self.config.get("news_sentiment", {})
        cache_key = f"news:{symbol.upper()}"

        async def producer() -> list[dict[str, Any]]:
            providers = [section.get("primary"), *section.get("parallel", [])]
            calls = [self._fetch_news(provider, symbol, section) for provider in providers if provider]
            nested = await asyncio.gather(*calls, return_exceptions=True)
            rows: list[dict[str, Any]] = []
            seen: set[str] = set()
            for result in nested:
                if isinstance(result, Exception):
                    continue
                for event in result:
                    key = event.get("payload", {}).get("url") or event.get("payload", {}).get("headline") or str(event)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(event)
            return rows

        cached = await stale_while_revalidate(cache_key, int(section.get("ttl_seconds", 60)), 300, producer)
        return {"symbol": symbol.upper(), "events": cached.value, "cache": {"hit": cached.hit, "stale": cached.stale}}

    async def _fetch_quote_from_chain(self, symbol: str, section: dict[str, Any]) -> dict[str, Any]:
        chain = [section.get("primary"), *section.get("failover", [])]
        errors: list[str] = []
        for provider_name in [name for name in chain if name]:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            provider_config = section.get("providers", {}).get(provider_name, {})
            try:
                quote = await self.router.call(
                    provider_name,
                    "latest_quote",
                    lambda provider=provider: asyncio.to_thread(provider.latest_quote, symbol),
                    timeout_ms=int(provider_config.get("timeout_ms", 1000)),
                    rate_limit_per_minute=int(provider_config.get("requests_per_minute", 60)),
                    priority="realtime",
                    audit_payload={"symbol": symbol.upper(), "asset_class": section.get("asset_class", "equity")},
                )
                return quote.model_dump() if hasattr(quote, "model_dump") else quote.dict()
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")
        raise AllProvidersFailedError("; ".join(errors) or "no quote providers configured")

    async def _fetch_news(self, provider_name: str, symbol: str, section: dict[str, Any]) -> list[dict[str, Any]]:
        provider_config = section.get("providers", {}).get(provider_name, {})
        events = await self.router.call(
            provider_name,
            "news",
            lambda: asyncio.to_thread(fetch_news, symbol),
            timeout_ms=int(provider_config.get("timeout_ms", 1000)),
            rate_limit_per_minute=int(provider_config.get("requests_per_minute", 60)),
            audit_payload={"symbol": symbol.upper()},
        )
        return [event.model_dump() if hasattr(event, "model_dump") else event.dict() for event in events]


data_orchestrator = DataOrchestrator()
