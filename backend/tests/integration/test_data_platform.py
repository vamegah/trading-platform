from datetime import date, datetime, timedelta, timezone

import pytest

from backend.data_pipeline.cleaning.corporate_actions import adjust_for_corporate_actions
from backend.data_pipeline.cleaning.data_quality import validate_rows
from backend.data_pipeline.cron_jobs.daily_sync import IngestionScheduler, run_intraday_sync
from backend.data_pipeline.ingestion.alt_data import AlternativeDataFeed, default_alt_data_registry
from backend.data_pipeline.ingestion.market_data import fetch_latest_quote
from backend.data_pipeline.ingestion.news import fetch_economic_calendar
from backend.data_pipeline.ingestion.providers import AlphaVantageProvider, MarketDataManager, PolygonProvider
from backend.data_pipeline.ingestion.security_master import SecurityMasterStore, universe_as_of
from backend.data_pipeline.lake.feature_store import publish_features
from backend.data_pipeline.lake.processed_store import write_processed_dataset
from backend.data_pipeline.lake.raw_store import write_raw_dataset
from backend.shared.models import CorporateActionEvent, NormalizedEvent, OHLCVBar, QuoteTick, VolumeSnapshot


def test_market_data_provider_failover_uses_secondary() -> None:
    manager = MarketDataManager([PolygonProvider(fail=True), AlphaVantageProvider()])
    quote = fetch_latest_quote("MSFT", manager)

    assert quote["source"] == "alpha_vantage"
    assert manager.last_used_provider == "alpha_vantage"
    assert manager.status()["failover_used"] is True
    assert "polygon" in manager.status()["attempted_providers"]


def test_polygon_provider_uses_authenticated_http_payloads() -> None:
    calls = []

    def transport(url: str, params: dict) -> dict:
        calls.append((url, params))
        if "/aggs/" in url:
            return {"results": [{"t": 1715731200000, "o": 100, "h": 102, "l": 99, "c": 101, "v": 1000}]}
        return {"results": {"sip_timestamp": 1715731200000000000, "bid_price": 100.9, "ask_price": 101.1, "bid_size": 4, "ask_size": 5}}

    provider = PolygonProvider(api_key="polygon-key", transport=transport)
    bars = provider.historical_bars("msft", "2024-05-15", "2024-05-15")
    quote = provider.latest_quote("msft")

    assert bars[0].source == "polygon"
    assert quote.ask == 101.1
    assert calls[0][1]["apiKey"] == "polygon-key"
    assert calls[1][1]["apiKey"] == "polygon-key"


def test_alpha_vantage_provider_uses_authenticated_http_payloads() -> None:
    calls = []

    def transport(url: str, params: dict) -> dict:
        calls.append((url, params))
        if params["function"] == "GLOBAL_QUOTE":
            return {"Global Quote": {"05. price": "123.45"}}
        return {
            "Time Series (Daily)": {
                "2024-05-15": {
                    "1. open": "120",
                    "2. high": "125",
                    "3. low": "119",
                    "4. close": "123",
                    "5. adjusted close": "122",
                    "6. volume": "10000",
                }
            }
        }

    provider = AlphaVantageProvider(api_key="alpha-key", transport=transport)
    bars = provider.historical_bars("msft", "2024-05-15", "2024-05-15")
    quote = provider.latest_quote("msft")

    assert bars[0].adjusted_close == 122
    assert quote.bid == 123.45
    assert all(call[1]["apikey"] == "alpha-key" for call in calls)


def test_normalized_market_and_event_schemas_validate() -> None:
    bar = OHLCVBar(
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        open=1,
        high=2,
        low=1,
        close=2,
        volume=100,
        source="test",
    )
    event = NormalizedEvent(
        source="test",
        event_type="news",
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        confidence=0.8,
    )

    assert bar.symbol == "AAPL"
    assert event.confidence == 0.8


def test_normalized_market_schemas_reject_inconsistent_payloads() -> None:
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        OHLCVBar(symbol="AAPL", timestamp=timestamp, open=10, high=9, low=8, close=10, volume=100, source="test")

    with pytest.raises(ValueError):
        QuoteTick(symbol="AAPL", timestamp=timestamp, bid=101, ask=100, source="test")

    volume = VolumeSnapshot(symbol="msft", timestamp=timestamp, volume=1000, average_volume=900, source="test")
    event = NormalizedEvent(source="test", event_type="news", symbol="msft", timestamp=timestamp, confidence=0.7)

    assert volume.symbol == "MSFT"
    assert event.source_timestamp == timestamp


def test_security_master_includes_delisted_point_in_time_membership() -> None:
    store = SecurityMasterStore()

    assert store.get("ENRNQ", date(2000, 1, 1)) is not None
    assert store.get("ENRNQ", date(2002, 1, 1)) is None
    assert "LEHMQ" in universe_as_of(date(2007, 1, 1))


def test_corporate_action_adjustments_cover_split_dividend_and_symbol_change() -> None:
    bar = OHLCVBar(
        symbol="ABC",
        timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        open=100,
        high=110,
        low=90,
        close=100,
        volume=1000,
        source="test",
    )
    adjusted = adjust_for_corporate_actions(
        [bar],
        [
            CorporateActionEvent(symbol="ABC", effective_date=date(2020, 2, 1), action_type="split", ratio=2),
            CorporateActionEvent(symbol="ABC", effective_date=date(2020, 3, 1), action_type="dividend", cash_amount=1),
            CorporateActionEvent(symbol="ABC", effective_date=date(2019, 12, 1), action_type="symbol_change", new_symbol="XYZ"),
        ],
    )

    assert adjusted[0].close == 50
    assert adjusted[0].adjusted_close == 49
    assert adjusted[0].symbol == "XYZ"


def test_corporate_action_adjustments_ignore_unrelated_symbols() -> None:
    bar = OHLCVBar(
        symbol="ABC",
        timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        open=100,
        high=110,
        low=90,
        close=100,
        volume=1000,
        source="test",
    )
    adjusted = adjust_for_corporate_actions(
        [bar],
        [CorporateActionEvent(symbol="OTHER", effective_date=date(2020, 2, 1), action_type="split", ratio=2)],
    )

    assert adjusted[0].close == 100


def test_data_quality_blocks_missing_stale_outlier_and_lookahead() -> None:
    report = validate_rows(
        [
            {
                "timestamp": datetime.now(timezone.utc) + timedelta(days=1),
                "open": None,
                "high": 1,
                "low": 2,
                "close": -1,
                "volume": 0,
            }
        ],
        as_of=datetime.now(timezone.utc),
    )

    assert report["blocked"] is True
    assert report["lookahead"] == 1


def test_lake_writes_include_version_source_schema_and_timestamp() -> None:
    rows = [{"timestamp": datetime.now(timezone.utc), "symbol": "AAPL", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}]
    raw = write_raw_dataset("market", rows, version="v1", source="test")
    processed = write_processed_dataset("market_clean", rows, version="v1", source=raw["manifest"]["dataset_id"])
    features = publish_features("signals", [{"symbol": "AAPL", "feature": 1}], version="v1", source="test")

    assert raw["schema_hash"]
    assert raw["content_hash"]
    assert raw["written_at"]
    assert processed["layer"] == "processed"
    assert processed["processed_at"]
    assert processed["manifest"]["source"] == raw["manifest"]["dataset_id"]
    assert features["schema_hash"]
    assert features["published_at"]


def test_alt_data_registry_accepts_new_feed_without_orchestrator_change() -> None:
    class CustomFeed(AlternativeDataFeed):
        name = "custom"

        def fetch(self, symbol: str) -> list[NormalizedEvent]:
            return [
                NormalizedEvent(
                    source=self.name,
                    event_type="custom",
                    symbol=symbol,
                    timestamp=datetime.now(timezone.utc),
                    confidence=0.5,
                )
            ]

    registry = default_alt_data_registry()
    registry.register(CustomFeed())

    assert any(event.source == "custom" for event in registry.fetch_all("AAPL"))


def test_economic_calendar_connector_returns_normalized_events() -> None:
    events = fetch_economic_calendar("AAPL")

    assert events
    assert events[0].event_type == "economic_calendar"
    assert events[0].source_timestamp is not None


def test_ingestion_scheduler_is_idempotent_and_dead_letters_failures() -> None:
    scheduler = IngestionScheduler(max_retries=1)
    first = scheduler.run_once("job-1", ["AAPL"])
    duplicate = scheduler.run_once("job-1", ["AAPL"])
    failed = scheduler.run_once("job-2", ["FAIL"])

    assert first.status == "completed"
    assert duplicate.status == "skipped_duplicate"
    assert failed.dead_lettered is True
    assert scheduler.dead_letters
    assert scheduler.metrics["jobs_completed"] == 1
    assert scheduler.metrics["dead_letters_total"] == 1


def test_intraday_ingestion_reports_window_and_metrics() -> None:
    result = run_intraday_sync(["MSFT"], window="5m")

    assert result["window"] == "5m"
    assert result["status"] == "completed"
    assert result["metrics"]["jobs_completed"] == 1
