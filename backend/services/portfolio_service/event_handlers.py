from typing import Any

from backend.services.portfolio_service.risk_monitor import LiveRiskMonitor, RiskLimits
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS


async def handle_portfolio_risk_requested(envelope: dict[str, Any]) -> dict[str, object]:
    payload = envelope.get("payload", {})
    limits_payload = payload.get("limits") or {}
    limits = RiskLimits(**limits_payload) if limits_payload else RiskLimits()
    result = LiveRiskMonitor().evaluate(payload.get("portfolio", []), limits)
    return event_bus.publish(
        TOPICS.portfolio_events,
        EVENT_TYPES.portfolio_risk_evaluated,
        result,
        source="portfolio_service",
        correlation_id=envelope.get("correlation_id"),
        causation_id=envelope.get("event_id"),
    )


PORTFOLIO_EVENT_HANDLERS = {
    EVENT_TYPES.portfolio_risk_requested: handle_portfolio_risk_requested,
}
