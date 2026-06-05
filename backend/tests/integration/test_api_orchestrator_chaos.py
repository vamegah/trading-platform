import pytest

from backend.shared.external_api.chaos import run_experiment


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "experiment_id",
    [
        "exp1_provider_outage",
        "exp2_provider_flapping",
        "exp3_cache_poisoning",
        "exp4_latency_spike_hedging",
        "exp5_websocket_exhaustion",
        "exp6_llm_budget_exhaustion",
        "exp7_audit_log_disruption",
        "exp8_sandbox_escape",
        "exp9_deployment_rollback",
    ],
)
async def test_chaos_experiments_pass_in_safe_simulation(experiment_id: str) -> None:
    result = await run_experiment(experiment_id)

    assert result.passed is True
    assert result.metrics


@pytest.mark.asyncio
async def test_provider_outage_records_failover_metrics() -> None:
    result = await run_experiment("exp1_provider_outage")

    assert result.metrics["provider"] == "alpha_vantage"
    assert result.metrics["failover_latency_ms"] < 2000
    assert "half_open" in result.metrics["circuit_states"]


@pytest.mark.asyncio
async def test_cache_poisoning_experiment_never_delivers_bad_quote() -> None:
    result = await run_experiment("exp3_cache_poisoning")

    assert result.metrics["poisoned_rejected"] is True
    assert "Data integrity violation detected" in result.alerts
