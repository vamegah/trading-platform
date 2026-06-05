from fastapi import APIRouter

from backend.shared.cache import cache_get_or_set, cache_stats, instrument_cache_key
from backend.shared.event_bus import event_bus
from backend.shared.events import CORE_EVENT_TOPOLOGY, TOPICS
from backend.shared.reliability import disaster_recovery_plan, estimate_load_test, slo_dashboard

router = APIRouter()


@router.post("/events/publish")
async def publish_event(payload: dict) -> dict[str, object]:
    return event_bus.publish(
        payload.get("topic", "market_data"),
        payload.get("event_type", "tick.received"),
        payload.get("payload", {}),
    )


@router.get("/events")
async def event_topics() -> dict[str, object]:
    topics = TOPICS.__dict__.copy()
    return {
        "topics": topics,
        "streams": {name: event_bus.stream_name(topic) for name, topic in topics.items()},
        "topology": CORE_EVENT_TOPOLOGY,
        "health": event_bus.health(list(topics.values())),
    }


@router.get("/events/health")
async def event_health() -> dict[str, object]:
    return event_bus.health(list(TOPICS.__dict__.values()))


@router.get("/events/correlations/{correlation_id}")
async def events_by_correlation(correlation_id: str, limit: int = 100) -> dict[str, object]:
    topics = list(TOPICS.__dict__.values())
    return {
        "correlation_id": correlation_id,
        "events": event_bus.by_correlation(correlation_id, topics, limit),
    }


@router.get("/events/{topic}")
async def recent_events(topic: str) -> dict[str, object]:
    return {"topic": topic, "events": event_bus.recent(topic)}


@router.post("/events/{topic}/groups/{group}")
async def ensure_event_group(topic: str, group: str) -> dict[str, object]:
    return event_bus.ensure_consumer_group(topic, group)


@router.get("/cache/instrument/{symbol}")
async def cached_instrument(symbol: str) -> dict[str, object]:
    result = cache_get_or_set(
        instrument_cache_key(symbol),
        300,
        lambda: {"symbol": symbol.upper(), "asset_type": "equity", "exchange": "NASDAQ"},
    )
    return result.__dict__


@router.get("/cache/stats")
async def cache_health() -> dict[str, object]:
    return cache_stats()


@router.get("/slo")
async def slo() -> dict[str, object]:
    return slo_dashboard()


@router.get("/dr")
async def dr(environment: str = "production") -> dict[str, object]:
    return disaster_recovery_plan(environment)


@router.post("/load-test/estimate")
async def load_test(payload: dict) -> dict[str, object]:
    return estimate_load_test(
        concurrent_users=int(payload.get("concurrent_users", 10000)),
        instruments=int(payload.get("instruments", 5000)),
        replicas=int(payload.get("replicas", 8)),
        duration_minutes=int(payload.get("duration_minutes", 0)),
        environment=str(payload.get("environment", "local-preflight")),
        distributed_evidence=bool(payload.get("distributed_evidence", False)),
    )
