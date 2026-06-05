import pytest

from backend.services.signal_orchestrator.orchestrator import generate_signal


@pytest.mark.asyncio
async def test_complete_signal_flow_graph_exists() -> None:
    signal = await generate_signal("MSFT")

    expected_nodes = {
        "user",
        "react_frontend",
        "api_gateway",
        "signal_orchestrator",
        "fundamentals_agent",
        "technical_agent",
        "news_sentiment_agent",
        "macro_agent",
        "alt_data_agent",
        "regime_detector",
        "bull_bear_debate",
        "factor_tagging_service",
        "tax_optimizer",
        "trader_risk_agent",
        "execution_service",
        "champion_challenger_manager",
        "mlflow_tracking",
        "model_promotion_pipeline",
        "notification_service",
    }

    assert expected_nodes.issubset(set(signal["flow"]))
    assert signal["agent_outputs"]["technical"]["agent"] == "technical"
    assert signal["agent_outputs"]["factor_tagging"]["agent"] == "factor_tagging"
    assert signal["risk"]["agent"] == "trader_risk"
    assert signal["execution"]["service"] == "execution_service"
    assert signal["champion_challenger"]["mlflow_tracking"]["enabled"] is True
    assert signal["notification"]["status"] == "queued"
