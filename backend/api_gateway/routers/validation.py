from fastapi import APIRouter

from backend.ml_training.champion_challenger import ChampionChallengerManager
from backend.ml_training.evaluation import monitor_model_health

router = APIRouter()


@router.post("/champion-challenger")
async def champion_challenger(payload: dict) -> dict[str, object]:
    return ChampionChallengerManager(
        min_observations=int(payload.get("min_observations", 3)),
        required_improvement=float(payload.get("required_improvement", 0.05)),
    ).evaluate_run(
        model_name=payload.get("model_name", "signal_orchestrator"),
        champion_scores=[float(value) for value in payload.get("champion_scores", [])],
        challenger_scores=[float(value) for value in payload.get("challenger_scores", [])],
        out_of_sample=bool(payload.get("out_of_sample", True)),
    )


@router.post("/monitor")
async def model_monitor(payload: dict) -> dict[str, object]:
    return monitor_model_health(
        reference=[float(value) for value in payload.get("reference", [])],
        latest=[float(value) for value in payload.get("latest", [])],
        actual=[float(value) for value in payload.get("actual", [])],
        predicted_probability=[float(value) for value in payload.get("predicted_probability", [])],
        signal_ages_minutes=[float(value) for value in payload.get("signal_ages_minutes", [])],
        model_version=payload.get("model_version", "signal-orchestrator-v1"),
        drift_threshold=float(payload.get("drift_threshold", 0.15)),
        calibration_threshold=float(payload.get("calibration_threshold", 0.25)),
    )
