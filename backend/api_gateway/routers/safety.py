from fastapi import APIRouter

from backend.services.safety_service.circuit_breaker import CircuitBreaker

router = APIRouter()
breaker = CircuitBreaker()


@router.get("/status")
async def status() -> dict[str, object]:
    return {
        "trading_allowed": breaker.is_trading_allowed(),
        "reason": breaker.manual_reason,
        "halted_at": breaker.halted_at,
        "halted_by": breaker.halted_by,
        "new_orders_blocked": not breaker.is_trading_allowed(),
        "cancel_pending_orders": not breaker.is_trading_allowed(),
    }


@router.post("/halt")
async def halt(reason: str, admin_id: str = "system") -> dict[str, object]:
    return breaker.trigger_halt(reason, admin_id)


@router.post("/resume")
async def resume(admin_id: str = "system") -> dict[str, object]:
    return breaker.resume_trading(admin_id)


@router.post("/monitor")
async def monitor(payload: dict) -> dict[str, object]:
    signal = breaker.monitor_auto(
        volatility_zscore=float(payload.get("volatility_zscore", 0.0)),
        correlation_spike=float(payload.get("correlation_spike", 0.0)),
        liquidity_drop=float(payload.get("liquidity_drop", 0.0)),
    )
    return {
        "triggered": signal.triggered,
        "severity": signal.severity,
        "reasons": signal.reasons,
        "trading_allowed": breaker.is_trading_allowed(),
        "reason": breaker.manual_reason,
        "halted_at": breaker.halted_at,
        "new_orders_blocked": not breaker.is_trading_allowed(),
        "cancel_pending_orders": signal.triggered and signal.severity == "critical",
        "manual_review_required": signal.triggered,
    }


@router.post("/guard-order")
async def guard_order(payload: dict) -> dict[str, object]:
    return breaker.guard_order(payload)
