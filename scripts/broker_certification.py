import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_BROKERS = ["alpaca", "ibkr", "tradestation", "deribit", "binance_futures"]
REQUIRED_BROKER_CHECKS = (
    "sandbox_submit_passed",
    "cancel_replace_passed",
    "positions_reconciled",
    "balances_reconciled",
    "fills_reconciled",
    "outage_behavior_tested",
    "live_credentials_approved",
)


def build_template(output: str | None = None) -> dict[str, object]:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brokers": {
            broker: {
                "sandbox_submit_passed": False,
                "cancel_replace_passed": False,
                "positions_reconciled": False,
                "balances_reconciled": False,
                "fills_reconciled": False,
                "outage_behavior_tested": False,
                "live_credentials_approved": False,
                "artifact_uri": "",
            }
            for broker in REQUIRED_BROKERS
        },
        "accepted": False,
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def validate(path: Path) -> dict[str, object]:
    report = json.loads(path.read_text(encoding="utf-8"))
    brokers = report.get("brokers", {})
    missing = [broker for broker in REQUIRED_BROKERS if broker not in brokers]
    failing = []
    for broker in REQUIRED_BROKERS:
        if broker not in brokers:
            continue
        checks = brokers[broker]
        for key in REQUIRED_BROKER_CHECKS:
            if checks.get(key) is not True:
                failing.append(f"{broker}:{key}")
        if not checks.get("artifact_uri"):
            failing.append(f"{broker}:artifact_uri")
    accepted = not missing and not failing and report.get("accepted") is True
    return {"valid": accepted, "missing": missing, "failing": failing, "accepted": report.get("accepted") is True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or validate broker certification evidence.")
    parser.add_argument("--output")
    parser.add_argument("--validate")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()
    result = validate(Path(args.validate)) if args.validate else build_template(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_invalid and result.get("valid") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
