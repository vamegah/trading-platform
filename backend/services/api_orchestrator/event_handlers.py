from typing import Any

from backend.data_pipeline.ingestion.orchestrator import data_orchestrator
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_quote_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        quote = await data_orchestrator.get_quote(
            str(payload["symbol"]).upper(),
            payload.get("asset_class", "equity"),
        )
        return event_bus.publish(
            TOPICS.external_api_events,
            EVENT_TYPES.quote_received,
            quote,
            source="external_api_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.external_api_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.quote_requested, "error": str(exc), "request": payload},
            source="external_api_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


async def handle_news_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    try:
        news = await data_orchestrator.get_news(str(payload["symbol"]).upper())
        return event_bus.publish(
            TOPICS.external_api_events,
            EVENT_TYPES.news_received,
            news,
            source="external_api_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )
    except Exception as exc:
        return event_bus.publish(
            TOPICS.external_api_events,
            EVENT_TYPES.command_failed,
            {"command": EVENT_TYPES.news_requested, "error": str(exc), "request": payload},
            source="external_api_orchestrator",
            correlation_id=envelope.get("correlation_id"),
            causation_id=envelope.get("event_id"),
        )


EXTERNAL_API_EVENT_HANDLERS = {
    EVENT_TYPES.quote_requested: handle_quote_requested,
    EVENT_TYPES.news_requested: handle_news_requested,
}
