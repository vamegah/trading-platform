from fastapi import APIRouter

from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS

router = APIRouter()


@router.post("/commands/events", status_code=202)
async def enqueue_event_tracking(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.personalization_commands,
        EVENT_TYPES.personalization_event_track_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.personalization_event_track_requested,
        "result_topic": TOPICS.personalization_events,
        **result,
    }


@router.post("/commands/persona", status_code=202)
async def enqueue_persona_build(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.personalization_commands,
        EVENT_TYPES.personalization_persona_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.personalization_persona_requested,
        "result_topic": TOPICS.personalization_events,
        **result,
    }
