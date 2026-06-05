from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.agents.trader_risk_agent.event_risk import evaluate_event_risk
from backend.services.agents.trader_risk_agent.position_sizer import PositionSizingInput, calculate_position_size
from backend.services.execution_service.order_router import execution_precheck
from backend.services.portfolio_service.optimizer import evaluate_trade_impact
from backend.services.portfolio_service.risk_monitor import LiveRiskMonitor, RiskLimits
from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord
from backend.services.portfolio_service.tax_optimizer import optimize_after_tax_sale
from backend.services.safety_service.circuit_breaker import CircuitBreaker
from backend.services.user_service.suitability import evaluate_suitability


def test_suitability_blocks_unsuitable_automated_trading() -> None:
    decision = evaluate_suitability(
        {
            "investment_experience": "beginner",
            "risk_tolerance": "low",
            "annual_income": "below_50k",
            "net_worth": "below_50k",
            "investment_horizon": "short",
            "loss_tolerance": "sell_all",
        }
    )

    assert decision.completed is True
    assert decision.automation_allowed is False
    assert "automated_trading" in decision.restricted_strategies


def test_position_sizer_respects_risk_constraints() -> None:
    result = calculate_position_size(
        PositionSizingInput(
            equity=100000,
            entry_price=100,
            stop_loss=95,
            win_probability=0.58,
            average_win_pct=0.08,
            average_loss_pct=-0.04,
            volatility=0.025,
            portfolio_volatility=0.015,
            max_drawdown_tolerance=0.18,
            current_portfolio_risk=0.08,
            risk_profile="balanced",
        )
    )

    assert result.quantity > 0
    assert result.portfolio_weight <= 0.2
    assert result.limiting_constraint in result.components
    assert result.remaining_drawdown_budget == 0.1
    assert result.risk_profile_multiplier == 0.85


def test_position_sizer_blocks_when_drawdown_budget_is_exhausted() -> None:
    result = calculate_position_size(
        PositionSizingInput(
            equity=100000,
            entry_price=100,
            stop_loss=95,
            win_probability=0.7,
            average_win_pct=0.08,
            average_loss_pct=-0.04,
            volatility=0.02,
            portfolio_volatility=0.015,
            max_drawdown_tolerance=0.1,
            current_portfolio_risk=0.12,
            risk_profile="aggressive",
        )
    )

    assert result.quantity == 0
    assert result.remaining_drawdown_budget == 0.0
    assert result.risk_budget == 0.0


def test_portfolio_optimizer_reports_factor_sector_and_correlation_breaches() -> None:
    result = evaluate_trade_impact(
        holdings={"AAPL": 70000, "MSFT": 30000},
        proposed_trade={"symbol": "NVDA", "side": "BUY", "notional": 50000},
        constraints={
            "max_sector_weight": 0.55,
            "max_factor_exposure": 0.35,
            "correlations": {"AAPL-MSFT": 0.92},
        },
    )

    assert result["after"]["constraint_breaches"]
    assert result["trade_allowed"] is False
    assert "expected_sharpe_delta" in result
    assert "concentration_delta" in result
    assert result["constraint_impact"]["after_breach_count"] >= 1
    assert result["review_required"] is True


def test_live_risk_monitor_flags_kill_switch_breaches() -> None:
    result = LiveRiskMonitor().evaluate(
        [
            {
                "symbol": "QQQ",
                "market_value": 150000,
                "beta": 1.8,
                "volatility": 0.04,
                "correlation": 0.91,
                "margin": 90000,
                "stop_loss_pct": 0.12,
            }
        ],
        RiskLimits(var_limit=3000, cvar_limit=5000, beta_limit=1.2, dollar_risk_limit=10000),
    )

    assert result["kill_switch_required"] is True
    assert {breach["metric"] for breach in result["breaches"]} >= {"var", "beta", "dollar_risk"}
    assert result["new_orders_blocked"] is True
    assert result["cancel_pending_orders"] is True
    assert result["within_target_latency"] is True
    assert {event["event_type"] for event in result["risk_breach_events"]} == {"portfolio_risk_breach"}


def test_execution_precheck_consumes_risk_breach_events() -> None:
    risk_result = LiveRiskMonitor().evaluate(
        [{"symbol": "QQQ", "market_value": 150000, "beta": 2.0, "volatility": 0.05}],
        RiskLimits(var_limit=1000),
    )

    result = execution_precheck(
        {
            "suitability_completed": True,
            "live_risk_result": risk_result,
            "automation_consent": True,
            "mode": "one_click",
        }
    )

    assert result["allowed"] is False
    assert "portfolio_risk_breach" in result["violations"]
    assert "kill_switch_active" in result["violations"]
    assert result["risk_breach_events"]


def test_event_risk_protocol_reduces_or_blocks_upcoming_high_impact_events() -> None:
    result = evaluate_event_risk(
        "MRNA",
        [{"type": "fda_decision", "date": (date.today() + timedelta(days=3)).isoformat()}],
    )

    assert result["block_new_automation"] is True
    assert result["size_multiplier"] == 0.5
    assert result["hedge_recommendation"] == "buy_protective_put_or_reduce_delta"


def test_medium_event_risk_flags_review_without_blocking_automation() -> None:
    result = evaluate_event_risk(
        "AAPL",
        [{"type": "investor_day", "date": (date.today() + timedelta(days=5)).isoformat()}],
    )

    assert result["action"] == "flag_for_review"
    assert result["block_new_automation"] is False
    assert result["position_size_multiplier"] == 0.8


def test_tax_optimizer_reports_wash_sale_and_holding_period_controls() -> None:
    as_of = date(2026, 1, 15)
    result = optimize_after_tax_sale(
        lots=[TaxLotRecord("loss", "MSFT", 10, 150, date(2025, 12, 1))],
        quantity=5,
        current_price=100,
        replacement_transactions=[{"symbol": "MSFT", "side": "BUY", "date": "2026-01-05"}],
        as_of=as_of,
    )

    selection = result["selections"][0]
    assert selection["lot"].lot_id == "loss"
    assert selection["wash_sale_risk"] is True
    assert selection["term"] == "short_term"
    assert result["tax_impact"]["disallowed_wash_sale_loss"] == 250


def test_circuit_breaker_halt_blocks_new_orders_and_cancels_pending() -> None:
    breaker = CircuitBreaker()
    breaker.trigger_halt("risk breach", admin_id="risk-admin")

    guarded = breaker.guard_order({"symbol": "MSFT"})

    assert guarded["allowed"] is False
    assert guarded["new_orders_blocked"] is True
    assert guarded["cancel_pending_orders"] is True


@pytest.mark.asyncio
async def test_milestone4_gateway_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        suitability = await client.post(
            "/api/profile/suitability/guard",
            json={
                "answers": {
                    "investment_experience": "advanced",
                    "risk_tolerance": "high",
                    "annual_income": "above_250k",
                    "net_worth": "above_1m",
                    "investment_horizon": "very_long",
                    "loss_tolerance": "buy_more",
                },
                "requested_strategy": "automated_trading",
            },
        )
        precheck = await client.post(
            "/execution/precheck",
            json={"suitability_completed": False, "risk_breach": False, "stale_signal": False},
        )
        custom_stress = await client.post(
            "/stress-test/custom",
            json={
                "scenario_name": "custom_oil_spike",
                "shocks": {"market": -0.1, "oil": 0.4},
                "portfolio": [{"symbol": "XOM", "market_value": 10000, "factor_betas": {"oil": 0.8}}],
            },
        )
        harvest = await client.post(
            "/portfolio/tax/harvest",
            json={
                "lots": [
                    {
                        "lot_id": "loss",
                        "symbol": "MSFT",
                        "quantity": 10,
                        "cost_per_share": 150,
                        "acquisition_date": "2024-01-01",
                    }
                ],
                "current_prices": {"MSFT": 100},
                "minimum_loss": 100,
            },
        )

    assert suitability.status_code == 200
    assert suitability.json()["allowed"] is True
    assert precheck.status_code == 200
    assert precheck.json()["allowed"] is False
    assert "suitability_required" in precheck.json()["violations"]
    assert custom_stress.status_code == 200
    assert custom_stress.json()["scenario"] == "custom_oil_spike"
    assert custom_stress.json()["custom_scenario"] is True
    assert custom_stress.json()["recommended_actions"]
    assert harvest.status_code == 200
    assert harvest.json()["count"] == 1
    assert harvest.json()["opportunities"][0]["holding_period_days"] > 0
