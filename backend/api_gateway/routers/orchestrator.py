from fastapi import APIRouter

from backend.data_pipeline.ingestion.orchestrator import data_orchestrator
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.external_api.chaos import run_experiment
from backend.shared.external_api.router import external_api_router

router = APIRouter()


@router.get("/quote/{symbol}")
async def quote(symbol: str, asset_class: str = "equity") -> dict[str, object]:
    return await data_orchestrator.get_quote(symbol, asset_class)


@router.get("/news/{symbol}")
async def news(symbol: str) -> dict[str, object]:
    return await data_orchestrator.get_news(symbol)


@router.post("/commands/quote", status_code=202)
async def enqueue_quote(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.external_api_commands,
        EVENT_TYPES.quote_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.quote_requested,
        "result_topic": TOPICS.external_api_events,
        **result,
    }


@router.post("/commands/news", status_code=202)
async def enqueue_news(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.external_api_commands,
        EVENT_TYPES.news_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.news_requested,
        "result_topic": TOPICS.external_api_events,
        **result,
    }


@router.get("/status")
async def status() -> dict[str, object]:
    return external_api_router.status()


@router.post("/chaos/{experiment_id}")
async def chaos_experiment(experiment_id: str) -> dict[str, object]:
    result = await run_experiment(experiment_id)
    return {
        "experiment_id": result.experiment_id,
        "passed": result.passed,
        "metrics": result.metrics,
        "alerts": result.alerts,
        "notes": result.notes,
    }
