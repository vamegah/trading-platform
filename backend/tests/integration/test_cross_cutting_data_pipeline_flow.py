import pytest

from backend.data_pipeline.cleaning.data_quality import quality_gate_or_raise, validate_rows
from backend.data_pipeline.ingestion.stream_ingestion import polygon_stock_stream
from backend.data_pipeline.lake.feature_store import publish_features
from backend.data_pipeline.lake.raw_store import write_raw_dataset


@pytest.mark.asyncio
async def test_ingestion_to_feature_publication_flow_is_reproducible() -> None:
    ticks = await polygon_stock_stream(
        [
            {"ev": "T", "sym": "msft", "p": 101.25, "t": "2026-05-15T14:30:00+00:00"},
            {"ev": "Q", "sym": "ignored", "p": 1},
        ]
    )
    quality = validate_rows(ticks)
    raw = write_raw_dataset("ticks", ticks, version="test-v1", source="polygon_stream")
    features = publish_features(
        "intraday_signal_features",
        [{"symbol": row["symbol"], "last_price": row["price"], "momentum_1m": 0.01} for row in ticks],
        version=raw["version"],
        source=raw["dataset"],
    )

    assert len(ticks) == 1
    assert quality["blocked"] is False
    assert raw["schema_hash"]
    assert raw["version"] == features["version"]
    assert features["rows_published"] == 1
    assert features["manifest"]["source"] == raw["dataset"]
    assert raw["manifest"]["lineage"]["source"] == "polygon_stream"


def test_invalid_dataset_is_blocked_before_processed_or_feature_publication() -> None:
    invalid_rows = [
        {
            "timestamp": "2026-05-15T14:30:00+00:00",
            "symbol": "MSFT",
            "open": 100,
            "high": 99,
            "low": 101,
            "close": -1,
            "volume": 0,
        }
    ]
    report = validate_rows(invalid_rows)

    assert report["blocked"] is True
    assert report["outliers"] >= 1
    with pytest.raises(ValueError):
        quality_gate_or_raise(invalid_rows)
    with pytest.raises(ValueError):
        publish_features(
            "blocked_features",
            [{"symbol": "MSFT", "last_price": -1}],
            quality_report=report,
        )
