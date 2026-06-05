from fastapi import FastAPI

from backend.services.agents.macro_agent.economic_indicators import macro_regime
from backend.shared.observability import instrument_app

app = FastAPI(title="Macro Agent", version="0.1.0")
instrument_app(app, "macro_agent", {"macro_data": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "macro_agent", "status": "healthy"}


@app.get("/regime")
async def regime() -> dict[str, str | float]:
    return macro_regime()
