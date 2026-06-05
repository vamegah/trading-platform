from backend.ml_training.champion_challenger import ChampionChallengerManager
from backend.ml_training.model_registry import ModelCandidate, validate_model_candidate


def _candidate(
    version: str,
    score: float,
    calibration: float = 0.08,
    drift: float = 0.1,
    artifact: str = "s3://models/signal/model.json",
) -> ModelCandidate:
    return ModelCandidate(
        name="signal_orchestrator",
        version=version,
        artifact_uri=artifact,
        out_of_sample_score=score,
        calibration_error=calibration,
        drift_score=drift,
        explainability_report_uri="s3://models/signal/shap.json",
        training_data_snapshot_id="features-v1",
    )


def test_model_candidate_requires_artifact_calibration_drift_and_explainability() -> None:
    champion = _candidate("1.0.0", 0.6)
    challenger = _candidate("1.1.0", 0.66)

    decision = validate_model_candidate(champion, challenger)

    assert decision["promotion_allowed"] is True
    assert decision["checks"]["artifact_present"] is True
    assert decision["checks"]["calibration"] is True
    assert decision["checks"]["drift"] is True


def test_model_candidate_blocks_missing_artifact_or_bad_calibration() -> None:
    champion = _candidate("1.0.0", 0.6)
    challenger = _candidate("1.1.0", 0.66, calibration=0.3, artifact="")

    decision = validate_model_candidate(champion, challenger)

    assert decision["promotion_allowed"] is False
    assert decision["checks"]["artifact_present"] is False
    assert decision["checks"]["calibration"] is False


def test_champion_challenger_manager_exposes_required_evidence_gate() -> None:
    decision = ChampionChallengerManager().evaluate_candidate_promotion(
        _candidate("1.0.0", 0.6),
        _candidate("1.1.0", 0.66),
    )

    assert decision["model_promotion_pipeline"]["gate"] == "passed"
    assert "explainability report" in decision["model_promotion_pipeline"]["required_evidence"]
