from backend.ml_training.models.regime_hmm import RegimeHmm


def detect_market_regime(features: dict[str, float] | None = None) -> dict[str, object]:
    inputs = features or {"volatility": 0.18, "trend": 0.04, "liquidity": 0.7}
    regime = RegimeHmm().classify(inputs)
    weights = {
        "fundamentals": 0.22,
        "technical": 0.22,
        "news_sentiment": 0.16,
        "macro": 0.14,
        "alt_data": 0.08,
        "debate": 0.1,
        "tax": 0.08,
    }
    if regime in {"risk_off", "bear", "high_volatility"}:
        weights.update({"macro": 0.22, "technical": 0.16, "fundamentals": 0.18})
    elif regime == "bull":
        weights.update({"technical": 0.26, "news_sentiment": 0.2, "fundamentals": 0.2, "macro": 0.1})
    elif regime == "sideways":
        weights.update({"fundamentals": 0.26, "technical": 0.18, "debate": 0.12})
    total = sum(weights.values()) or 1.0
    weights = {key: round(value / total, 4) for key, value in weights.items()}
    return {"agent": "regime_detector", "regime": regime, "features": inputs, "agent_weights": weights}
