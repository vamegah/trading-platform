from backend.data_pipeline.ingestion.providers import (
    FinancialModelingPrepProvider,
    MarketDataManager,
    PolygonProvider,
    TwelveDataProvider,
)
from backend.shared.external_apis import list_external_api_status, missing_live_integrations


def test_external_api_catalog_contains_go_live_providers() -> None:
    names = {provider["name"] for provider in list_external_api_status()}

    assert {"polygon", "financial_modeling_prep", "twelve_data", "finnhub", "alpaca", "auth0", "sentry"}.issubset(names)
    assert "polygon" in missing_live_integrations()


def test_market_data_manager_routes_through_new_provider_failover() -> None:
    manager = MarketDataManager(
        [
            PolygonProvider(fail=True),
            FinancialModelingPrepProvider(),
            TwelveDataProvider(),
        ]
    )

    quote = manager.latest_quote("msft")

    assert quote.symbol == "MSFT"
    assert manager.last_used_provider == "financial_modeling_prep"


def test_fmp_provider_normalizes_http_payloads() -> None:
    def transport(url, params):
        if "historical-price-full" in url:
            return {
                "historical": [
                    {
                        "date": "2024-05-15",
                        "open": 100,
                        "high": 105,
                        "low": 99,
                        "close": 103,
                        "adjClose": 102.5,
                        "volume": 1000,
                    }
                ]
            }
        return [{"price": 103.25}]

    provider = FinancialModelingPrepProvider(api_key="fmp-key", transport=transport)

    bars = provider.historical_bars("msft", "2024-05-15", "2024-05-15")
    quote = provider.latest_quote("msft")

    assert bars[0].source == "financial_modeling_prep"
    assert bars[0].adjusted_close == 102.5
    assert quote.ask == 103.25


def test_twelve_data_provider_normalizes_http_payloads() -> None:
    def transport(url, params):
        if "time_series" in url:
            return {
                "values": [
                    {
                        "datetime": "2024-05-15",
                        "open": "100",
                        "high": "105",
                        "low": "99",
                        "close": "103",
                        "volume": "1000",
                    }
                ]
            }
        return {"close": "103.25"}

    provider = TwelveDataProvider(api_key="twelve-key", transport=transport)

    bars = provider.historical_bars("msft", "2024-05-15", "2024-05-15")
    quote = provider.latest_quote("msft")

    assert bars[0].source == "twelve_data"
    assert bars[0].close == 103
    assert quote.bid == 103.25
