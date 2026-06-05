# API Orchestrator Chaos Engineering

This repository includes a safe chaos harness for the API orchestration layer. Local and CI runs are deterministic simulations; staging can use the Kubernetes manifests only after approvals and feature flags are enabled.

## Safety Gates

- `config/chaos_experiments.yaml` disables `chaos_mode` and every experiment by default.
- Local execution requires `--allow-disabled`, which runs simulations only.
- Live brokerage is never used by the chaos harness.
- `make chaos-stop` prints the panic-button actions for local and staging environments.

## Run Locally

```bash
python scripts/chaos_run.py --allow-disabled --experiment all
python scripts/chaos_run.py --allow-disabled --experiment exp1_provider_outage
```

Gateway endpoint:

```bash
POST /orchestrator/chaos/{experiment_id}
```

## Experiments

| ID | Purpose | Local Mode |
| --- | --- | --- |
| `exp1_provider_outage` | Provider outage failover and half-open recovery | Simulated provider failure |
| `exp2_provider_flapping` | Oscillation prevention and provider pinning | Simulated 30% failure loop |
| `exp3_cache_poisoning` | Reject invalid cached quotes | In-memory poisoned quote |
| `exp4_latency_spike_hedging` | Hedged request latency protection | Async delayed primary |
| `exp5_websocket_exhaustion` | Pool recovery expectations | Deterministic pool model |
| `exp6_llm_budget_exhaustion` | Cost governor downgrade path | Token bucket exhaustion |
| `exp7_audit_log_disruption` | Local buffer and ordered replay | In-memory audit buffer |
| `exp8_sandbox_escape` | Deny host/network/file escape attempts | Sandbox policy evaluator |
| `exp9_deployment_rollback` | Failover state consistency across rollback | State consistency model |

## Staging Manifests

`infrastructure/k8s/chaos-experiments.yaml` contains Chaos Mesh resources for provider outage, latency injection, and rollout disruption. Apply only in a dedicated staging chaos namespace after SRE approval.

## Pass Criteria

The suite fails closed if any experiment reports `passed=false`. Reports include alerts fired, latency/failover metrics, and audit entries. Failed staging runs must block release promotion until remediation evidence is attached.
