import pytest

from backend.api_gateway.main import app
from backend.services.signal_orchestrator.orchestrator import generate_signal
from backend.ml_training.train_pipeline import train


@pytest.mark.asyncio
async def test_platform_graph_edges_exist() -> None:
    routes = {route.path for route in app.routes}
    assert "/api/auth/login" in routes
    assert "/portfolio/summary" in routes
    assert "/execution/orders" in routes
    assert "/signals/evaluate" in routes
    assert "/backtest/{symbol}" in routes

    signal = await generate_signal("MSFT")
    flow = set(signal["flow"])
    assert "data_lake_postgresql" in flow
    assert "redis_cache" in flow
    assert "external_broker_apis" in flow
    assert "backtesting_engine" in flow
    assert "ml_pipeline_model_training" in flow
    assert "monitoring_logging" in flow

    for service in (
        "fundamentals_agent",
        "technical_agent",
        "news_sentiment_agent",
        "macro_agent",
        "bull_bear_debate_agent",
        "trader_risk_agent",
    ):
        assert signal["database_edges"][service]["store"] == "data_lake_postgresql"

    assert signal["cache"]["read"]["store"] == "redis_cache"
    assert signal["cache"]["write"]["store"] == "redis_cache"
    assert "alpaca" in signal["execution"]["external_broker_apis"]

    training = train([{"feature": 1.0, "target": 1.0}])
    assert training["database_edge"]["service"] == "ml_pipeline_model_training"
