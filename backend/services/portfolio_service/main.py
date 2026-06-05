from fastapi import FastAPI

from backend.services.portfolio_service.optimizer import optimize_portfolio
from backend.shared.observability import RequestContextMiddleware, add_observability_routes

app = FastAPI(title="Portfolio Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
add_observability_routes(app, "portfolio_service", {"database": "configured"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "portfolio_service", "status": "healthy"}


@app.post("/optimize")
async def optimize(holdings: dict[str, float]) -> dict[str, object]:
    return optimize_portfolio(holdings)
