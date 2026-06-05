from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.shared.cache import cache_get_or_set, cache_stats
from backend.shared.event_bus import event_bus
from backend.shared.reliability import disaster_recovery_plan, estimate_load_test, slo_dashboard


def test_event_bus_fanout_is_within_latency_budget() -> None:
    result = event_bus.publish("market_data", "tick.received", {"symbol": "MSFT", "price": 100})

    assert result["published"] is True
    assert result["within_budget"] is True
    assert result["latency_ms"] <= 500
    assert result["fanout"]["stream_depth"] >= 1
    assert result["delivery_guarantee"] == "at_least_once_stream_and_best_effort_pubsub"
    assert event_bus.recent("market_data")


def test_cache_get_or_set_hits_on_second_dashboard_lookup() -> None:
    first = cache_get_or_set("dashboard:demo", 60, lambda: {"equity": 100000})
    second = cache_get_or_set("dashboard:demo", 60, lambda: {"equity": 0})

    assert first.hit is False
    assert second.hit is True
    assert second.value["equity"] == 100000
    assert second.namespace == "dashboard"
    assert cache_stats()["hits"] >= 1


def test_event_bus_health_reports_stream_depth_and_queue_budget() -> None:
    event_bus.publish("signals", "signal.generated", {"symbol": "MSFT"})
    health = event_bus.health(["signals"])

    assert health["stream_depths"]["signals"] >= 1
    assert health["within_queue_budget"] is True
    assert health["latency_budget_ms"] == 500


def test_slo_dr_and_load_estimates_are_ready_for_operations() -> None:
    slo = slo_dashboard()
    dr = disaster_recovery_plan("production")
    load = estimate_load_test(10000, 5000)

    assert any(item["name"] == "market_hours_uptime" and item["target"] == 0.999 for item in slo["slos"])
    assert slo["dashboards"]
    assert "event_bus" in slo
    assert dr["restore_test"]["status"] == "passed"
    assert dr["restore_test"]["evidence_id"].startswith("restore:production:")
    assert dr["backup_policy"]["audit_store"]["retention_days"] >= 2555
    assert dr["secondary_region"]
    assert load["passes_500ms_slo"] is True
    assert load["concurrent_users"] == 10000
    assert load["scaling_recommendation"]["recommended_market_open_replicas"] >= 8
    assert "redis_stream_lag" in load["scaling_recommendation"]["autoscale_on"]


def test_infrastructure_manifests_define_scaling_and_reliability_controls() -> None:
    hpa = Path("infrastructure/k8s/hpa-config.yaml").read_text()
    observability = Path("infrastructure/k8s/observability-config.yaml").read_text()
    terraform = Path("infrastructure/terraform/main.tf").read_text() + Path("infrastructure/terraform/environments.tf").read_text()
    dr_doc = Path("docs/disaster_recovery.md").read_text()

    assert "signal-orchestrator-hpa" in hpa
    assert "queue_depth" in hpa
    assert "ServiceMonitor" in observability
    assert "PrometheusRule" in observability
    assert "redis-event-bus" in observability
    assert "dr_region" in terraform
    assert "backup_retention_days" in terraform
    assert "redis_stream_lag_target" in terraform
    assert "Recovery point objective" in dr_doc
    assert "drill_id" in dr_doc


@pytest.mark.asyncio
async def test_reliability_gateway_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        published = await client.post(
            "/reliability/events/publish",
            json={"topic": "signals", "event_type": "signal.generated", "payload": {"symbol": "MSFT"}},
        )
        cached_first = await client.get("/reliability/cache/instrument/MSFT")
        cached_second = await client.get("/reliability/cache/instrument/MSFT")
        cache_health = await client.get("/reliability/cache/stats")
        event_health = await client.get("/reliability/events/health")
        slo = await client.get("/reliability/slo")
        dr = await client.get("/reliability/dr", params={"environment": "production"})
        load = await client.post(
            "/reliability/load-test/estimate",
            json={
                "concurrent_users": 10000,
                "instruments": 5000,
                "replicas": 8,
                "duration_minutes": 240,
                "environment": "staging",
                "distributed_evidence": True,
            },
        )

    assert published.status_code == 200
    assert published.json()["within_budget"] is True
    assert cached_first.status_code == 200
    assert cached_second.json()["hit"] is True
    assert cache_health.json()["requests"] >= 2
    assert event_health.json()["within_queue_budget"] is True
    assert slo.json()["slos"]
    assert dr.json()["restore_test"]["status"] == "passed"
    assert load.json()["passes_500ms_slo"] is True
    assert load.json()["production_ready"] is True
