import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.shared.external_api.chaos import run_experiment  # noqa: E402


def load_flags(path: str = "config/chaos_experiments.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run safe chaos simulations for the API orchestration layer.")
    parser.add_argument("--experiment", default="all", help="Experiment id, or all")
    parser.add_argument("--allow-disabled", action="store_true", help="Run even if config flags are disabled. Intended for CI simulations only.")
    parser.add_argument("--output", default="", help="Optional JSON report path")
    args = parser.parse_args()

    flags = load_flags()
    if not args.allow_disabled and not flags.get("chaos_mode", {}).get("enabled", False):
        raise SystemExit("chaos_mode is disabled. Use --allow-disabled only for safe CI simulations.")

    experiment_ids = list(flags.get("experiments", {}).keys()) if args.experiment == "all" else [args.experiment]
    results = []
    for experiment_id in experiment_ids:
        experiment = flags.get("experiments", {}).get(experiment_id, {})
        if not args.allow_disabled and not experiment.get("enabled", False):
            raise SystemExit(f"{experiment_id} is disabled")
        result = await run_experiment(experiment_id)
        results.append(
            {
                "experiment_id": result.experiment_id,
                "passed": result.passed,
                "metrics": result.metrics,
                "alerts": result.alerts,
                "notes": result.notes,
            }
        )

    report = {
        "suite": "api_orchestrator_chaos",
        "passed": all(item["passed"] for item in results),
        "results": results,
    }
    text = json.dumps(report, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
