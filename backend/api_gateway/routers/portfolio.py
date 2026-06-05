from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.agents.trader_risk_agent.position_sizer import (
    PositionSizingInput,
    calculate_position_size,
)
from backend.services.portfolio_service.optimizer import evaluate_trade_impact, optimize_portfolio
from backend.services.portfolio_service.risk_monitor import LiveRiskMonitor, RiskLimits
from backend.shared.event_bus import event_bus
from backend.shared.events import EVENT_TYPES, TOPICS
from backend.shared.models import PortfolioSnapshot

router = APIRouter()
risk_monitor = LiveRiskMonitor()


class PositionSizingPayload(BaseModel):
    equity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    win_probability: float = Field(ge=0, le=1)
    average_win_pct: float = Field(gt=0)
    average_loss_pct: float = Field(lt=0)
    volatility: float = Field(gt=0)
    portfolio_volatility: float = Field(gt=0)
    max_drawdown_tolerance: float = Field(gt=0)
    current_portfolio_risk: float = 0.0
    risk_profile: str = "balanced"


@router.get("/summary", response_model=PortfolioSnapshot)
async def summary() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        account_id="demo",
        equity=125000.0,
        cash=18420.0,
        gross_exposure=0.82,
        net_exposure=0.48,
        risk_score=58,
    )


@router.get("/health")
async def health() -> dict[str, str | int]:
    return {"status": "balanced", "risk_score": 58, "rebalance_due": "false"}


@router.post("/position-size")
async def position_size(payload: PositionSizingPayload) -> dict[str, object]:
    result = calculate_position_size(PositionSizingInput(**payload.dict()))
    return result.__dict__


@router.post("/optimize")
async def optimize(payload: dict) -> dict[str, object]:
    return optimize_portfolio(payload.get("holdings", {}), payload.get("constraints", {}))


@router.post("/trade-impact")
async def trade_impact(payload: dict) -> dict[str, object]:
    return evaluate_trade_impact(
        payload.get("holdings", {}),
        payload.get("proposed_trade", {}),
        payload.get("constraints", {}),
    )


@router.post("/risk/live")
async def live_risk(payload: dict) -> dict[str, object]:
    limits_payload = payload.get("limits") or {}
    limits = RiskLimits(**limits_payload) if limits_payload else RiskLimits()
    return risk_monitor.evaluate(payload.get("portfolio", []), limits)


@router.post("/commands/risk/live", status_code=202)
async def enqueue_live_risk(payload: dict) -> dict[str, object]:
    result = event_bus.publish(
        TOPICS.portfolio_commands,
        EVENT_TYPES.portfolio_risk_requested,
        payload,
        source="api_gateway",
    )
    return {
        "status": "accepted",
        "command": EVENT_TYPES.portfolio_risk_requested,
        "result_topic": TOPICS.portfolio_events,
        **result,
    }
