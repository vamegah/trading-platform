from typing import Any

from backend.services.personalization.event_tracker import track_event
from backend.services.personalization.persona_engine import build_persona
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_event_track_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        result = track_event(payload)
        return event_bus.publish(
            TOPICS.personalization_events,
            EVENT_TYPES.personalization_event_tracked,
            result,
            source="personalization_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.personalization_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.personalization_event_track_requested, "error": str(exc), "request": payload},
            source="personalization_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


async def handle_persona_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        result = build_persona(str(payload["user_id"]))
        return event_bus.publish(
            TOPICS.personalization_events,
            EVENT_TYPES.personalization_persona_built,
            result,
            source="personalization_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.personalization_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.personalization_persona_requested, "error": str(exc), "request": payload},
            source="personalization_engine",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


PERSONALIZATION_EVENT_HANDLERS = {
    EVENT_TYPES.personalization_event_track_requested: handle_event_track_requested,
    EVENT_TYPES.personalization_persona_requested: handle_persona_requested,
}
