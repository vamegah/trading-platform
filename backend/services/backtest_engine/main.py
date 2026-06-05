from fastapi import FastAPI

from backend.services.backtest_engine.walk_forward import run_walk_forward
from backend.shared.models import BacktestRequest, BacktestResult
from backend.shared.observability import instrument_app

app = FastAPI(title="Backtest Engine", version="0.1.0")
instrument_app(app, "backtest_engine", {"data_lake": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "backtest_engine", "status": "healthy"}


@app.post("/run", response_model=BacktestResult)
async def run(request: BacktestRequest) -> BacktestResult:
    return run_walk_forward(request)
