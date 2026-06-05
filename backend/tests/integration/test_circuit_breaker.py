from backend.services.safety_service.black_swan_detector import BlackSwanDetector
from backend.services.safety_service.circuit_breaker import CircuitBreaker


def test_black_swan_detector_flags_multiple_stress_inputs() -> None:
    signal = BlackSwanDetector().evaluate(
        volatility_zscore=4.0,
        correlation_spike=0.9,
        liquidity_drop=0.2,
    )

    assert signal.triggered is True
    assert signal.severity == "critical"


def test_manual_circuit_breaker_blocks_trading() -> None:
    breaker = CircuitBreaker()
    breaker.trigger_halt("manual test", admin_id="admin")

    assert breaker.is_trading_allowed() is False

    breaker.resume_trading(admin_id="admin")
    assert breaker.is_trading_allowed() is True

