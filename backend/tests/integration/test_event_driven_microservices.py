from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.backtest_engine.worker import run_once as run_backtest_worker
from backend.services.personalization.worker import run_once as run_personalization_worker
from backend.shared.event_bus import event_bus
from backend.shared.events import CORE_EVENT_TOPOLOGY, EVENT_TYPES, TOPICS
from backend.shared.service_registry import EVENT_DRIVEN_SERVICE_GRAPH


def test_event_topology_covers_core_microservices() -> None:
    assert "api_gateway" in CORE_EVENT_TOPOLOGY
    for service in (
        "external_api_orchestrator",
        "signal_orchestrator",
        "execution_service",
        "portfolio_service",
        "backtest_engine",
        "marketplace_service",
        "personalization_engine",
    ):
        assert CORE_EVENT_TOPOLOGY[service]["subscribes"]
        assert CORE_EVENT_TOPOLOGY[service]["publishes"]

    assert "redis_streams_event_bus" in EVENT_DRIVEN_SERVICE_GRAPH
    assert "signal_worker" in EVENT_DRIVEN_SERVICE_GRAPH["redis_streams_event_bus"]


@pytest.mark.asyncio
async def test_gateway_accepts_async_microservice_commands() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        signal = await client.post("/signals/commands/evaluate", json={"symbol": "MSFT"})
        quote = await client.post("/orchestrator/commands/quote", json={"symbol": "MSFT"})
        execution = await client.post(
            "/execution/commands/smart-route",
            json={"symbol": "MSFT", "quantity": 1, "suitability_completed": True},
        )
        risk = await client.post(
            "/portfolio/commands/risk/live",
            json={"portfolio": [{"symbol": "MSFT", "market_value": 1000, "beta": 1.1}]},
        )
        backtest = await client.post("/backtest/commands/walk-forward", json={"symbol": "MSFT", "days": 30})
        marketplace = await client.post(
            "/marketplace/commands/agents/publish",
            json={
                "id": "agent-test",
                "name": "Test Agent",
                "publisher_id": "publisher-test",
                "asset_types": ["equity"],
                "description": "Test event-driven marketplace publish",
            },
        )
        personalization = await client.post(
            "/personalization/commands/persona",
            json={"user_id": "demo"},
        )

    for response in (signal, quote, execution, risk, backtest, marketplace, personalization):
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["correlation_id"]
        assert body["stream"].startswith("stream:commands.")


@pytest.mark.asyncio
async def test_workers_publish_correlated_result_events() -> None:
    persona_command = event_bus.publish(
        TOPICS.personalization_commands,
        EVENT_TYPES.personalization_persona_requested,
        {"user_id": "worker-demo"},
        source="test",
    )
    await run_personalization_worker("test-personalization-worker")
    persona_events = event_bus.by_correlation(
        str(persona_command["correlation_id"]),
        [TOPICS.personalization_events],
    )

    backtest_command = event_bus.publish(
        TOPICS.backtest_commands,
        EVENT_TYPES.backtest_walk_forward_requested,
        {"symbol": "MSFT", "days": 30},
        source="test",
    )
    await run_backtest_worker("test-backtest-worker")
    backtest_events = event_bus.by_correlation(
        str(backtest_command["correlation_id"]),
        [TOPICS.backtest_events],
    )

    assert any(event["event_type"] == EVENT_TYPES.personalization_persona_built for event in persona_events)
    assert any(event["event_type"] == EVENT_TYPES.backtest_completed for event in backtest_events)


def test_deployment_manifests_include_event_workers_and_edge_ingress() -> None:
    compose = Path("docker-compose.yml").read_text()
    workers = Path("infrastructure/k8s/event-workers-deployment.yaml").read_text()
    ingress = Path("infrastructure/k8s/ingress-edge.yaml").read_text()
    terraform = Path("infrastructure/terraform/edge_ingress.tf").read_text()
    docs = Path("docs/event_driven_architecture.md").read_text()

    for service in ("signal-worker", "execution-worker", "backtest-worker", "marketplace-worker"):
        assert service in compose
        assert service in workers

    assert "CloudFront" in ingress
    assert "aws_wafv2_web_acl" in terraform
    assert "Redis Streams" in docs
