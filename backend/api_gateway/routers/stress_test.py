from fastapi import APIRouter

from backend.services.stress_test_service.engine import StressTestEngine
from backend.services.stress_test_service.scenarios import list_scenarios

router = APIRouter()
engine = StressTestEngine()


@router.get("/scenarios")
async def scenarios() -> list[dict[str, object]]:
    return list_scenarios()


@router.post("/run/{scenario_name}")
async def run_stress_test(scenario_name: str, portfolio: list[dict]) -> dict[str, object]:
    return engine.run_portfolio_stress(portfolio, scenario_name)


@router.post("/custom")
async def run_custom_stress_test(payload: dict) -> dict[str, object]:
    return engine.run_portfolio_stress(
        payload.get("portfolio", []),
        payload.get("scenario_name", "custom"),
        custom_shocks=payload.get("shocks", {}),
    )
