import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from scripts.broker_certification import validate as validate_broker
from scripts.evidence_manifest import build_template, load_manifest, validate_manifest
from scripts.legal_compliance_review import validate as validate_legal
from scripts.model_validation_report import validate_report as validate_model
from scripts.provider_certification import validate as validate_provider
from scripts.run_dr_drill import DR_STEPS
from scripts.security_assessment import validate_assessment


def _valid_provider(path: Path) -> bool:
    return validate_provider(path)["valid"] is True


def _valid_broker(path: Path) -> bool:
    return validate_broker(path)["valid"] is True


def _valid_model(path: Path) -> bool:
    return validate_model(path)["valid"] is True


def _valid_persistent_controls(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _all_true(
        payload,
        (
            "production_ready",
            "passed",
            "secret_restored",
            "audit_chain_valid",
            "privacy_record_restored",
            "kms_or_vault_backed",
            "production_backup_restored",
            "secret_store_restore_verified",
            "audit_store_restore_verified",
            "privacy_store_restore_verified",
            "compliance_evidence_restore_verified",
        ),
    )


def _valid_cloud_plan(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _all_true(
        payload,
        (
            "production_ready",
            "passed",
            "terraform_markers_present",
            "kubernetes_manifests_present",
            "cloud_backend_configured",
            "production_apply_verified",
            "dr_region_verified",
            "backup_policy_verified",
            "monitoring_verified",
        ),
    )


def _valid_load(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        payload.get("production_ready") is True
        and payload.get("passed") is True
        and int(payload.get("users", 0)) >= 10_000
        and int(payload.get("instruments", 0)) >= 5_000
        and int(payload.get("duration_minutes", 0)) >= 240
        and payload.get("environment") in {"staging", "production-like", "production"}
        and payload.get("distributed_evidence") is True
        and float(payload.get("p95_latency_ms", 100_000)) <= min(float(payload.get("target_latency_ms", 500)), 500.0)
    )


def _valid_security(path: Path) -> bool:
    return validate_assessment(path)["valid"] is True


def _valid_dr(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    steps = payload.get("steps", {})
    return (
        payload.get("production_ready") is True
        and payload.get("passed") is True
        and all(steps.get(step) == "passed" for step in DR_STEPS)
        and payload.get("rto_minutes", 100_000) <= payload.get("target_rto_minutes", 0)
        and payload.get("rpo_minutes", 100_000) <= payload.get("target_rpo_minutes", 0)
    )


def _valid_legal(path: Path) -> bool:
    return validate_legal(path)["valid"] is True


def _valid_paper(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        payload.get("passed") is True
        and int(payload.get("validation_window_days", 0)) >= 30
        and int(payload.get("total_trades", 0)) >= 20
        and int(payload.get("rejected_or_skipped", 0)) == 0
        and payload.get("reconciled_trades") == payload.get("total_trades")
        and float(payload.get("average_slippage_bps", 100_000)) <= 25
        and int(payload.get("risk_breaches", 1)) == 0
        and int(payload.get("model_drift_alerts", 1)) == 0
        and payload.get("attribution_inputs_complete") is True
    )


def _all_true(payload: dict[str, object], keys: tuple[str, ...]) -> bool:
    return all(payload.get(key) is True for key in keys)


VALIDATORS: dict[str, Callable[[Path], bool]] = {
    "provider_certification": _valid_provider,
    "broker_certification": _valid_broker,
    "model_validation": _valid_model,
    "persistent_controls_restore": _valid_persistent_controls,
    "cloud_infrastructure_plan": _valid_cloud_plan,
    "load_soak_test": _valid_load,
    "security_assessment": _valid_security,
    "dr_outage_drill": _valid_dr,
    "legal_compliance_review": _valid_legal,
    "paper_trading_validation": _valid_paper,
}


def accept_evidence(
    manifest_path: Path,
    evidence_key: str,
    artifact_path: Path,
    owner: str,
    notes: str,
) -> dict[str, object]:
    if evidence_key not in VALIDATORS:
        raise ValueError(f"Unsupported evidence key: {evidence_key}")
    if not artifact_path.exists():
        raise FileNotFoundError(str(artifact_path))
    if not VALIDATORS[evidence_key](artifact_path):
        raise ValueError(f"Evidence artifact failed validation: {artifact_path}")

    manifest = load_manifest(manifest_path) if manifest_path.exists() else build_template()
    manifest.setdefault("evidence", {})[evidence_key] = {
        "accepted": True,
        "artifact_uri": str(artifact_path),
        "owner": owner,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    result = validate_manifest(manifest_path)
    return {
        "manifest": str(manifest_path),
        "evidence_key": evidence_key,
        "accepted": True,
        "manifest_valid": result.valid,
        "remaining_failing": result.failing,
        "remaining_missing": result.missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an evidence artifact and accept it into release_evidence.json.")
    parser.add_argument("--manifest", default="release_evidence.json")
    parser.add_argument("--key", required=True, choices=sorted(VALIDATORS))
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--notes", required=True)
    args = parser.parse_args()

    result = accept_evidence(Path(args.manifest), args.key, Path(args.artifact), args.owner, args.notes)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
