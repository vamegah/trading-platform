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
    from backend.services.trader_operating_system import portfolio_command_center
    cmd = portfolio_command_center()
    totals = cmd.get("totals", {})
    positions = cmd.get("positions", [])
    total_market_value = sum(float(p.get("market_value", 0)) for p in positions)
    equity = float(totals.get("equity", total_market_value))
    cash = float(totals.get("cash", 0.0))
    gross_exposure = round(total_market_value / max(equity, 1.0), 4) if equity else 0.0
    long_val = sum(float(p.get("market_value", 0)) for p in positions if float(p.get("market_value", 0)) > 0)
    short_val = sum(float(p.get("market_value", 0)) for p in positions if float(p.get("market_value", 0)) < 0)
    net_exposure = round((long_val + short_val) / max(equity, 1.0), 4) if equity else 0.0
    risk_alerts = cmd.get("risk_alerts", [])
    risk_score = min(100, len(risk_alerts) * 15 + int(gross_exposure * 60))
    return PortfolioSnapshot(
        account_id=str(totals.get("account_id", "primary")),
        equity=equity,
        cash=cash,
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        risk_score=risk_score,
    )


@router.get("/health")
async def health() -> dict[str, str | int]:
    from backend.services.trader_operating_system import portfolio_command_center
    cmd = portfolio_command_center()
    risk_alerts = cmd.get("risk_alerts", [])
    risk_score = min(100, len(risk_alerts) * 15)
    return {"status": "balanced", "risk_score": risk_score, "rebalance_due": str(len(risk_alerts) > 0).lower()}


@router.post("/position-size")
async def position_size(payload: PositionSizingPayload) -> dict[str, object]:
    result = calculate_position_size(PositionSizingInput(**payload.model_dump()))
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
