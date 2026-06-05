import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ml_training.model_registry import (  # noqa: E402
    ModelCandidate,
    PromotionPolicy,
    validate_model_candidate,
)


def _candidate(payload: dict) -> ModelCandidate:
    return ModelCandidate(
        name=payload["name"],
        version=payload["version"],
        artifact_uri=payload.get("artifact_uri", ""),
        out_of_sample_score=float(payload.get("out_of_sample_score", 0)),
        calibration_error=float(payload.get("calibration_error", 1)),
        drift_score=float(payload.get("drift_score", 1)),
        explainability_report_uri=payload.get("explainability_report_uri", ""),
        training_data_snapshot_id=payload.get("training_data_snapshot_id", ""),
    )


def build_template() -> dict[str, object]:
    return {
        "champion": {
            "name": "signal_orchestrator",
            "version": "1.0.0",
            "artifact_uri": "s3://models/signal/1.0.0/model.json",
            "out_of_sample_score": 0.62,
            "calibration_error": 0.1,
            "drift_score": 0.1,
            "explainability_report_uri": "s3://models/signal/1.0.0/shap.json",
            "training_data_snapshot_id": "features-v1",
        },
        "challenger": {
            "name": "signal_orchestrator",
            "version": "1.1.0",
            "artifact_uri": "",
            "out_of_sample_score": 0,
            "calibration_error": 1,
            "drift_score": 1,
            "explainability_report_uri": "",
            "training_data_snapshot_id": "",
        },
        "human_approval": {
            "approved": False,
            "approver": "",
            "reviewed_at": "",
            "notes": "",
        },
    }


def validate_report(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    decision = validate_model_candidate(
        _candidate(payload["champion"]),
        _candidate(payload["challenger"]),
        PromotionPolicy(),
    )
    approval = payload.get("human_approval", {})
    human_approved = approval.get("approved") is True and bool(approval.get("approver")) and bool(approval.get("reviewed_at"))
    return {
        "valid": decision["promotion_allowed"] and human_approved,
        "model_decision": decision,
        "human_approved": human_approved,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or validate production model validation evidence.")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--validate")
    parser.add_argument("--fail-invalid", action="store_true")
    args = parser.parse_args()

    if args.template:
        print(json.dumps(build_template(), indent=2, sort_keys=True))
        return

    if not args.validate:
        raise SystemExit("--validate is required unless --template is used")
    result = validate_report(Path(args.validate))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_invalid and not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
