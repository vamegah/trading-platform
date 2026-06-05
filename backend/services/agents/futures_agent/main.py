from fastapi import FastAPI

from backend.services.agents.futures_agent.carry_model import calculate_carry
from backend.services.agents.futures_agent.term_structure import analyze_term_structure
from backend.shared.observability import instrument_app

app = FastAPI(title="Futures Agent", version="0.1.0")
instrument_app(app, "futures_agent", {"futures_data": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "futures_agent", "status": "healthy"}


@app.get("/analyze/{root_symbol}")
async def analyze(root_symbol: str) -> dict[str, object]:
    return {
        "root_symbol": root_symbol.upper(),
        "asset_type": "futures",
        "term_structure": analyze_term_structure(root_symbol),
        "carry": calculate_carry(root_symbol),
    }
