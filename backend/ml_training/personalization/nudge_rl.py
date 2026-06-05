def choose_nudge_action(state: dict) -> dict[str, str | float]:
    risk = float(state.get("risk", 0.5))
    return {
        "action": "show_risk_context" if risk >= 0.5 else "show_confidence_context",
        "policy_confidence": 0.55,
    }

