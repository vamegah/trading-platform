from fastapi import APIRouter

from backend.services.paper_trading import account
from backend.services.execution_service.trade_journal import journal
from backend.services.signal_orchestrator.orchestrator import generate_signal

router = APIRouter()


@router.get("/balance")
async def get_balance() -> dict[str, object]:
    return account.get_balance()


@router.post("/execute/{symbol}")
async def execute_signal(symbol: str) -> dict[str, object]:
    signal = await generate_signal(symbol.upper())
    return await account.execute_signal_async(signal)


@router.get("/trades")
async def get_trades() -> dict[str, list[dict]]:
    return {"trades": account.trades}


@router.get("/journal")
async def get_journal() -> dict[str, list[dict]]:
    return {"entries": journal.list_entries()}
