from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    version: str
    artifact_uri: str
    out_of_sample_score: float
    calibration_error: float
    drift_score: float
    explainability_report_uri: str
    training_data_snapshot_id: str


@dataclass(frozen=True)
class PromotionPolicy:
    required_improvement: float = 0.05
    max_calibration_error: float = 0.12
    max_drift_score: float = 0.2


def validate_model_candidate(
    champion: ModelCandidate,
    challenger: ModelCandidate,
    policy: PromotionPolicy | None = None,
) -> dict[str, object]:
    active_policy = policy or PromotionPolicy()
    improvement = (challenger.out_of_sample_score - champion.out_of_sample_score) / max(abs(champion.out_of_sample_score), 0.0001)
    checks = {
        "artifact_present": bool(challenger.artifact_uri),
        "snapshot_present": bool(challenger.training_data_snapshot_id),
        "explainability_present": bool(challenger.explainability_report_uri),
        "improvement": improvement >= active_policy.required_improvement,
        "calibration": challenger.calibration_error <= active_policy.max_calibration_error,
        "drift": challenger.drift_score <= active_policy.max_drift_score,
    }
    missing_checks = [name for name, passed in checks.items() if not passed]
    return {
        "model_name": challenger.name,
        "champion_version": champion.version,
        "challenger_version": challenger.version,
        "observed_improvement": round(improvement, 4),
        "checks": checks,
        "missing_checks": missing_checks,
        "promotion_allowed": all(checks.values()),
        "human_approval_required": all(checks.values()),
        "policy": {
            "required_improvement": active_policy.required_improvement,
            "max_calibration_error": active_policy.max_calibration_error,
            "max_drift_score": active_policy.max_drift_score,
        },
        "registry": {
            "tracking_system": "mlflow-compatible",
            "artifact_uri": challenger.artifact_uri,
            "training_data_snapshot_id": challenger.training_data_snapshot_id,
            "explainability_report_uri": challenger.explainability_report_uri,
        },
    }
