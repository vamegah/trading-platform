import pytest

from backend.data_pipeline.ingestion.orchestrator import DataOrchestrator
from backend.data_pipeline.ingestion.providers import AlphaVantageProvider, PolygonProvider
from backend.shared.external_api.circuit_breaker import CircuitBreaker, CircuitOpenError
from backend.shared.external_api.router import ExternalAPIRouter


@pytest.mark.asyncio
async def test_data_orchestrator_quote_failover_and_cache() -> None:
    config = {
        "equity_market_data": {
            "asset_class": "equity",
            "primary": "polygon",
            "failover": ["alpha_vantage"],
            "ttl_seconds": 5,
            "stale_ttl_seconds": 60,
            "providers": {
                "polygon": {"timeout_ms": 100, "requests_per_minute": 60},
                "alpha_vantage": {"timeout_ms": 100, "requests_per_minute": 60},
            },
        }
    }
    orchestrator = DataOrchestrator(
        config=config,
        providers={
            "polygon": PolygonProvider(fail=True),
            "alpha_vantage": AlphaVantageProvider(),
        },
    )

    first = await orchestrator.get_quote("ORCHT")
    second = await orchestrator.get_quote("ORCHT")

    assert first["symbol"] == "ORCHT"
    assert first["source"] == "alpha_vantage"
    assert first["cache"]["hit"] is False
    assert second["cache"]["hit"] is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_repeated_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)
    router = ExternalAPIRouter(circuit_breaker=breaker)

    async def failing():
        raise TimeoutError("provider timeout")

    for _ in range(2):
        with pytest.raises(TimeoutError):
            await router.call("polygon", "quote", failing, timeout_ms=100)

    with pytest.raises(CircuitOpenError):
        await router.call("polygon", "quote", failing, timeout_ms=100)


@pytest.mark.asyncio
async def test_rate_governor_rejects_non_realtime_over_budget() -> None:
    router = ExternalAPIRouter()

    async def ok():
        return {"ok": True}

    await router.call("openai", "chat", ok, rate_limit_per_minute=1)
    with pytest.raises(Exception):
        await router.call("openai", "chat", ok, rate_limit_per_minute=1)
