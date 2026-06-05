import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.ml_training.champion_challenger import ChampionChallengerManager
from backend.ml_training.evaluation import decay_monitor, drift_score, monitor_model_health
from backend.services.backtest_engine.backtest_engine import full_walkforward_backtest
from backend.services.backtest_engine.cost_model import estimate_transaction_cost
from backend.services.backtest_engine.metrics import summarize_performance
from backend.services.execution_service.trade_journal import TradeJournal
from backend.services.paper_trading import PaperTradingAccount


@pytest.mark.asyncio
async def test_walk_forward_backtest_is_point_in_time_and_benchmark_aware() -> None:
    result = await full_walkforward_backtest("MSFT", days=180)

    assert result["survivorship_bias_free"] is True
    assert "MSFT" in result["point_in_time_universe"]
    assert result["data_snapshot_id"].startswith("pit:")
    assert {"sharpe", "sortino", "max_drawdown", "profit_factor", "calmar"}.issubset(result["metrics"])
    assert "excess_return" in result["benchmark"]
    assert result["cost_model"] == "commission_spread_slippage_almgren_chriss_liquidity"
    assert result["walk_forward_window_count"] >= 1
    assert len(result["equity_curve"]) == 180
    assert result["equity_curve"][0] == 100000.0
    assert result["no_lookahead_validation"]["all_windows_lookahead_safe"] is True


@pytest.mark.asyncio
async def test_walk_forward_backtest_includes_delisted_point_in_time_membership() -> None:
    result = await full_walkforward_backtest(
        "LEHMQ",
        start_date="2008-01-01",
        end_date="2008-09-20",
        days=260,
    )

    assert "LEHMQ" in result["point_in_time_universe"]
    assert result["delisted_during_backtest"] is True
    assert any(row["symbol"] == "LEHMQ" for row in result["point_in_time_universe_snapshot"])


def test_realistic_cost_model_penalizes_large_illiquid_orders() -> None:
    small = estimate_transaction_cost("MSFT", "BUY", quantity=100, price=100, daily_volume=1_000_000)
    large = estimate_transaction_cost("MSFT", "BUY", quantity=200_000, price=100, daily_volume=300_000)

    assert large.total_cost > small.total_cost
    assert large.liquidity_penalty > 0
    assert large.market_impact > small.market_impact
    assert large.capacity_warning is True
    assert large.participation_rate > small.participation_rate


def test_performance_metrics_match_known_fixture_directionally() -> None:
    metrics = summarize_performance(
        equity_curve=[100, 104, 102, 108, 112],
        returns=[0.0, 0.04, -0.0192, 0.0588, 0.037],
        trades=[{"pnl": 400}, {"pnl": -100}, {"pnl": 250}],
    )

    assert metrics["max_drawdown"] == 0.0192
    assert metrics["win_rate"] == 0.6667
    assert metrics["profit_factor"] == 6.5
    assert metrics["calmar"] > 0


def test_champion_challenger_and_model_monitors_gate_promotion_and_alerts() -> None:
    decision = ChampionChallengerManager().evaluate_run(
        "signal_orchestrator",
        champion_scores=[0.6, 0.61, 0.62],
        challenger_scores=[0.66, 0.67, 0.68],
        out_of_sample=True,
    )

    assert decision["model_promotion_pipeline"]["promotion_recommended"] is True
    assert decision["model_promotion_pipeline"]["checks"]["out_of_sample"] is True
    assert drift_score([0.5, 0.51, 0.52], [0.7, 0.71, 0.72]) > 0.15
    assert decay_monitor([20, 130, 160, 180])["decay_alert"] is True


@pytest.mark.asyncio
async def test_paper_trading_uses_precheck_router_cost_model_and_journal_attribution() -> None:
    account = PaperTradingAccount(balance=50000, account_id="paper-test")
    result = await account.execute_signal_async(
        {
            "symbol": "MSFT",
            "signal": "BUY",
            "confidence": 0.72,
            "price": 100,
            "position_size": 5000,
            "model_version_id": "signal-v1",
            "data_snapshot_id": "snapshot-msft",
            "factor_exposures": {"quality": 0.7, "growth": 0.4},
        }
    )

    assert result["status"] == "executed"
    assert result["precheck"]["allowed"] is True
    assert result["paper_execution_parity"]["same_order_router_contract"] is True
    assert result["estimated_transaction_cost"]["total_cost"] > 0
    assert result["journal_entry"]["model_version_id"] == "signal-v1"
    assert result["journal_entry"]["attribution"]["factor_breakdown"]["quality"] == 0.7


def test_trade_journal_tags_snapshot_model_and_cost_attribution() -> None:
    entry = TradeJournal().log_trade(
        {
            "symbol": "AAPL",
            "action": "BUY",
            "cost": 12.5,
            "gross_notional": 10000,
            "paper_account_id": "paper-test",
            "precheck": {"allowed": True},
            "estimated_transaction_cost": {"total_cost": 12.5},
        },
        {
            "symbol": "AAPL",
            "signal": "BUY",
            "confidence": 0.7,
            "model_version_id": "model-v1",
            "data_snapshot_id": "snapshot-aapl",
            "factor_exposures": {"quality": 0.6},
        },
    )

    assert {"paper", "prechecked", "costed", "model_versioned", "snapshot_linked"}.issubset(entry["trade_tags"])
    assert entry["attribution"]["execution_drag_bps"] < 0


def test_model_health_monitor_returns_structured_alerts() -> None:
    result = monitor_model_health(
        reference=[0.5, 0.51, 0.52],
        latest=[0.7, 0.71, 0.72],
        actual=[1, 0, 1],
        predicted_probability=[0.8, 0.7, 0.75],
        signal_ages_minutes=[20, 140, 160, 180],
    )

    assert result["alert"] is True
    assert {alert["type"] for alert in result["monitoring_alerts"]} >= {"model_drift", "signal_decay"}


@pytest.mark.asyncio
async def test_milestone5_gateway_endpoints_cover_backtest_paper_and_validation() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        backtest = await client.post("/backtest/walk-forward", json={"symbol": "MSFT", "days": 120})
        paper = await client.post("/paper/execute/MSFT")
        journal = await client.get("/paper/journal")
        validation = await client.post(
            "/validation/champion-challenger",
            json={
                "model_name": "signal_orchestrator",
                "champion_scores": [0.6, 0.61, 0.62],
                "challenger_scores": [0.66, 0.67, 0.68],
            },
        )
        monitor = await client.post(
            "/validation/monitor",
            json={
                "reference": [0.5, 0.51, 0.52],
                "latest": [0.7, 0.71, 0.72],
                "actual": [1, 0, 1],
                "predicted_probability": [0.8, 0.7, 0.75],
                "signal_ages_minutes": [20, 140, 160, 180],
            },
        )

    assert backtest.status_code == 200
    assert backtest.json()["metrics"]["sharpe"] is not None
    assert len(backtest.json()["equity_curve"]) >= 2
    assert paper.status_code == 200
    assert paper.json()["status"] in {"executed", "skipped"}
    assert journal.status_code == 200
    assert "entries" in journal.json()
    assert validation.json()["model_promotion_pipeline"]["gate"] == "passed"
    assert monitor.json()["alert"] is True
