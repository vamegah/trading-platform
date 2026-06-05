from fastapi import APIRouter, HTTPException

from backend.services.safety_service.circuit_breaker import CircuitBreaker
from backend.services.execution_service.order_router import route_order
from backend.shared.models import OrderRequest

router = APIRouter()
breaker = CircuitBreaker()


@router.post("/orders")
async def submit_order(order: OrderRequest) -> dict[str, str | float]:
    if not breaker.is_trading_allowed():
        raise HTTPException(status_code=403, detail="Trading halted by circuit breaker")
    return route_order(order)


@router.get("/risk")
async def get_risk_metrics() -> dict[str, object]:
    return {"var": 0.0, "cvar": 0.0, "limits": {"kill_switch_active": not breaker.is_trading_allowed()}}


@router.post("/risk/kill-switch")
async def toggle_kill_switch(active: bool) -> dict[str, object]:
    if active:
        return breaker.trigger_halt("manual gateway request", admin_id="gateway")
    return breaker.resume_trading(admin_id="gateway")
