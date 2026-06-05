from backend.services.backtest_engine.cost_model import estimate_transaction_cost
from backend.services.backtest_engine.metrics import summarize_performance


def test_known_backtest_metric_fixture_outputs_expected_values() -> None:
    metrics = summarize_performance(
        equity_curve=[100000, 102000, 101000, 105000, 103000],
        returns=[0, 0.02, -0.0098, 0.0396, -0.019],
        trades=[{"pnl": 2000}, {"pnl": -1000}, {"pnl": 1500}],
    )

    assert metrics["max_drawdown"] == 0.019
    assert metrics["win_rate"] == 0.6667
    assert metrics["profit_factor"] == 3.5
    assert metrics["sortino"] > 0
    assert metrics["trade_count"] == 3
    assert metrics["expectancy"] > 0


def test_flat_equity_curve_has_zero_drawdown_and_zero_risk_ratios() -> None:
    metrics = summarize_performance(
        equity_curve=[100000, 100000, 100000],
        returns=[0, 0, 0],
        trades=[],
    )

    assert metrics["max_drawdown"] == 0
    assert metrics["sharpe"] == 0
    assert metrics["sortino"] == 0
    assert metrics["calmar"] == 0


def test_cost_assumptions_penalize_illiquid_large_orders() -> None:
    liquid = estimate_transaction_cost("SPY", "BUY", 100, 500, daily_volume=50_000_000)
    illiquid = estimate_transaction_cost("SMALL", "BUY", 100_000, 5, daily_volume=200_000)

    assert illiquid.return_drag > liquid.return_drag
    assert illiquid.liquidity_penalty > 0
    assert illiquid.total_cost > liquid.total_cost
    assert illiquid.capacity_warning is True


def test_zero_quantity_cost_model_is_safe_and_costless() -> None:
    cost = estimate_transaction_cost("SPY", "BUY", 0, 500, daily_volume=50_000_000)

    assert cost.total_cost == 0
    assert cost.return_drag == 0
    assert cost.participation_rate == 0
