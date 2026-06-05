def build_options_strategy(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol.upper(),
        "strategy": "defined_risk_call_spread",
        "max_risk": 250.0,
        "target_reward": 420.0,
    }

