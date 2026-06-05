def adapt_experience(persona: dict) -> dict[str, object]:
    sensitivity = float(persona.get("nudge_sensitivity", 0.5))
    return {
        "nudge_strength": "gentle" if sensitivity < 0.6 else "direct",
        "detail_level": persona.get("preferred_detail_level", "medium"),
        "show_risk_first": sensitivity >= 0.5,
    }

