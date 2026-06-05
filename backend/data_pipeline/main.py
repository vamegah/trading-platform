import logging
from datetime import datetime, timezone

from backend.data_pipeline.cleaning.data_quality import run_data_quality_checks
from backend.data_pipeline.cron_jobs.daily_sync import run_daily_sync

logger = logging.getLogger(__name__)


def run_initial_ingestion(symbols: list[str] | None = None) -> dict[str, object]:
    universe = symbols or ["AAPL", "MSFT", "NVDA"]
    logger.info("starting_initial_ingestion symbols=%s", ",".join(universe))
    sync_result = run_daily_sync(universe)
    quality = run_data_quality_checks(
        rows=[{"timestamp": datetime.now(timezone.utc), "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}]
    )
    return {
        "status": "complete",
        "symbols": universe,
        "sync": sync_result,
        "quality": quality,
    }


def run_daily_ingestion(symbols: list[str] | None = None) -> dict[str, object]:
    universe = symbols or ["AAPL", "MSFT", "NVDA"]
    logger.info("starting_daily_ingestion symbols=%s", ",".join(universe))
    return run_daily_sync(universe)


if __name__ == "__main__":
    print(run_initial_ingestion())
