from fastapi import FastAPI

from backend.services.agents.options_agent.greeks_engine import calculate_greeks
from backend.services.agents.options_agent.iv_analyzer import analyze_iv
from backend.services.agents.options_agent.strategy_builder import build_options_strategy
from backend.shared.observability import instrument_app

app = FastAPI(title="Options Agent", version="0.1.0")
instrument_app(app, "options_agent", {"options_data": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "options_agent", "status": "healthy"}


@app.get("/analyze/{symbol}")
async def analyze(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol.upper(),
        "asset_type": "options",
        "greeks": calculate_greeks(symbol),
        "iv": analyze_iv(symbol),
        "strategy": build_options_strategy(symbol),
    }
