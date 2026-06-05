from backend.data_pipeline.ingestion.providers import MarketDataManager, get_market_data_manager
from backend.data_pipeline.ingestion.orchestrator import data_orchestrator


def fetch_market_data(symbols: list[str], manager: MarketDataManager | None = None) -> list[dict]:
    data_manager = manager or get_market_data_manager()
    rows = []
    for symbol in symbols:
        rows.extend(bar.model_dump() for bar in data_manager.historical_bars(symbol, "latest", "latest"))
    return rows


def fetch_latest_quote(symbol: str, manager: MarketDataManager | None = None) -> dict:
    data_manager = manager or get_market_data_manager()
    return data_manager.latest_quote(symbol).model_dump()


async def fetch_latest_quote_orchestrated(symbol: str, asset_class: str = "equity") -> dict:
    return await data_orchestrator.get_quote(symbol, asset_class)


def ingest_historical_market_data(db=None, years_back: int = 10, symbols: list[str] | None = None) -> dict[str, object]:
    rows = fetch_market_data(symbols or ["AAPL", "MSFT", "NVDA"])
    return {"rows": rows, "rows_ingested": len(rows), "years_back": years_back}
