from fastapi import FastAPI

from backend.data_pipeline.ingestion.orchestrator import data_orchestrator
from backend.shared.external_api.router import external_api_router
from backend.shared.observability import instrument_app

app = FastAPI(title="External API Orchestrator", version="0.1.0")
instrument_app(app, "api_orchestrator", {"providers": "configured", "redis": "optional"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "api_orchestrator", "status": "healthy"}


@app.get("/quote/{symbol}")
async def quote(symbol: str, asset_class: str = "equity") -> dict[str, object]:
    return await data_orchestrator.get_quote(symbol, asset_class)


@app.get("/news/{symbol}")
async def news(symbol: str) -> dict[str, object]:
    return await data_orchestrator.get_news(symbol)


@app.get("/status")
async def status() -> dict[str, object]:
    return external_api_router.status()
