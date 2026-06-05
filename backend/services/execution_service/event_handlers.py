from typing import Any

from backend.services.execution_service.broker_registry import get_broker
from backend.services.execution_service.order_router import OrderRouter, execution_precheck
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_order_route_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    precheck = execution_precheck(payload)
    if not precheck["allowed"]:
        return event_bus.publish(
            TOPICS.execution_events,
            EVENT_TYPES.order_rejected,
            {"precheck": precheck, "request": payload},
            source="execution_service",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )

    broker = get_broker(payload.get("broker", "alpaca"), payload.get("broker_mode", "sandbox"))
    result = await OrderRouter(broker).smart_route(
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
    return event_bus.publish(
        TOPICS.execution_events,
        EVENT_TYPES.order_routed,
        result,
        source="execution_service",
        correlation_id=envelope.get("correlation_id"),
        causation_id=envelope.get("event_id"),
    )


EXECUTION_EVENT_HANDLERS = {
    EVENT_TYPES.order_route_requested: handle_order_route_requested,
}
