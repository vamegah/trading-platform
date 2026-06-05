from fastapi import APIRouter, Query

from backend.services.backtest_engine.backtest_engine import full_walkforward_backtest
from backend.services.backtest_engine.walk_forward import run_walk_forward
from backend.shared.data_lake import record_data_lake_edge
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import BacktestRequest

router = APIRouter()


@router.get("/{symbol}")
async def run_backtest(symbol: str, days: int = Query(365)) -> dict[str, object]:
    result = run_walk_forward(
        BacktestRequest(
            strategy_id=f"{symbol.upper()}-demo",
            start_date=f"{days}_days_ago",
            end_date="today",
            universe=[symbol.upper()],
        )
    )
    return {
        **result.model_dump(),
        "database_edge": record_data_lake_edge("backtesting_engine", "read", f"historical_prices:{symbol.upper()}"),
    }


@router.post("/walk-forward")
async def walk_forward_backtest(payload: dict) -> dict[str, object]:
    return await full_walkforward_backtest(
        symbol=str(payload.get("symbol", "MSFT")).upper(),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        days=int(payload.get("days", 252)),
    )


@router.post("/commands/walk-forward", status_code=202)
async def enqueue_walk_forward_backtest(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.backtest_commands,
        EVENT_TYPES.backtest_walk_forward_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.backtest_walk_forward_requested,
        "result_topic": TOPICS.backtest_events,
        **result,
    }
