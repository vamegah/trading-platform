from fastapi import FastAPI

from backend.services.agents.fundamentals_agent.analyzer import analyze_fundamentals
from backend.shared.observability import instrument_app

app = FastAPI(title="Fundamentals Agent", version="0.1.0")
instrument_app(app, "fundamentals_agent", {"filings": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "fundamentals_agent", "status": "healthy"}


@app.get("/analyze/{symbol}")
async def analyze(symbol: str) -> dict[str, str | float]:
    return analyze_fundamentals(symbol)
