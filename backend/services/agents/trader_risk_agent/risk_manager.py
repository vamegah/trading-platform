from backend.services.agents.trader_risk_agent.event_risk import evaluate_event_risk


def assess_risk(symbol: str, events: list[dict] | None = None) -> dict[str, float | str | dict]:
    current_price = 100.0
    volatility = 0.025
    entry_low = current_price * 0.985
    entry_high = current_price * 1.005
    stop_loss = current_price * (1 - volatility * 2.5)
    take_profit = current_price * (1 + volatility * 4)
    event_protocol = evaluate_event_risk(symbol, events)
    return {
        "symbol": symbol.upper(),
        "agent": "trader_risk",
        "risk_score": 0.42,
        "max_portfolio_weight": 0.08,
        "entry_zone_low": round(entry_low, 2),
        "entry_zone_high": round(entry_high, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "confidence_adjustment": -0.03,
        "event_risk_protocol": event_protocol,
    }
