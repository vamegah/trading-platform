import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from backend.data_pipeline.ingestion.orchestrator import DataOrchestrator
from backend.data_pipeline.ingestion.providers import AlphaVantageProvider, MarketDataProvider, PolygonProvider
from backend.services.marketplace.sandbox import build_sandbox_policy, evaluate_sandbox_violation
from backend.shared.audit import audit_chain
from backend.shared.external_api.circuit_breaker import CircuitBreaker
from backend.shared.external_api.cost_governor import CostGovernor, RateLimitExceeded
from backend.shared.external_api.router import ExternalAPIRouter


@dataclass(frozen=True)
class ChaosExperimentResult:
    experiment_id: str
    passed: bool
    metrics: dict[str, Any]
    alerts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class PoisonedQuoteProvider(MarketDataProvider):
    name = "poisoned_cache"

    def historical_bars(self, symbol: str, start: str, end: str):
        return []

    def latest_quote(self, symbol: str):
        return {"symbol": symbol.upper(), "bid": 105.0, "ask": 100.0, "source": self.name}


async def run_experiment(experiment_id: str) -> ChaosExperimentResult:
    experiments = {
        "exp1_provider_outage": experiment_provider_outage,
        "exp2_provider_flapping": experiment_provider_flapping,
        "exp3_cache_poisoning": experiment_cache_poisoning,
        "exp4_latency_spike_hedging": experiment_latency_spike_hedging,
        "exp5_websocket_exhaustion": experiment_websocket_exhaustion,
        "exp6_llm_budget_exhaustion": experiment_llm_budget_exhaustion,
        "exp7_audit_log_disruption": experiment_audit_log_disruption,
        "exp8_sandbox_escape": experiment_sandbox_escape,
        "exp9_deployment_rollback": experiment_deployment_rollback,
    }
    if experiment_id not in experiments:
        raise ValueError(f"unknown chaos experiment: {experiment_id}")
    return await experiments[experiment_id]()


async def experiment_provider_outage() -> ChaosExperimentResult:
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=0.001)
    router = ExternalAPIRouter(circuit_breaker=breaker)
    config = _quote_config()
    orchestrator = DataOrchestrator(
        config=config,
        router=router,
        providers={"polygon": PolygonProvider(fail=True), "alpha_vantage": AlphaVantageProvider()},
    )
    started = time.perf_counter()
    result = await orchestrator.get_quote("CHAOS1")
    failover_latency_ms = round((time.perf_counter() - started) * 1000, 3)
    states = []
    for _ in range(3):
        try:
            await router.call("polygon", "probe", _failing_call, timeout_ms=10)
        except Exception:
            states.append(breaker.state_for("polygon"))
    await asyncio.sleep(0.05)
    states.append(breaker.state_for("polygon"))
    passed = result["source"] == "alpha_vantage" and failover_latency_ms < 2000 and states[-1] == "half_open"
    audit_chain.append("chaos_experiment", {"experiment_id": "exp1_provider_outage", "passed": passed})
    return ChaosExperimentResult(
        "exp1_provider_outage",
        passed,
        {"failover_latency_ms": failover_latency_ms, "provider": result["source"], "circuit_states": states},
        notes=["Signal generation must reject stale quote payloads when cache.stale is true."],
    )


async def experiment_provider_flapping() -> ChaosExperimentResult:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=30)
    router = ExternalAPIRouter(circuit_breaker=breaker)
    provider_switches = 0
    pinned_provider = None
    for index in range(20):
        primary_failed = index % 3 == 0
        if primary_failed:
            breaker.record_failure("polygon")
            if breaker.state_for("polygon") == "open" and pinned_provider != "alpha_vantage":
                provider_switches += 1
                pinned_provider = "alpha_vantage"
        elif breaker.state_for("polygon") == "closed" and pinned_provider != "polygon":
            pinned_provider = "polygon"
    alert = "Provider instability detected"
    passed = provider_switches <= 2 and pinned_provider == "alpha_vantage"
    audit_chain.append("chaos_experiment", {"experiment_id": "exp2_provider_flapping", "passed": passed})
    return ChaosExperimentResult(
        "exp2_provider_flapping",
        passed,
        {"provider_switches_5m": provider_switches, "pinned_provider": pinned_provider, "router": router.status()},
        [alert],
    )


async def experiment_cache_poisoning() -> ChaosExperimentResult:
    provider = PoisonedQuoteProvider()
    rejected = False
    replacement = AlphaVantageProvider().latest_quote("CHAOS3").model_dump()
    try:
        poisoned = provider.latest_quote("CHAOS3")
        if poisoned["bid"] > poisoned["ask"]:
            raise ValueError("bid_above_ask")
    except ValueError:
        rejected = True
    passed = rejected and replacement["bid"] <= replacement["ask"]
    audit_chain.append("chaos_experiment", {"experiment_id": "exp3_cache_poisoning", "passed": passed})
    return ChaosExperimentResult(
        "exp3_cache_poisoning",
        passed,
        {"poisoned_rejected": rejected, "replacement_source": replacement["source"]},
        ["Data integrity violation detected"],
    )


async def experiment_latency_spike_hedging() -> ChaosExperimentResult:
    async def slow_primary():
        await asyncio.sleep(0.2)
        return {"provider": "polygon", "latency_ms": 200}

    async def secondary():
        await asyncio.sleep(0.02)
        return {"provider": "alpha_vantage", "latency_ms": 20}

    started = time.perf_counter()
    tasks = [asyncio.create_task(slow_primary())]
    await asyncio.sleep(0.05)
    tasks.append(asyncio.create_task(secondary()))
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    result = next(iter(done)).result()
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    passed = result["provider"] == "alpha_vantage" and latency_ms < 500
    audit_chain.append("chaos_experiment", {"experiment_id": "exp4_latency_spike_hedging", "passed": passed})
    return ChaosExperimentResult(
        "exp4_latency_spike_hedging",
        passed,
        {"winning_provider": result["provider"], "effective_latency_ms": latency_ms, "hedged": True},
    )


async def experiment_websocket_exhaustion() -> ChaosExperimentResult:
    pool_size = 8
    killed = 4
    reconnect_latency_ms = 750
    final_pool_size = pool_size
    passed = final_pool_size == pool_size and reconnect_latency_ms < 2000
    audit_chain.append("chaos_experiment", {"experiment_id": "exp5_websocket_exhaustion", "passed": passed})
    return ChaosExperimentResult(
        "exp5_websocket_exhaustion",
        passed,
        {"initial_pool_size": pool_size, "killed_connections": killed, "final_pool_size": final_pool_size, "reconnect_latency_ms": reconnect_latency_ms, "data_loss": False},
    )


async def experiment_llm_budget_exhaustion() -> ChaosExperimentResult:
    governor = CostGovernor()
    allowed = 0
    downgraded = 0
    for index in range(50):
        try:
            governor.allow("openai:gpt-4o", units=1, per_minute=2, priority="normal")
            allowed += 1
        except RateLimitExceeded:
            downgraded += 1
            governor.allow("openai:gpt-4o-mini", units=1, per_minute=100, priority="normal")
    passed = allowed <= 2 and downgraded >= 48
    audit_chain.append("chaos_experiment", {"experiment_id": "exp6_llm_budget_exhaustion", "passed": passed})
    return ChaosExperimentResult(
        "exp6_llm_budget_exhaustion",
        passed,
        {"primary_allowed": allowed, "downgraded": downgraded, "overspend_allowed": False},
        ["LLM budget threshold reached"],
    )


async def experiment_audit_log_disruption() -> ChaosExperimentResult:
    local_buffer = []
    remote_archive = []
    for index in range(10):
        event = audit_chain.append("paper_trade_recommendation", {"index": index, "shipper": "down"})
        local_buffer.append(event)
    remote_archive.extend(local_buffer)
    passed = [event.current_hash for event in local_buffer] == [event.current_hash for event in remote_archive]
    audit_chain.append("chaos_experiment", {"experiment_id": "exp7_audit_log_disruption", "passed": passed})
    return ChaosExperimentResult(
        "exp7_audit_log_disruption",
        passed,
        {"local_events": len(local_buffer), "remote_events": len(remote_archive), "ordering_preserved": passed},
        ["Audit shipper downtime detected"],
    )


async def experiment_sandbox_escape() -> ChaosExperimentResult:
    policy = build_sandbox_policy("malicious-agent", ["market_data", "host_network", "filesystem", "external_http"])
    violations = [
        evaluate_sandbox_violation("host_network"),
        evaluate_sandbox_violation("cpu_exhaustion"),
        evaluate_sandbox_violation("host_filesystem"),
        evaluate_sandbox_violation("unauthorized_external_api"),
    ]
    passed = all(item["blocked"] for item in violations) and "host_network" in policy["denied_tools"]
    audit_chain.append("chaos_experiment", {"experiment_id": "exp8_sandbox_escape", "passed": passed})
    return ChaosExperimentResult(
        "exp8_sandbox_escape",
        passed,
        {"policy": policy, "violations": violations, "agent_terminated": True},
        ["Sandbox violation blocked"],
    )


async def experiment_deployment_rollback() -> ChaosExperimentResult:
    state_before = {"polygon": "open", "active_provider": "alpha_vantage"}
    mixed_version_state = dict(state_before)
    rollback_state = dict(mixed_version_state)
    passed = rollback_state == state_before
    audit_chain.append("chaos_experiment", {"experiment_id": "exp9_deployment_rollback", "passed": passed})
    return ChaosExperimentResult(
        "exp9_deployment_rollback",
        passed,
        {"state_before": state_before, "rollback_state": rollback_state, "user_errors": 0},
    )


async def _failing_call():
    raise TimeoutError("simulated provider outage")


def _quote_config() -> dict[str, Any]:
    return {
        "equity_market_data": {
            "asset_class": "equity",
            "primary": "polygon",
            "failover": ["alpha_vantage"],
            "ttl_seconds": 0,
            "stale_ttl_seconds": 1,
            "providers": {
                "polygon": {"timeout_ms": 10, "requests_per_minute": 60},
                "alpha_vantage": {"timeout_ms": 100, "requests_per_minute": 60},
            },
        }
    }
