import pytest

from backend.services.signal_orchestrator.orchestrator import generate_signal


@pytest.mark.asyncio
async def test_final_recommendation_contract_has_required_risk_explainability_and_audit_fields() -> None:
    signal = await generate_signal("NVDA", {"factor_load": {"growth": 0.5, "momentum": 0.3}})

    assert signal["signal"] in {"BUY", "SELL", "HOLD"}
    assert {"up_5pct_20d", "down_3pct_20d", "tail_loss_8pct_20d"}.issubset(signal["probability_distribution"])
    assert signal["factor_exposures"] if "factor_exposures" in signal else signal["agent_outputs"]["factor_tagging"]
    assert signal["tail_risk_summary"]
    assert signal["freshness_score"] <= 1
    assert signal["audit_metadata"]["reproducible"] is True
    assert signal["audit_metadata"]["input_data_hash"]
    assert signal["audit_metadata"]["replay_instructions"]["symbol"] == "NVDA"
    assert signal["audit_metadata"]["contract_version"] == signal["contract_version"]
    assert signal["model_version_id"]
    assert signal["data_snapshot_id"]
    assert signal["explainability"]["top_drivers"]
    assert abs(
        signal["probability_distribution"]["up_5pct_20d"]
        + signal["probability_distribution"]["down_3pct_20d"]
        + signal["probability_distribution"]["flat_20d"]
        - 1
    ) <= 0.001
    assert signal["cache"]["read"]["store"] == "redis_cache"
    assert signal["cache"]["write"]["store"] == "redis_cache"
    assert signal["signal_freshness"]["invalidation_triggers"]


@pytest.mark.asyncio
async def test_repeated_signal_uses_current_cached_contract_without_losing_audit_metadata() -> None:
    first = await generate_signal("AAPL")
    second = await generate_signal("AAPL")

    assert first["contract_version"] == second["contract_version"]
    assert second["cache"]["read"]["hit"] is True
    assert second["audit_metadata"]["reproducible"] is True
    assert second["audit_metadata"]["input_data_snapshots"] == first["audit_metadata"]["input_data_snapshots"]
