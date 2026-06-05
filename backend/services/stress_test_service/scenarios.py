PREDEFINED_SCENARIOS: dict[str, dict[str, object]] = {
    "2008_financial_crisis": {
        "label": "2008 Financial Crisis",
        "period": "2008-09 to 2009-03",
        "severity": "severe",
        "description": "Equity, credit, and volatility shock calibrated to the global financial crisis.",
        "shocks": {"market": -0.38, "credit": -0.22, "volatility": 0.65},
    },
    "covid_crash_2020": {
        "label": "2020 COVID Crash",
        "period": "2020-02 to 2020-03",
        "severity": "severe",
        "description": "Fast equity drawdown with liquidity stress and volatility expansion.",
        "shocks": {"market": -0.28, "liquidity": -0.18, "volatility": 0.8},
    },
    "rate_hike_2022": {
        "label": "2022 Rate-Hike Selloff",
        "period": "2022",
        "severity": "moderate",
        "description": "Higher-rate shock penalizing duration and growth exposure.",
        "shocks": {"market": -0.18, "duration": -0.25, "growth": -0.3},
    },
    "oil_spike": {
        "label": "Oil Spike",
        "period": "custom historical analogue",
        "severity": "moderate",
        "description": "Inflationary oil shock with broad-market pressure.",
        "shocks": {"market": -0.08, "oil": 0.35, "inflation": 0.18},
    },
}


def get_scenario(name: str) -> dict[str, object]:
    if name not in PREDEFINED_SCENARIOS:
        raise ValueError(f"Unknown stress scenario: {name}")
    return PREDEFINED_SCENARIOS[name]


def list_scenarios() -> list[dict[str, object]]:
    return [{"name": name, **scenario} for name, scenario in PREDEFINED_SCENARIOS.items()]
