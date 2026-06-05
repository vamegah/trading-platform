import time

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.shared.event_bus import event_bus
from backend.shared.reliability import estimate_load_test


@pytest.mark.asyncio
async def test_signal_delivery_endpoint_stays_under_latency_budget_for_fixture() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        started = time.perf_counter()
        response = await client.post("/signals/evaluate", json={"symbol": "MSFT"})
        elapsed_ms = (time.perf_counter() - started) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 500


def test_load_estimate_for_target_scale_passes_slo_and_documents_bottlenecks() -> None:
    estimate = estimate_load_test(concurrent_users=10_000, instruments=5_000)

    assert estimate["passes_500ms_slo"] is True
    assert estimate["estimated_p95_ms"] <= 500
    assert estimate["bottlenecks"]
    assert estimate["scaling_recommendation"]["recommended_market_open_replicas"] >= 8
    assert "redis_stream_lag" in estimate["scaling_recommendation"]["autoscale_on"]


def test_event_fanout_health_stays_inside_queue_and_latency_budget() -> None:
    result = event_bus.publish("events.signal", "signal.generated", {"symbol": "MSFT"})
    health = event_bus.health(["events.signal"])

    assert result["within_budget"] is True
    assert result["fanout"]["stream_depth"] >= 1
    assert health["within_queue_budget"] is True
    assert health["latency_budget_ms"] == 500


def test_load_estimate_requires_distributed_soak_before_production_ready() -> None:
    preflight = estimate_load_test(concurrent_users=10_000, instruments=5_000)
    production_like = estimate_load_test(
        concurrent_users=10_000,
        instruments=5_000,
        duration_minutes=240,
        environment="staging",
        distributed_evidence=True,
    )

    assert preflight["passes_500ms_slo"] is True
    assert preflight["production_ready"] is False
    assert production_like["production_ready"] is True
