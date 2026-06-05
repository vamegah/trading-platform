from fastapi import FastAPI

from backend.services.safety_service.circuit_breaker import CircuitBreaker
from backend.shared.observability import RequestContextMiddleware, add_observability_routes

app = FastAPI(title="Safety Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
add_observability_routes(app, "safety_service", {"circuit_breaker": "in_memory"})
breaker = CircuitBreaker()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "safety_service", "status": "healthy"}


@app.get("/status")
async def status() -> dict[str, bool | str | None]:
    return {"trading_allowed": breaker.is_trading_allowed(), "reason": breaker.manual_reason}


@app.post("/halt")
async def halt(reason: str, admin_id: str = "system") -> dict[str, object]:
    return breaker.trigger_halt(reason, admin_id)


@app.post("/resume")
async def resume(admin_id: str = "system") -> dict[str, object]:
    return breaker.resume_trading(admin_id)


@app.post("/evaluate")
async def evaluate(payload: dict) -> dict[str, object]:
    signal = breaker.monitor_auto(
        volatility_zscore=float(payload.get("volatility_zscore", 0.0)),
        correlation_spike=float(payload.get("correlation_spike", 0.0)),
        liquidity_drop=float(payload.get("liquidity_drop", 0.0)),
    )
    return signal.__dict__
