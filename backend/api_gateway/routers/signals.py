from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.signal_orchestrator.orchestrator import generate_signal
from backend.shared.cache import cache_get_or_set, cache_set, scanner_cache_key
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import SignalRequest

router = APIRouter()


class ScannerRequest(BaseModel):
    universe: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    min_confidence: float = 0.0
    sector: str | None = None
    factor: str | None = None
    custom_criteria: dict[str, float | str | bool] = Field(default_factory=dict)


SECTOR_MAP = {
    "AAPL": "technology",
    "MSFT": "technology",
    "NVDA": "technology",
    "AMD": "technology",
    "GOOGL": "communication_services",
    "JPM": "financials",
    "XOM": "energy",
}


@router.get("/{symbol}")
async def get_signal(symbol: str) -> dict:
    signal = await generate_signal(symbol.upper())
    if "error" in signal:
        raise HTTPException(status_code=404, detail=signal["error"])
    return signal


@router.post("/evaluate")
async def evaluate_signal(request: SignalRequest) -> dict:
    signal = await generate_signal(request.symbol.upper(), request.portfolio_context)
    event_bus.publish(
        TOPICS.signal_events,
        EVENT_TYPES.signal_generated,
        {"symbol": signal["symbol"], "signal": signal["signal"]},
        source="api_gateway",
    )
    return signal


@router.post("/commands/evaluate", status_code=202)
async def enqueue_signal_evaluation(request: SignalRequest) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.signal_commands,
        EVENT_TYPES.signal_evaluate_requested,
        request.model_dump(),
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.signal_evaluate_requested,
        "result_topic": TOPICS.signal_events,
        **result,
    }


@router.post("/scanner")
async def discovery_scanner(request: ScannerRequest) -> dict[str, object]:
    cache_key = scanner_cache_key(
        request.universe,
        request.min_confidence,
        request.factor,
        request.sector,
        request.custom_criteria,
    )
    cached = cache_get_or_set(
        cache_key,
        60,
        lambda: None,
    )
    if cached.hit and isinstance(cached.value, dict):
        return {**cached.value, "cache": {"hit": True, "latency_ms": cached.latency_ms}}

    ranked = []
    requested_sector = request.sector.lower() if request.sector else None
    min_reward_to_risk = float(request.custom_criteria.get("min_reward_to_risk", 0) or 0)
    max_tail_risk = float(request.custom_criteria.get("max_tail_risk", 1) or 1)
    min_expected_return = float(request.custom_criteria.get("min_expected_return", -1) or -1)
    for symbol in request.universe:
        normalized_symbol = symbol.upper()
        sector = SECTOR_MAP.get(normalized_symbol, "technology")
        if requested_sector and sector != requested_sector:
            continue
        signal = await generate_signal(normalized_symbol)
        confidence = float(signal["confidence"])
        exposures = signal.get("factor_exposures") or signal["agent_outputs"]["factor_tagging"]["factor_exposures"]
        if confidence < request.min_confidence:
            continue
        if request.factor and exposures.get(request.factor, 0.0) <= 0:
            continue
        probability = signal["probability_distribution"]
        reward_to_risk = round(
            probability["up_5pct_20d"] / max(probability["down_3pct_20d"], 0.01),
            4,
        )
        expected_return = float(signal.get("return_distribution", {}).get("expected_return_20d", probability["up_5pct_20d"]))
        tail_risk = float(probability.get("tail_loss_8pct_20d", 1.0))
        if reward_to_risk < min_reward_to_risk:
            continue
        if tail_risk > max_tail_risk:
            continue
        if expected_return < min_expected_return:
            continue
        ranked.append(
            {
                "symbol": signal["symbol"],
                "signal": signal["signal"],
                "confidence": confidence,
                "expected_return_rank": expected_return,
                "reward_to_risk": reward_to_risk,
                "sector": sector,
                "factor_exposures": exposures,
                "tail_risk": tail_risk,
                "freshness_score": signal.get("freshness_score", 0.0),
                "rationale": signal.get("rationale", [])[:2],
            }
        )
    ranked.sort(key=lambda item: (item["expected_return_rank"], item["reward_to_risk"]), reverse=True)
    result = {
        "results": ranked,
        "count": len(ranked),
        "filters": request.model_dump(),
        "ranked_by": ["expected_return_rank", "reward_to_risk"],
    }
    cache_set(cache_key, result, 60)
    return {**result, "cache": {"hit": False, "latency_ms": cached.latency_ms}}
