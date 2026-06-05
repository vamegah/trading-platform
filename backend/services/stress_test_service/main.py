from fastapi import FastAPI

from backend.services.stress_test_service.engine import StressTestEngine
from backend.services.stress_test_service.scenarios import list_scenarios
from backend.shared.observability import RequestContextMiddleware, add_observability_routes

app = FastAPI(title="Stress Test Service", version="0.1.0")
app.add_middleware(RequestContextMiddleware)
add_observability_routes(app, "stress_test_service", {"data_lake": "configured"})
engine = StressTestEngine()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "stress_test_service", "status": "healthy"}


@app.get("/scenarios")
async def scenarios() -> list[dict[str, object]]:
    return list_scenarios()


@app.post("/run/{scenario_name}")
async def run_stress_test(scenario_name: str, portfolio: list[dict]) -> dict[str, object]:
    return engine.run_portfolio_stress(portfolio, scenario_name)
