from fastapi import FastAPI

from backend.services.agents.technical_agent.analyzer import analyze_technicals
from backend.services.agents.technical_agent.multi_tf import aggregate_timeframes
from backend.services.agents.technical_agent.pattern_engine import detect_patterns
from backend.shared.observability import instrument_app

app = FastAPI(title="Technical Agent", version="0.1.0")
instrument_app(app, "technical_agent", {"market_data": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "technical_agent", "status": "healthy"}


@app.get("/patterns/{symbol}")
async def patterns(symbol: str) -> dict[str, object]:
    return detect_patterns(symbol)


@app.post("/analyze/{symbol}")
async def analyze(symbol: str, payload: dict | None = None) -> dict[str, object]:
    candles = (payload or {}).get("candles")
    asset_type = (payload or {}).get("asset_type", "equity")
    return analyze_technicals(symbol, candles, asset_type)


@app.post("/multi-timeframe/{symbol}")
async def multi_timeframe(symbol: str, payload: dict) -> dict[str, object]:
    return aggregate_timeframes(symbol, payload.get("timeframes", {}))
