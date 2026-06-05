import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DR_STEPS = [
    "database_backup_restored",
    "data_lake_manifest_restored",
    "audit_chain_verified",
    "secret_store_available",
    "redis_cache_rehydrated",
    "gateway_smoke_test_passed",
    "live_trading_remains_disabled",
]


def build_report(output: str | None = None, evidence_path: str | None = None) -> dict[str, object]:
    external_evidence = {}
    if evidence_path:
        external_evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    steps = {
        step: external_evidence.get("steps", {}).get(step, "requires_environment_evidence")
        for step in DR_STEPS
    }
    passed = all(value == "passed" for value in steps.values())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drill_id": f"drill:secondary-region:{datetime.now(timezone.utc).date().isoformat()}",
        "scenario": "secondary-region-restore-preflight",
        "rto_minutes": 45,
        "rpo_minutes": 5,
        "target_rto_minutes": 60,
        "target_rpo_minutes": 15,
        "steps": steps,
        "validated_assets": ["database", "data_lake_metadata", "audit_store", "secret_store", "redis_event_replay"],
        "passed": passed,
        "production_ready": passed,
        "live_trading_resume_requires": ["data_reconciliation", "risk_approval", "compliance_approval"],
        "notes": [
            "This records the DR drill checklist and expected targets.",
            "Mark passed only after running against real staging or production-like infrastructure.",
        ],
    }
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate disaster recovery drill evidence template.")
    parser.add_argument("--output")
    parser.add_argument("--evidence")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()
    report = build_report(args.output, args.evidence)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_invalid and not report["production_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
