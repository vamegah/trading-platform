def evaluate_predictions(actual: list[float], predicted: list[float]) -> dict[str, float]:
    pairs = list(zip(actual, predicted, strict=False))
    if not pairs:
        return {"mae": 0.0}
    error = sum(abs(left - right) for left, right in pairs) / len(pairs)
    return {"mae": round(error, 4)}


def calibration_error(actual: list[float], predicted_probability: list[float]) -> float:
    pairs = list(zip(actual, predicted_probability, strict=False))
    if not pairs:
        return 0.0
    return round(sum(abs((1.0 if outcome > 0 else 0.0) - probability) for outcome, probability in pairs) / len(pairs), 4)


def drift_score(reference: list[float], latest: list[float]) -> float:
    if not reference or not latest:
        return 0.0
    reference_mean = sum(reference) / len(reference)
    latest_mean = sum(latest) / len(latest)
    reference_range = max(reference) - min(reference) or 1.0
    return round(abs(latest_mean - reference_mean) / reference_range, 4)


def decay_monitor(signal_ages_minutes: list[float], half_life_minutes: float = 60.0) -> dict[str, float | bool]:
    if not signal_ages_minutes:
        return {
            "average_age_minutes": 0.0,
            "stale_fraction": 0.0,
            "decay_alert": False,
            "half_life_minutes": half_life_minutes,
            "stale_threshold_minutes": half_life_minutes * 2,
            "max_age_minutes": 0.0,
            "action": "healthy",
        }
    stale = [age for age in signal_ages_minutes if age > half_life_minutes * 2]
    average_age = sum(signal_ages_minutes) / len(signal_ages_minutes)
    stale_fraction = len(stale) / len(signal_ages_minutes)
    return {
        "average_age_minutes": round(average_age, 2),
        "stale_fraction": round(stale_fraction, 4),
        "decay_alert": stale_fraction >= 0.25,
        "half_life_minutes": half_life_minutes,
        "stale_threshold_minutes": half_life_minutes * 2,
        "max_age_minutes": round(max(signal_ages_minutes), 2),
        "action": "refresh_or_cancel_stale_signals" if stale_fraction >= 0.25 else "healthy",
    }


def monitor_model_health(
    reference: list[float],
    latest: list[float],
    actual: list[float],
    predicted_probability: list[float],
    signal_ages_minutes: list[float],
    model_version: str = "signal-orchestrator-v1",
    drift_threshold: float = 0.15,
    calibration_threshold: float = 0.25,
) -> dict[str, object]:
    drift = drift_score(reference, latest)
    calibration = calibration_error(actual, predicted_probability)
    decay = decay_monitor(signal_ages_minutes)
    alerts = []
    if drift >= drift_threshold:
        alerts.append(
            {
                "type": "model_drift",
                "severity": "warning" if drift < drift_threshold * 1.5 else "critical",
                "value": drift,
                "threshold": drift_threshold,
                "action": "run_challenger_validation",
            }
        )
    if calibration >= calibration_threshold:
        alerts.append(
            {
                "type": "calibration_error",
                "severity": "warning" if calibration < calibration_threshold * 1.5 else "critical",
                "value": calibration,
                "threshold": calibration_threshold,
                "action": "recalibrate_probabilities",
            }
        )
    if bool(decay["decay_alert"]):
        alerts.append(
            {
                "type": "signal_decay",
                "severity": "warning",
                "value": decay["stale_fraction"],
                "threshold": 0.25,
                "action": decay["action"],
            }
        )
    severity_rank = {"normal": 0, "warning": 1, "critical": 2}
    severity = "normal"
    for alert in alerts:
        if severity_rank[str(alert["severity"])] > severity_rank[severity]:
            severity = str(alert["severity"])
    return {
        "drift_score": drift,
        "calibration_error": calibration,
        "decay": decay,
        "model_version": model_version,
        "alert": bool(alerts),
        "severity": severity,
        "monitoring_alerts": alerts,
        "thresholds": {
            "drift": drift_threshold,
            "calibration": calibration_threshold,
            "stale_fraction": 0.25,
        },
    }
