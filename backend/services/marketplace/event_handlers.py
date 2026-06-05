from dataclasses import asdict
from typing import Any

from backend.services.marketplace.models import AgentSubscription, MarketplaceAgent
from backend.services.marketplace.routers.agents import _AGENTS
from backend.services.marketplace.routers.subscriptions import _SUBSCRIPTIONS
from backend.services.marketplace.vetting import vet_agent_manifest
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_agent_publish_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        agent = MarketplaceAgent(**payload)
        vetting = vet_agent_manifest(payload)
        agent.status = "approved" if vetting["approved"] else "pending_review"
        _AGENTS[agent.id] = agent
        return event_bus.publish(
            TOPICS.marketplace_events,
            EVENT_TYPES.marketplace_agent_published,
            {"agent": asdict(agent), "vetting": vetting},
            source="marketplace_service",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.marketplace_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.marketplace_agent_publish_requested, "error": str(exc), "request": payload},
            source="marketplace_service",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


async def handle_subscription_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        subscription = AgentSubscription(**payload)
        _SUBSCRIPTIONS.append(subscription)
        return event_bus.publish(
            TOPICS.marketplace_events,
            EVENT_TYPES.marketplace_subscription_created,
            {"subscription": asdict(subscription)},
            source="marketplace_service",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.marketplace_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.marketplace_subscription_requested, "error": str(exc), "request": payload},
            source="marketplace_service",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


MARKETPLACE_EVENT_HANDLERS = {
    EVENT_TYPES.marketplace_agent_publish_requested: handle_agent_publish_requested,
    EVENT_TYPES.marketplace_subscription_requested: handle_subscription_requested,
}
