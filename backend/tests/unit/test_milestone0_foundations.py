import asyncio
import importlib

import httpx
import pytest
from pydantic import ValidationError

from backend.api_gateway.main import app
from backend.shared.contracts import API_VERSION, ApiEnvelope, HealthResponse
from backend.shared.database import Base
from backend.shared.models import (
    AuditEventDTO,
    DataSnapshot,
    Instrument,
    InstrumentDTO,
    ModelVersion,
    Order,
    OrderDTO,
    Portfolio,
    Recommendation,
    RecommendationDTO,
    Trade,
    UserDTO,
)


SERVICE_APP_MODULES = (
    "backend.services.api_orchestrator.main",
    "backend.services.execution_service.main",
    "backend.services.safety_service.main",
    "backend.services.white_label.main",
    "backend.services.backtest_engine.main",
    "backend.services.portfolio_service.main",
    "backend.services.stress_test_service.main",
    "backend.services.signal_orchestrator.main",
    "backend.services.personalization.main",
    "backend.services.marketplace.main",
    "backend.services.agents.macro_agent.main",
    "backend.services.agents.trader_risk_agent.main",
    "backend.services.agents.futures_agent.main",
    "backend.services.agents.fundamentals_agent.main",
    "backend.services.agents.technical_agent.main",
    "backend.services.agents.crypto_agent.main",
    "backend.services.agents.bull_bear_agent.main",
    "backend.services.agents.options_agent.main",
    "backend.services.agents.news_sentiment_agent.main",
)


def test_domain_tables_are_registered() -> None:
    expected = {
        Instrument.__tablename__,
        Portfolio.__tablename__,
        Recommendation.__tablename__,
        Order.__tablename__,
        Trade.__tablename__,
        ModelVersion.__tablename__,
        DataSnapshot.__tablename__,
        "audit_logs",
    }

    assert expected.issubset(set(Base.metadata.tables))


def test_domain_dtos_validate_foundation_contracts() -> None:
    user = UserDTO(email="Trader@example.com")
    instrument = InstrumentDTO(symbol="msft", asset_type="equity")
    order = OrderDTO(symbol="nvda", side="buy", quantity=3, order_type="LIMIT")
    recommendation = RecommendationDTO(
        symbol="aapl",
        recommendation="BUY",
        confidence=0.81,
        probability_distribution={"up_5pct_20d": 0.62, "tail_loss_8pct_20d": 0.08},
        factor_exposures={"quality": 0.4, "momentum": 0.2},
        tail_risk_summary={"cvar": -0.07},
    )

    assert user.email == "trader@example.com"
    assert instrument.symbol == "MSFT"
    assert order.side == "BUY"
    assert recommendation.signal == "BUY"
    assert recommendation.audit_metadata.reproducible is True

    with pytest.raises(ValidationError):
        RecommendationDTO(
            symbol="AAPL",
            recommendation="BUY",
            confidence=1.2,
            probability_distribution={"win": 1.4},
        )

    with pytest.raises(ValidationError):
        AuditEventDTO(action="order.submit", previous_hash="same-hash-value", current_hash="same-hash-value")


def test_versioned_contracts() -> None:
    envelope = ApiEnvelope(data={"ok": True})
    health = HealthResponse(service="api_gateway")

    assert envelope.api_version == API_VERSION
    assert health.status == "healthy"


def test_gateway_ready_metrics_and_request_id() -> None:
    async def request() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            ready = await client.get("/ready", headers={"x-request-id": "test-request"})
            metrics = await client.get("/metrics")
            return ready, metrics

    ready_response, metrics_response = asyncio.run(request())

    assert ready_response.status_code == 200
    assert ready_response.headers["x-request-id"] == "test-request"
    assert ready_response.json()["ready"] is True
    assert metrics_response.status_code == 200
    assert "counters" in metrics_response.json()


def test_fastapi_services_expose_foundation_probes() -> None:
    async def request_probes(service_app, request_id: str) -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=service_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            health = await client.get("/health", headers={"x-request-id": request_id})
            ready = await client.get("/ready", headers={"x-request-id": request_id})
            metrics = await client.get("/metrics", headers={"x-request-id": request_id})
            return health, ready, metrics

    for module_name in SERVICE_APP_MODULES:
        service_app = importlib.import_module(module_name).app
        health_response, ready_response, metrics_response = asyncio.run(request_probes(service_app, module_name))

        assert health_response.status_code == 200, module_name
        assert ready_response.status_code == 200, module_name
        assert ready_response.headers["x-request-id"] == module_name
        assert ready_response.json()["ready"] is True
        assert metrics_response.status_code == 200, module_name
        assert "counters" in metrics_response.json()
