from fastapi import FastAPI

from backend.services.agents.trader_risk_agent.position_sizer import size_position
from backend.services.agents.trader_risk_agent.risk_manager import assess_risk
from backend.shared.observability import instrument_app

app = FastAPI(title="Trader Risk Agent", version="0.1.0")
instrument_app(app, "trader_risk_agent", {"risk_limits": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "trader_risk_agent", "status": "healthy"}


@app.get("/risk/{symbol}")
async def risk(symbol: str, equity: float = 100000.0) -> dict[str, float | str]:
    assessment = assess_risk(symbol)
    assessment["position_size"] = size_position(equity, float(assessment["risk_score"]))
    return assessment


async def generate_order_from_signal(signal: dict, user: dict | None = None) -> dict[str, object] | None:
    action = signal.get("signal") or signal.get("recommendation")
    symbol = str(signal["symbol"]).upper()
    if action not in {"BUY", "SELL"}:
        return None
    price = float(signal.get("entry_price") or signal.get("price") or 100.0)
    quantity = float(signal.get("position_size", 0.0)) / price
    if quantity <= 0:
        quantity = 1.0
    return {
        "symbol": symbol,
        "side": action,
        "quantity": round(quantity, 4),
        "order_type": "limit",
        "limit_price": round(price, 2),
        "user_id": (user or {}).get("id", "demo"),
    }
