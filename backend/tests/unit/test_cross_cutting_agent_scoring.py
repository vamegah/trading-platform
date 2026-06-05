from datetime import date, timedelta

from backend.services.agents.alt_data_agent.alt_analyzer import analyze_alt_data
from backend.services.agents.bull_bear_agent.debate_engine import run_debate
from backend.services.agents.crypto_agent.on_chain import analyze_on_chain
from backend.services.agents.fundamentals_agent.analyzer import analyze_fundamentals
from backend.services.agents.futures_agent.carry_model import calculate_carry
from backend.services.agents.macro_agent.economic_indicators import macro_regime
from backend.services.agents.news_sentiment_agent.nlp_model import score_sentiment
from backend.services.agents.options_agent.greeks_engine import calculate_greeks
from backend.services.agents.technical_agent.analyzer import analyze_technicals
from backend.services.agents.trader_risk_agent.risk_manager import assess_risk


def _assert_score_between_zero_and_one(value: float) -> None:
    assert 0 <= value <= 1


def test_each_agent_handles_normal_symbol_inputs() -> None:
    outputs = [
        analyze_fundamentals("msft"),
        analyze_technicals("msft"),
        score_sentiment("msft"),
        macro_regime(),
        analyze_alt_data("msft"),
        run_debate("msft"),
        assess_risk("msft"),
    ]

    assert all(output for output in outputs)
    assert outputs[0]["symbol"] == "MSFT"
    assert outputs[1]["symbol"] == "MSFT"
    assert outputs[2]["symbol"] == "MSFT"
    assert outputs[6]["entry_zone_low"] < outputs[6]["entry_zone_high"]
    _assert_score_between_zero_and_one(outputs[0]["score"])
    _assert_score_between_zero_and_one(outputs[1]["confidence"])
    _assert_score_between_zero_and_one(outputs[2]["score"])
    _assert_score_between_zero_and_one(outputs[6]["risk_score"])


def test_agents_return_deterministic_scores_for_fixture_symbol() -> None:
    first = analyze_fundamentals("AAPL")
    second = analyze_fundamentals("AAPL")
    technical = analyze_technicals("AAPL")
    sentiment = score_sentiment("AAPL")

    assert first["score"] == second["score"]
    assert 0 <= technical["confidence"] <= 1
    assert 0 <= sentiment["score"] <= 1
    assert first["evidence"] == second["evidence"]


def test_bad_or_sparse_inputs_fail_soft_with_structured_outputs() -> None:
    fundamentals = analyze_fundamentals("")
    technicals = analyze_technicals("")
    event_risk = assess_risk(
        "XYZ",
        [{"type": "earnings", "date": (date.today() + timedelta(days=2)).isoformat()}],
    )

    assert fundamentals["symbol"] == ""
    assert "factors" in fundamentals
    assert technicals["timeframes"]["confluence"] in {"bullish", "bearish", "mixed"}
    assert technicals["support_resistance"]["support"] < technicals["support_resistance"]["resistance"]
    assert event_risk["event_risk_protocol"]["block_new_automation"] is True
    assert event_risk["event_risk_protocol"]["blocked_reason"] == "upcoming_high_impact_event"


def test_extended_asset_agents_return_scored_outputs() -> None:
    greeks = calculate_greeks("btc-30jun-c")
    carry = calculate_carry("cl")
    crypto = analyze_on_chain("btc")

    assert greeks["delta"] != 0
    assert carry["recommendation"]
    assert crypto["network_value_signal"] > 0


def test_agent_scoring_outputs_are_serializable_and_include_agent_names() -> None:
    outputs = [
        analyze_fundamentals("MSFT"),
        analyze_technicals("MSFT"),
        score_sentiment("MSFT"),
        analyze_alt_data("MSFT"),
        run_debate("MSFT"),
        assess_risk("MSFT"),
    ]

    assert all("agent" in output for output in outputs)
    assert {output["agent"] for output in outputs} >= {
        "fundamentals",
        "technical",
        "news_sentiment",
        "alt_data",
        "bull_bear_debate",
        "trader_risk",
    }
