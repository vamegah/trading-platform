from backend.services.stress_test_service.engine import StressTestEngine


def test_stress_test_engine_runs_predefined_scenario() -> None:
    engine = StressTestEngine()
    result = engine.run_portfolio_stress(
        portfolio=[
            {"symbol": "SPY", "market_value": 100000, "factor_betas": {"market": 1.0}},
            {"symbol": "QQQ", "market_value": 50000, "factor_betas": {"market": 1.2}},
        ],
        scenario_name="2008_financial_crisis",
    )

    assert result["scenario"] == "2008_financial_crisis"
    assert result["portfolio_value_after"] < result["portfolio_value_before"]
    assert len(result["positions"]) == 2

