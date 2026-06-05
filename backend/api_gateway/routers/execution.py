from fastapi import APIRouter

from backend.services.execution_service.broker_registry import get_broker, list_broker_capabilities
from backend.services.execution_service.order_router import (
    AlmgrenChrissImpactModel,
    OrderRouter,
    execution_precheck,
    route_order,
)
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import OrderRequest

router = APIRouter()


@router.post("/orders")
async def submit_order(order: OrderRequest) -> dict[str, str | float]:
    return route_order(order)


@router.post("/impact")
async def estimate_impact(order: OrderRequest, current_price: float = 100.0) -> dict[str, float]:
    estimate = AlmgrenChrissImpactModel().estimate(
        symbol=order.symbol,
        order_size=order.quantity,
        side=order.side,
        current_price=current_price,
    )
    return estimate.__dict__


@router.post("/precheck")
async def precheck_order(payload: dict) -> dict[str, object]:
    return execution_precheck(payload)


@router.get("/brokers")
async def brokers(mode: str = "sandbox") -> list[dict[str, object]]:
    return list_broker_capabilities(mode)


@router.post("/smart-route")
async def smart_route(payload: dict) -> dict[str, object]:
    precheck = execution_precheck(payload)
    if not precheck["allowed"]:
        return {"status": "rejected", "precheck": precheck}
    broker = get_broker(payload.get("broker", "alpaca"), payload.get("broker_mode", "sandbox"))
    return await OrderRouter(broker).smart_route(
        symbol=payload["symbol"],
        side=payload.get("side", "BUY"),
        quantity=float(payload["quantity"]),
        asset_type=payload.get("asset_type", "equity"),
        order_type=payload.get("order_type", "MARKET"),
        urgency=payload.get("urgency", "normal"),
        current_price=float(payload.get("current_price", 100.0)),
        daily_volume=float(payload.get("daily_volume", 1_000_000)),
        limit_price=float(payload["limit_price"]) if payload.get("limit_price") is not None else None,
        stop_price=float(payload["stop_price"]) if payload.get("stop_price") is not None else None,
    )


@router.post("/commands/smart-route", status_code=202)
async def enqueue_smart_route(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.execution_commands,
        EVENT_TYPES.order_route_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.order_route_requested,
        "result_topic": TOPICS.execution_events,
        **result,
    }


@router.get("/brokers/{broker_name}/account")
async def broker_account(broker_name: str, mode: str = "sandbox") -> dict[str, object]:
    broker = get_broker(broker_name, mode)
    return {
        "broker": broker_name,
        "mode": mode,
        "balances": await broker.get_balances(),
        "positions": await broker.get_positions(),
        "capabilities": broker.capabilities().__dict__,
    }
