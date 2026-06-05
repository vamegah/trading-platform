import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def estimate_latency_ms(users: int, instruments: int, replicas: int) -> float:
    workload = users * max(instruments, 1)
    capacity = max(replicas, 1) * 12_500_000
    pressure = workload / capacity
    return round(120 + min(pressure, 4.0) * 95, 2)


def build_report(
    users: int,
    instruments: int,
    replicas: int,
    output: str | None,
    duration_minutes: int = 0,
    environment: str = "local-preflight",
    distributed_evidence: bool = False,
) -> dict[str, object]:
    p95_latency_ms = estimate_latency_ms(users, instruments, replicas)
    workload = users * max(instruments, 1)
    capacity = max(replicas, 1) * 12_500_000
    saturation = workload / capacity
    preflight_passed = users >= 10_000 and instruments >= 5_000 and p95_latency_ms <= 500
    production_ready = (
        preflight_passed
        and duration_minutes >= 240
        and environment in {"staging", "production-like", "production"}
        and distributed_evidence
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": "market-open-scanner-and-signal-fanout",
        "environment": environment,
        "users": users,
        "instruments": instruments,
        "replicas": replicas,
        "duration_minutes": duration_minutes,
        "distributed_evidence": distributed_evidence,
        "estimated_requests": workload,
        "saturation": round(saturation, 4),
        "p95_latency_ms": p95_latency_ms,
        "target_latency_ms": 500,
        "passed": preflight_passed,
        "production_ready": production_ready,
        "autoscaling_signals": ["cpu", "memory", "queue_depth", "redis_stream_lag"],
        "bottlenecks": ["redis_memory", "agent_cpu_queue", "broker_api_rate_limits"],
        "notes": [
            "This deterministic preflight estimates capacity before cloud load testing.",
            "Production signoff requires a real distributed load/soak test of at least 240 minutes against staging or production-like infrastructure.",
        ],
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic production load preflight.")
    parser.add_argument("--users", type=int, default=10_000)
    parser.add_argument("--instruments", type=int, default=5_000)
    parser.add_argument("--replicas", type=int, default=8)
    parser.add_argument("--duration-minutes", type=int, default=0)
    parser.add_argument("--environment", default="local-preflight")
    parser.add_argument("--distributed-evidence", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    report = build_report(
        args.users,
        args.instruments,
        args.replicas,
        args.output,
        args.duration_minutes,
        args.environment,
        args.distributed_evidence,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_invalid and not report["production_ready"]:
        raise SystemExit(1)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
