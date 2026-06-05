from datetime import datetime, timedelta, timezone

import pytest

from backend.services.agents.bull_bear_agent.debate_engine import run_debate
from backend.services.agents.fundamentals_agent.analyzer import analyze_fundamentals
from backend.services.agents.macro_agent.economic_indicators import macro_regime
from backend.services.agents.news_sentiment_agent.nlp_model import score_sentiment
from backend.services.agents.technical_agent.analyzer import analyze_technicals
from backend.services.factor_tagging import tag_factor_exposures
from backend.services.explainability import generate_explanation
from backend.services.regime_detector import detect_market_regime
from backend.services.signal_orchestrator.freshness_model import should_auto_cancel_signal
from backend.services.signal_orchestrator.orchestrator import generate_signal


def test_fundamental_agent_returns_evidence_and_red_flags() -> None:
    result = analyze_fundamentals("NVDA")

    assert "beneish_m_score" in result["factors"]
    assert result["evidence"]
    assert all("url" in item for item in result["evidence"])
    assert "red_flags" in result
    assert "red_flag_explanations" in result


def test_technical_agent_returns_multitimeframe_and_patterns() -> None:
    result = analyze_technicals("MSFT")

    assert result["timeframes"]["confluence"] in {"bullish", "bearish", "mixed"}
    assert result["timeframes"]["timeframes"]["daily"]["confidence"] > 0
    assert result["timeframes"]["timeframes"]["daily"]["posture"] in {"trend_following", "range_bound"}
    assert "support" in result["support_resistance"]
    assert "volume_profile" in result


def test_news_macro_debate_and_factor_outputs_are_complete() -> None:
    news = score_sentiment("AAPL")
    macro = macro_regime()
    debate = run_debate("AAPL")
    factors = tag_factor_exposures("NVDA", {"factor_load": {"growth": 0.4}})

    assert {"news", "social", "insider_transactions", "event_risk"}.issubset(news["scores"])
    assert macro["regime"] in {"risk_on", "risk_off", "neutral"}
    assert debate["unresolved_risks"]
    assert "growth" in factors["factor_exposures"]
    assert factors["factor_warnings"]


def test_regime_detection_changes_agent_weights() -> None:
    high_vol = detect_market_regime({"volatility": 0.35, "trend": -0.1, "liquidity": 0.4})
    bull = detect_market_regime({"volatility": 0.12, "trend": 0.08, "liquidity": 0.8})

    assert high_vol["regime"] == "high_volatility"
    assert bull["regime"] == "bull"
    assert high_vol["agent_weights"] != bull["agent_weights"]


@pytest.mark.asyncio
async def test_final_signal_is_probabilistic_actionable_and_explainable() -> None:
    signal = await generate_signal(
        "MSFT",
        {
            "factor_load": {"quality": 0.4},
            "equity": 125000,
            "risk_profile": "balanced",
            "max_drawdown_tolerance": 0.1,
        },
    )

    assert signal["signal"] in {"BUY", "SELL", "HOLD"}
    assert "tail_loss_8pct_20d" in signal["probability_distribution"]
    directional_sum = (
        signal["probability_distribution"]["up_5pct_20d"]
        + signal["probability_distribution"]["down_3pct_20d"]
        + signal["probability_distribution"]["flat_20d"]
    )
    assert abs(directional_sum - 1.0) <= 0.001
    assert signal["return_distribution"]["horizon_days"] == 20
    assert signal["tail_risk_summary"]["cvar_20d"] < 0
    assert signal["factor_exposures"]["quality"] > 0
    assert signal["entry_zone"]["low"] < signal["entry_zone"]["high"]
    assert signal["stop_loss"] < signal["take_profit"]
    assert signal["position_size"] >= 0
    assert signal["position_sizing"]["method"] == "min_of_kelly_volatility_risk_parity"
    assert signal["explainability"]["top_drivers"]
    assert signal["explainability"]["feature_attributions"]
    assert signal["explainability"]["plain_language_risks"]
    assert signal["signal_freshness"]["stale_order_action"] in {"keep_active", "cancel_pending_orders"}


@pytest.mark.asyncio
async def test_explainability_layer_uses_local_surrogate_attributions() -> None:
    explanation = await generate_explanation("AAPL")

    assert explanation["feature_contributions"]
    assert explanation["top_drivers"]
    assert explanation["plain_language_risks"]


def test_signal_freshness_auto_cancels_stale_signal() -> None:
    old_time = datetime.now(timezone.utc) - timedelta(hours=12)

    assert should_auto_cancel_signal(old_time) is True
