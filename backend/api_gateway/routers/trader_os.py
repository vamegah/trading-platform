from fastapi import APIRouter

from backend.services.trader_operating_system import (
    add_journal_plan,
    broker_reconciliation,
    cancel_order,
    compliance_center,
    copilot_response,
    event_calendar,
    execution_quality,
    margin_snapshot,
    market_replay,
    options_approval,
    options_suite,
    order_blotter,
    portfolio_command_center,
    replay_trade,
    replace_order,
    submit_order_ticket,
    trade_journal_v2,
    watchlists_and_heatmaps,
)

router = APIRouter()


@router.get("/command-center")
async def command_center() -> dict[str, object]:
    return portfolio_command_center()


@router.get("/orders")
async def orders() -> dict[str, object]:
    return order_blotter()


@router.post("/orders")
async def submit_order(payload: dict) -> dict[str, object]:
    return submit_order_ticket(payload)


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: str) -> dict[str, object]:
    return cancel_order(order_id)


@router.post("/orders/{order_id}/replace")
async def replace(order_id: str, payload: dict) -> dict[str, object]:
    return replace_order(order_id, payload)


@router.get("/options/{symbol}")
async def options(symbol: str) -> dict[str, object]:
    return options_suite(symbol)


@router.post("/options/approval")
async def approve_options(payload: dict) -> dict[str, object]:
    return options_approval(payload)


@router.post("/margin")
async def margin(payload: dict) -> dict[str, object]:
    return margin_snapshot(payload)


@router.get("/execution-quality")
async def fill_quality() -> dict[str, object]:
    return execution_quality()


@router.get("/replay/{symbol}")
async def replay(symbol: str, session_date: str | None = None) -> dict[str, object]:
    return market_replay(symbol, session_date)


@router.post("/replay/trades")
async def simulated_replay_trade(payload: dict) -> dict[str, object]:
    return replay_trade(payload)


@router.get("/watchlists")
async def watchlists() -> dict[str, object]:
    return watchlists_and_heatmaps()


@router.get("/events")
async def events() -> dict[str, object]:
    return event_calendar()


@router.get("/journal")
async def journal() -> dict[str, object]:
    return trade_journal_v2()


@router.post("/journal")
async def journal_plan(payload: dict) -> dict[str, object]:
    return add_journal_plan(payload)


@router.post("/copilot")
async def copilot(payload: dict) -> dict[str, object]:
    return copilot_response(payload)


@router.get("/compliance-center")
async def compliance() -> dict[str, object]:
    return compliance_center()


@router.get("/reconciliation")
async def reconciliation() -> dict[str, object]:
    return broker_reconciliation()
