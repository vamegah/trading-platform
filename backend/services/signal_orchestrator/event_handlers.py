from typing import Any

from backend.services.signal_orchestrator.orchestrator import generate_signal
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_signal_evaluate_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        signal = await generate_signal(
            str(payload["symbol"]).upper(),
            payload.get("portfolio_context"),
        )
        return event_bus.publish(
            TOPICS.signal_events,
            EVENT_TYPES.signal_generated,
            signal,
            source="signal_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.signal_events,
            EVENT_TYPES.signal_failed,
            {"symbol": payload.get("symbol"), "error": str(exc)},
            source="signal_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


SIGNAL_EVENT_HANDLERS = {
    EVENT_TYPES.signal_evaluate_requested: handle_signal_evaluate_requested,
}
