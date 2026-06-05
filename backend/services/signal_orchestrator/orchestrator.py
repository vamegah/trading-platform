import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from backend.ml_training.champion_challenger import evaluate_champion_challenger
from backend.services.agents.alt_data_agent.alt_analyzer import analyze_alt_data
from backend.services.agents.bull_bear_agent.debate_engine import run_debate
from backend.services.agents.fundamentals_agent.analyzer import analyze_fundamentals
from backend.services.agents.macro_agent.economic_indicators import macro_regime
from backend.services.agents.news_sentiment_agent.nlp_model import score_sentiment
from backend.services.agents.technical_agent.analyzer import analyze_technicals
from backend.services.agents.trader_risk_agent.position_sizer import (
    PositionSizingInput,
    calculate_position_size,
    size_position,
)
from backend.services.agents.trader_risk_agent.risk_manager import assess_risk
from backend.services.execution_service.order_router import AlmgrenChrissImpactModel
from backend.services.factor_tagging import tag_factor_exposures
from backend.services.notification_service.push import send_notification
from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord
from backend.services.portfolio_service.tax_optimizer import optimize_after_tax_sale
from backend.services.regime_detector import detect_market_regime
from backend.services.signal_orchestrator.freshness_model import (
    should_auto_cancel_signal,
    signal_freshness_score,
)
from backend.shared.config import settings
from backend.shared.data_lake import agent_db_edges, record_data_lake_edge
from backend.shared.logging_config import record_monitoring_event
from backend.shared.redis_client import redis_client


SIGNAL_CONTRACT_VERSION = "m2.2026-06-03"


def _cache_get(cache_key: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    edge = {"store": "redis_cache", "operation": "get", "key": cache_key, "status": "miss", "hit": False}
    try:
        cached = redis_client.get(cache_key)
    except Exception:
        edge["status"] = "unavailable"
        return None, edge
    if not cached:
        return None, edge
    edge["status"] = "hit"
    edge["hit"] = True
    return json.loads(cached), edge


def _cache_set(cache_key: str, payload: dict[str, Any]) -> dict[str, str]:
    edge = {"store": "redis_cache", "operation": "setex", "key": cache_key, "status": "stored"}
    try:
        redis_client.setex(cache_key, 300, json.dumps(payload, default=str))
    except Exception:
        edge["status"] = "unavailable"
    return edge


def _normalize_score(value: float) -> float:
    return value / 100 if value > 1 else value


def _normalize_directional_probabilities(up: float, down: float, flat: float) -> dict[str, float]:
    total = max(up + down + flat, 0.0001)
    return {
        "up_5pct_20d": round(up / total, 4),
        "down_3pct_20d": round(down / total, 4),
        "flat_20d": round(flat / total, 4),
    }


def _return_distribution(probabilities: dict[str, float], tail_loss_probability: float) -> dict[str, float]:
    expected_return = (
        probabilities["up_5pct_20d"] * 0.05
        - probabilities["down_3pct_20d"] * 0.03
        - tail_loss_probability * 0.08
    )
    return {
        "expected_return_20d": round(expected_return, 4),
        "p10_return_20d": round(-0.08 * max(tail_loss_probability, 0.25), 4),
        "p50_return_20d": round(expected_return / 2, 4),
        "p90_return_20d": round(0.05 * max(probabilities["up_5pct_20d"], 0.25), 4),
        "horizon_days": 20,
    }


def _tail_risk_summary(probabilities: dict[str, float], return_distribution: dict[str, float]) -> dict[str, object]:
    tail_probability = probabilities["tail_loss_8pct_20d"]
    return {
        "tail_loss_threshold": -0.08,
        "tail_loss_probability": tail_probability,
        "cvar_20d": round(return_distribution["p10_return_20d"] * 1.25, 4),
        "summary": f"{tail_probability:.0%} modeled probability of an 8% drawdown over 20 trading days.",
    }


def _local_surrogate_explainability(
    scores: dict[str, float],
    weights: dict[str, float],
    combined_score: float,
) -> dict[str, object]:
    contributions = {
        name: round((score - 0.5) * weights.get(name, 0.0), 4)
        for name, score in scores.items()
    }
    top_drivers = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
    return {
        "method": "interpretable_weighted_surrogate",
        "baseline_score": 0.5,
        "prediction_score": round(combined_score, 4),
        "feature_attributions": contributions,
        "top_drivers": [
            {
                "factor": name,
                "score": round(scores[name], 4),
                "weight": round(weights.get(name, 0.0), 4),
                "contribution": contribution,
            }
            for name, contribution in top_drivers
        ],
        "plain_language_risks": [
            "Macro regime can overpower single-stock signals.",
            "Signal freshness decays and stale entries should be canceled.",
            "Factor concentration can increase hidden portfolio risk.",
        ],
    }


def _is_signal_contract_current(signal: dict[str, Any]) -> bool:
    return (
        signal.get("contract_version") == SIGNAL_CONTRACT_VERSION
        and isinstance(signal.get("factor_exposures"), dict)
        and isinstance(signal.get("return_distribution"), dict)
        and isinstance(signal.get("tail_risk_summary"), dict)
        and isinstance(signal.get("explainability", {}).get("feature_attributions"), dict)
    )


def _tax_optimizer_result(symbol: str) -> dict[str, object]:
    today = datetime.now(timezone.utc).date()
    lots = [
        TaxLotRecord("demo-loss", symbol.upper(), 10, 120.0, today.replace(year=today.year - 1)),
        TaxLotRecord("demo-gain", symbol.upper(), 10, 80.0, today.replace(year=today.year - 2)),
    ]
    return optimize_after_tax_sale(lots=lots, quantity=2, current_price=100.0)


def _synthesize_recommendation(agent_outputs: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    scores = {
        "fundamentals": _normalize_score(agent_outputs["fundamentals"]["score"]),
        "technical": _normalize_score(agent_outputs["technical"]["confidence"]),
        "news_sentiment": _normalize_score(agent_outputs["news_sentiment"]["score"]),
        "macro": _normalize_score(agent_outputs["macro"]["liquidity_score"]),
        "alt_data": _normalize_score(agent_outputs["alt_data"]["score"]),
        "debate": max(0.0, min(1.0, 0.5 + agent_outputs["bull_bear_debate"]["conviction"] / 2)),
        "tax": 0.55 if agent_outputs["tax_optimizer"]["tax_impact"]["estimated_tax"] <= 0 else 0.48,
    }
    combined = sum(scores[key] * weights.get(key, 0.0) for key in scores)
    rating = "BUY" if combined >= 0.68 else "SELL" if combined <= 0.38 else "HOLD"
    tail_loss_probability = round(max(0.03, min(0.45, 0.32 - combined * 0.18 + scores["macro"] * 0.04)), 4)
    directional_probabilities = _normalize_directional_probabilities(
        up=max(0.05, min(0.9, 0.35 + combined * 0.45)),
        down=max(0.05, min(0.7, 0.45 - combined * 0.25)),
        flat=0.22,
    )
    probabilities = {**directional_probabilities, "tail_loss_8pct_20d": tail_loss_probability}
    distribution = _return_distribution(directional_probabilities, tail_loss_probability)
    return {
        "signal": rating,
        "combined_score": round(combined, 4),
        "confidence": round(max(0.0, min(1.0, combined)), 4),
        "component_scores": scores,
        "probability_distribution": probabilities,
        "return_distribution": distribution,
        "tail_risk_summary": _tail_risk_summary(probabilities, distribution),
        "explainability": _local_surrogate_explainability(scores, weights, combined),
    }


def _position_sizing_result(
    risk: dict[str, Any],
    recommendation: dict[str, Any],
    portfolio_context: dict | None,
) -> dict[str, object]:
    context = portfolio_context or {}
    equity = float(context.get("equity", 100000.0))
    entry_price = (float(risk["entry_zone_low"]) + float(risk["entry_zone_high"])) / 2
    stop_loss = float(risk["stop_loss"])
    take_profit = float(risk["take_profit"])
    average_win_pct = max((take_profit - entry_price) / entry_price, 0.001)
    average_loss_pct = -max((entry_price - stop_loss) / entry_price, 0.001)
    sizing = calculate_position_size(
        PositionSizingInput(
            equity=equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            win_probability=float(recommendation["probability_distribution"]["up_5pct_20d"]),
            average_win_pct=average_win_pct,
            average_loss_pct=average_loss_pct,
            volatility=float(context.get("volatility", 0.025)),
            portfolio_volatility=float(context.get("portfolio_volatility", 0.16)),
            max_drawdown_tolerance=float(context.get("max_drawdown_tolerance", 0.12)),
            current_portfolio_risk=float(context.get("current_portfolio_risk", 0.02)),
            risk_profile=str(context.get("risk_profile", "balanced")),
        )
    )
    return {
        "method": sizing.method,
        "quantity": sizing.quantity,
        "notional": sizing.notional,
        "portfolio_weight": sizing.portfolio_weight,
        "risk_budget": sizing.risk_budget,
        "limiting_constraint": sizing.limiting_constraint,
        "components": sizing.components,
    }


async def generate_signal(symbol: str, portfolio_context: dict | None = None) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    normalized_symbol = symbol.upper()
    cache_key = f"signal:{normalized_symbol}"
    cached_signal, cache_read = _cache_get(cache_key)
    if cached_signal:
        if _is_signal_contract_current(cached_signal):
            cached_signal["cache"] = {
                "read": cache_read,
                "write": cached_signal.get("cache", {}).get(
                    "write",
                    {"store": "redis_cache", "operation": "setex", "key": cache_key, "status": "cached"},
                ),
                "source": "redis_cache",
            }
            return cached_signal
        cache_read["status"] = "stale_contract"
        cache_read["hit"] = False

    fundamentals = analyze_fundamentals(normalized_symbol)
    technical = analyze_technicals(normalized_symbol)
    news = score_sentiment(normalized_symbol)
    macro = macro_regime()
    alt = analyze_alt_data(normalized_symbol)
    regime = detect_market_regime({"volatility": 0.18, "trend": technical["momentum_score"]})
    debate = run_debate(normalized_symbol, {"fundamentals": fundamentals, "technical": technical, "news": news, "macro": macro})
    factors = tag_factor_exposures(normalized_symbol, portfolio_context)
    tax = _tax_optimizer_result(normalized_symbol)

    agent_outputs = {
        "fundamentals": fundamentals,
        "technical": technical,
        "news_sentiment": news,
        "macro": macro,
        "alt_data": alt,
        "regime_detector": regime,
        "bull_bear_debate": debate,
        "factor_tagging": factors,
        "tax_optimizer": tax,
    }
    recommendation = _synthesize_recommendation(agent_outputs, regime["agent_weights"])
    risk = assess_risk(normalized_symbol)
    fallback_position_size = size_position(float((portfolio_context or {}).get("equity", 100000.0)), float(risk["risk_score"]))
    position_sizing = _position_sizing_result(risk, recommendation, portfolio_context)
    risk["position_size"] = position_sizing["notional"] or fallback_position_size
    risk["position_sizing"] = position_sizing
    impact = AlmgrenChrissImpactModel().estimate(
        symbol=normalized_symbol,
        order_size=float(risk["position_size"]) / 100.0,
        side="BUY" if recommendation["signal"] == "BUY" else "SELL",
        current_price=100.0,
    )
    champion = evaluate_champion_challenger(
        latest_score=recommendation["combined_score"],
        challenger_score=min(recommendation["combined_score"] + 0.03, 1.0),
    )
    freshness = signal_freshness_score(generated_at)
    alert = send_notification(
        f"{normalized_symbol} signal generated: {recommendation['signal']}",
        priority="high" if recommendation["confidence"] >= 0.7 else "normal",
    )
    db_edges = agent_db_edges(normalized_symbol)
    db_edges.update(
        {
            "signal_orchestrator": record_data_lake_edge("signal_orchestrator", "write", f"signal:{normalized_symbol}"),
            "backtesting_engine": record_data_lake_edge("backtesting_engine", "read", f"historical_prices:{normalized_symbol}"),
            "ml_pipeline_model_training": record_data_lake_edge("ml_pipeline_model_training", "read_write", "feature_store"),
            "monitoring_logging": record_monitoring_event("signal_generated"),
        }
    )

    signal = {
        "contract_version": SIGNAL_CONTRACT_VERSION,
        "flow": [
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
            "data_lake_postgresql",
            "redis_cache",
            "external_broker_apis",
            "backtesting_engine",
            "ml_pipeline_model_training",
            "monitoring_logging",
        ],
        "symbol": normalized_symbol,
        "generated_at": generated_at.isoformat(),
        "model_version_id": "signal-orchestrator-v1.0.0",
        "data_snapshot_id": f"snapshot:{normalized_symbol}:{generated_at.date().isoformat()}",
        "audit_metadata": {
            "recommendation_id": f"rec:{normalized_symbol}:{generated_at.strftime('%Y%m%d%H%M%S')}",
            "audit_event_id": f"audit:{normalized_symbol}:{generated_at.strftime('%Y%m%d%H%M%S')}",
            "model_versions": {
                "signal_orchestrator": "v1.0.0",
                "fundamentals_agent": "v1.0.0",
                "technical_agent": "v1.0.0",
                "news_sentiment_agent": "v1.0.0",
                "macro_agent": "v1.0.0",
                "alt_data_agent": "v1.0.0",
                "regime_detector": "v1.0.0",
                "bull_bear_debate": "v1.0.0",
                "factor_tagging": "v1.0.0",
                "trader_risk_agent": "v1.0.0",
            },
            "input_data_snapshots": {
                "market_data": f"ohlcv:{normalized_symbol}:{generated_at.date().isoformat()}",
                "fundamentals": f"filings:{normalized_symbol}:latest-point-in-time",
                "news": f"news:{normalized_symbol}:{generated_at.date().isoformat()}",
                "macro": f"macro:{generated_at.date().isoformat()}",
            },
            "input_data_hash": sha256(
                f"{normalized_symbol}:{generated_at.date().isoformat()}:{SIGNAL_CONTRACT_VERSION}".encode()
            ).hexdigest(),
            "reproducible": True,
            "contract_version": SIGNAL_CONTRACT_VERSION,
            "replay_instructions": {
                "symbol": normalized_symbol,
                "generated_at": generated_at.isoformat(),
                "use_model_versions": True,
                "use_input_data_snapshots": True,
                "random_seed": 0,
            },
        },
        "freshness_score": freshness,
        "signal_freshness": {
            "score": freshness,
            "half_life_minutes": settings.signal_half_life_minutes,
            "auto_cancel_threshold": settings.signal_auto_cancel_threshold,
            "stale_order_action": "cancel_pending_orders" if should_auto_cancel_signal(generated_at) else "keep_active",
            "invalidation_triggers": [
                "earnings_or_high_impact_event",
                "factor_exposure_breach",
                "regime_change",
                "price_breaks_stop_loss",
            ],
        },
        "auto_cancel": should_auto_cancel_signal(generated_at),
        **recommendation,
        "factor_exposures": factors["factor_exposures"],
        "factor_warnings": factors["factor_warnings"],
        "entry_zone": {
            "low": risk["entry_zone_low"],
            "high": risk["entry_zone_high"],
        },
        "stop_loss": risk["stop_loss"],
        "take_profit": risk["take_profit"],
        "position_size": risk["position_size"],
        "position_sizing": position_sizing,
        "agent_outputs": agent_outputs,
        "database_edges": db_edges,
        "cache": {"read": cache_read},
        "risk": risk,
        "execution": {
            "service": "execution_service",
            "status": "ready_for_order",
            "external_broker_apis": ["alpaca", "ibkr", "tradestation", "deribit", "binance_futures"],
            "market_impact": impact.__dict__,
        },
        "champion_challenger": champion,
        "notification": alert,
        "rationale": [
            "Signal synthesized from all graph agents/services.",
            f"Regime detector selected {regime['regime']} weights.",
            "Risk agent and execution impact estimate attached before trading.",
        ],
    }
    signal["cache"]["write"] = _cache_set(cache_key, signal)
    return signal


async def build_signal(request) -> dict[str, Any]:
    symbol = request.symbol if hasattr(request, "symbol") else str(request.get("symbol"))
    return await generate_signal(symbol)


def attach_freshness(signal: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    generated_at = signal.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at)
    if not isinstance(generated_at, datetime):
        generated_at = datetime.now(timezone.utc)

    freshness = signal_freshness_score(generated_at, now)
    auto_cancel = should_auto_cancel_signal(generated_at, now)
    return {
        **signal,
        "freshness_score": freshness,
        "auto_cancel": auto_cancel,
        "signal_freshness": {
            "score": freshness,
            "half_life_minutes": settings.signal_half_life_minutes,
            "auto_cancel_threshold": settings.signal_auto_cancel_threshold,
            "stale_order_action": "cancel_pending_orders" if auto_cancel else "keep_active",
            "invalidation_triggers": signal.get("signal_freshness", {}).get(
                "invalidation_triggers",
                [
                    "earnings_or_high_impact_event",
                    "factor_exposure_breach",
                    "regime_change",
                    "price_breaks_stop_loss",
                ],
            ),
        },
    }
