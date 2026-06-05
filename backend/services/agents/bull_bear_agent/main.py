from fastapi import FastAPI

from backend.services.agents.bull_bear_agent.debate_engine import run_debate
from backend.shared.observability import instrument_app

app = FastAPI(title="Bull Bear Agent", version="0.1.0")
instrument_app(app, "bull_bear_agent", {"signal_inputs": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "bull_bear_agent", "status": "healthy"}


@app.get("/debate/{symbol}")
async def debate(symbol: str) -> dict[str, object]:
    return run_debate(symbol)
