from typing import Any

from backend.services.backtest_engine.backtest_engine import full_walkforward_backtest
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_walk_forward_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        result = await full_walkforward_backtest(
            symbol=str(payload.get("symbol", "MSFT")).upper(),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            days=int(payload.get("days", 252)),
        )
        return event_bus.publish(
            TOPICS.backtest_events,
            EVENT_TYPES.backtest_completed,
            result,
            source="backtest_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.backtest_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.backtest_walk_forward_requested, "error": str(exc), "request": payload},
            source="backtest_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


BACKTEST_EVENT_HANDLERS = {
    EVENT_TYPES.backtest_walk_forward_requested: handle_walk_forward_requested,
}
