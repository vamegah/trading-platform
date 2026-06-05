from fastapi import FastAPI

from backend.services.signal_orchestrator.orchestrator import build_signal
from backend.shared.models import SignalRequest
from backend.shared.observability import RequestContextMiddleware, add_observability_routes

app = FastAPI(title="Signal Orchestrator", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
add_observability_routes(app, "signal_orchestrator", {"redis": "optional"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "signal_orchestrator", "status": "healthy"}


@app.post("/signals/evaluate")
async def evaluate(request: SignalRequest) -> dict:
    return await build_signal(request)
