import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_trades(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("trades", payload if isinstance(payload, list) else [])


def build_report(trades: list[dict[str, Any]], days: int, output: str | None = None) -> dict[str, Any]:
    total_trades = len(trades)
    rejected_or_skipped = sum(1 for trade in trades if trade.get("status") in {"rejected", "skipped"})
    reconciled = sum(1 for trade in trades if trade.get("reconciled") is True)
    slippage_values = [abs(float(trade.get("slippage_bps", 0))) for trade in trades]
    risk_breaches = sum(1 for trade in trades if trade.get("risk_breach") is True)
    drift_alerts = sum(1 for trade in trades if trade.get("model_drift_alert") is True)
    attribution_ready = sum(1 for trade in trades if _has_attribution_inputs(trade))
    attribution_inputs_complete = total_trades > 0 and attribution_ready == total_trades
    average_slippage = round(sum(slippage_values) / len(slippage_values), 4) if slippage_values else 0.0
    passed = (
        days >= 30
        and total_trades >= 20
        and rejected_or_skipped == 0
        and reconciled == total_trades
        and attribution_inputs_complete
        and risk_breaches == 0
        and drift_alerts == 0
        and average_slippage <= 25
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_window_days": days,
        "total_trades": total_trades,
        "rejected_or_skipped": rejected_or_skipped,
        "reconciled_trades": reconciled,
        "average_slippage_bps": average_slippage,
        "risk_breaches": risk_breaches,
        "model_drift_alerts": drift_alerts,
        "attribution_ready_trades": attribution_ready,
        "attribution_inputs_complete": attribution_inputs_complete,
        "required_minimum_days": 30,
        "required_minimum_trades": 20,
        "passed": passed,
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _has_attribution_inputs(trade: dict[str, Any]) -> bool:
    attribution = trade.get("attribution")
    if not isinstance(attribution, dict):
        return False
    source_breakdown = attribution.get("source_breakdown")
    factor_breakdown = attribution.get("factor_breakdown")
    model_version = trade.get("model_version_id") or attribution.get("model_version_id")
    data_snapshot = trade.get("data_snapshot_id") or attribution.get("data_snapshot_id")
    return bool(source_breakdown or factor_breakdown) and bool(model_version) and bool(data_snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate extended paper trading evidence.")
    parser.add_argument("--trades")
    parser.add_argument("--days", type=int, default=0)
    parser.add_argument("--output")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    report = build_report(_load_trades(args.trades), args.days, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_invalid and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
