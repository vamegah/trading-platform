from fastapi import APIRouter

from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS

router = APIRouter()


@router.post("/commands/agents/publish", status_code=202)
async def enqueue_agent_publish(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.marketplace_commands,
        EVENT_TYPES.marketplace_agent_publish_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.marketplace_agent_publish_requested,
        "result_topic": TOPICS.marketplace_events,
        **result,
    }


@router.post("/commands/subscriptions", status_code=202)
async def enqueue_subscription(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.marketplace_commands,
        EVENT_TYPES.marketplace_subscription_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.marketplace_subscription_requested,
        "result_topic": TOPICS.marketplace_events,
        **result,
    }
