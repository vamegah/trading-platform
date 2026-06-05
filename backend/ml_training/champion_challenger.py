from backend.ml_training.model_registry import ModelCandidate, validate_model_candidate


def evaluate_champion_challenger(
    model_name: str = "signal_orchestrator",
    latest_score: float = 0.62,
    challenger_score: float = 0.64,
) -> dict[str, object]:
    improvement = (challenger_score - latest_score) / max(latest_score, 0.0001)
    promote = improvement >= 0.05
    return {
        "manager": "champion_challenger",
        "model_name": model_name,
        "champion": {"alias": "champion", "score": latest_score},
        "challenger": {"alias": "challenger", "score": challenger_score},
        "mlflow_tracking": {
            "enabled": True,
            "registered_model": model_name,
            "experiment": "trading-platform-signals",
        },
        "model_promotion_pipeline": {
            "promotion_recommended": promote,
            "required_improvement": 0.05,
            "observed_improvement": round(improvement, 4),
        },
    }


class ChampionChallengerManager:
    def __init__(self, min_observations: int = 3, required_improvement: float = 0.05):
        self.min_observations = min_observations
        self.required_improvement = required_improvement

    def evaluate_run(
        self,
        model_name: str,
        champion_scores: list[float],
        challenger_scores: list[float],
        out_of_sample: bool = True,
    ) -> dict[str, object]:
        observations = min(len(champion_scores), len(challenger_scores))
        champion_mean = sum(champion_scores[:observations]) / observations if observations else 0.0
        challenger_mean = sum(challenger_scores[:observations]) / observations if observations else 0.0
        improvement = (challenger_mean - champion_mean) / max(abs(champion_mean), 0.0001)
        checks = {
            "minimum_observations": observations >= self.min_observations,
            "out_of_sample": out_of_sample,
            "required_improvement": improvement >= self.required_improvement,
        }
        gate_reasons = [
            name
            for name, passed in checks.items()
            if not passed
        ]
        promote = all(checks.values())
        return {
            "manager": "champion_challenger",
            "model_name": model_name,
            "observations": observations,
            "out_of_sample": out_of_sample,
            "champion": {"alias": "champion", "mean_score": round(champion_mean, 4), "scores": champion_scores},
            "challenger": {"alias": "challenger", "mean_score": round(challenger_mean, 4), "scores": challenger_scores},
            "model_promotion_pipeline": {
                "promotion_recommended": promote,
                "required_improvement": self.required_improvement,
                "observed_improvement": round(improvement, 4),
                "gate": "passed" if promote else "hold",
                "checks": checks,
                "gate_reasons": gate_reasons,
                "silent_challenger_run": True,
                "human_approval_required": promote,
            },
            "mlflow_tracking": {
                "enabled": True,
                "registered_model": model_name,
                "experiment": "trading-platform-signals",
            },
        }

    def evaluate_candidate_promotion(
        self,
        champion: ModelCandidate,
        challenger: ModelCandidate,
    ) -> dict[str, object]:
        decision = validate_model_candidate(champion, challenger)
        decision["manager"] = "champion_challenger"
        decision["model_promotion_pipeline"] = {
            "promotion_recommended": decision["promotion_allowed"],
            "gate": "passed" if decision["promotion_allowed"] else "hold",
            "gate_reasons": [
                name
                for name, passed in decision.get("checks", {}).items()
                if not passed
            ],
            "silent_challenger_run": True,
            "human_approval_required": decision["promotion_allowed"],
            "required_evidence": [
                "registered artifact",
                "training data snapshot",
                "out-of-sample score",
                "calibration report",
                "drift report",
                "explainability report",
            ],
        }
        return decision
