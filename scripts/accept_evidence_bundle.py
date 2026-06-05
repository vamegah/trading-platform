import argparse
import json
from pathlib import Path

from scripts.accept_evidence import VALIDATORS, accept_evidence
from scripts.evidence_manifest import load_manifest, validate_manifest


ARTIFACT_FILENAMES = {
    "provider_certification": "provider_certification.json",
    "broker_certification": "broker_certification.json",
    "model_validation": "model_validation.json",
    "persistent_controls_restore": "persistent_controls_restore.json",
    "cloud_infrastructure_plan": "cloud_infrastructure_plan.json",
    "load_soak_test": "load_soak_test.json",
    "security_assessment": "security_assessment.json",
    "dr_outage_drill": "dr_outage_drill.json",
    "legal_compliance_review": "legal_compliance_review.json",
    "paper_trading_validation": "paper_trading_validation.json",
}

DEFAULT_OWNERS = {
    "provider_certification": "data-platform",
    "broker_certification": "execution",
    "model_validation": "ml-review-board",
    "persistent_controls_restore": "platform-security",
    "cloud_infrastructure_plan": "sre",
    "load_soak_test": "sre",
    "security_assessment": "security",
    "dr_outage_drill": "sre",
    "legal_compliance_review": "compliance",
    "paper_trading_validation": "trading-ops",
}


def validate_bundle(evidence_dir: Path) -> dict[str, object]:
    missing: list[str] = []
    failing: list[str] = []
    valid: list[str] = []

    for key, validator in VALIDATORS.items():
        artifact_path = evidence_dir / ARTIFACT_FILENAMES[key]
        if not artifact_path.exists():
            missing.append(key)
            continue
        if not validator(artifact_path):
            failing.append(key)
            continue
        valid.append(key)

    return {
        "valid": not missing and not failing,
        "missing": missing,
        "failing": failing,
        "accepted": valid,
    }


def accept_evidence_bundle(
    manifest_path: Path,
    evidence_dir: Path,
    release_candidate: str,
    live_requested: bool = False,
    notes_prefix: str = "M10 reviewed evidence",
) -> dict[str, object]:
    preflight = validate_bundle(evidence_dir)
    if not preflight["valid"]:
        return {
            "manifest": str(manifest_path),
            "evidence_dir": str(evidence_dir),
            "release_candidate": release_candidate,
            "live_requested": live_requested,
            "manifest_updated": False,
            **preflight,
        }

    accepted_keys: list[str] = []
    for key in VALIDATORS:
        result = accept_evidence(
            manifest_path=manifest_path,
            evidence_key=key,
            artifact_path=evidence_dir / ARTIFACT_FILENAMES[key],
            owner=DEFAULT_OWNERS[key],
            notes=f"{notes_prefix}: {key}",
        )
        if result["accepted"] is True:
            accepted_keys.append(key)

    manifest = load_manifest(manifest_path)
    manifest.setdefault("release", {})["candidate"] = release_candidate
    manifest["release"]["environment"] = "production"
    manifest["release"]["live_trading_requested"] = live_requested
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    result = validate_manifest(manifest_path)
    return {
        "manifest": str(manifest_path),
        "evidence_dir": str(evidence_dir),
        "release_candidate": release_candidate,
        "live_requested": live_requested,
        "manifest_updated": True,
        "valid": result.valid,
        "missing": result.missing,
        "failing": result.failing,
        "accepted": accepted_keys,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Atomically accept a complete M10 evidence artifact bundle.")
    parser.add_argument("--manifest", default="release_evidence.json")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--release-candidate", required=True)
    parser.add_argument("--live-requested", action="store_true")
    parser.add_argument("--notes-prefix", default="M10 reviewed evidence")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    result = accept_evidence_bundle(
        manifest_path=Path(args.manifest),
        evidence_dir=Path(args.evidence_dir),
        release_candidate=args.release_candidate,
        live_requested=args.live_requested,
        notes_prefix=args.notes_prefix,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_invalid and not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
