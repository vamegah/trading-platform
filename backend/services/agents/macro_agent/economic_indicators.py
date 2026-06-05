import requests

from backend.shared.config import settings


def fetch_macro_events(country: str = "US") -> list[dict[str, object]]:
    if not settings.macro_calendar_api_key:
        return [
            {
                "country": country,
                "event": "macro_calendar_sample",
                "importance": "medium",
                "source": "sample",
            }
        ]
    response = requests.get(
        "https://api.tradingeconomics.com/calendar",
        params={"c": settings.macro_calendar_api_key, "country": country},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else payload.get("data", [])


def fetch_world_bank_indicator(country: str, indicator: str) -> dict[str, object]:
    response = requests.get(
        f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}",
        params={"format": "json", "per_page": 5},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    return {"country": country, "indicator": indicator, "observations": rows, "source": "world_bank"}


def macro_regime() -> dict[str, str | float]:
    rates_score = 0.54
    yield_curve_score = 0.42
    inflation_score = 0.48
    gdp_score = 0.58
    commodity_score = 0.51
    central_bank_score = 0.46
    composite = round(
        rates_score * 0.2
        + yield_curve_score * 0.2
        + inflation_score * 0.2
        + gdp_score * 0.15
        + commodity_score * 0.1
        + central_bank_score * 0.15,
        4,
    )
    environment = "risk_on" if composite >= 0.6 else "risk_off" if composite <= 0.4 else "neutral"
    return {
        "agent": "macro",
        "regime": environment,
        "inflation_pressure": 0.54,
        "liquidity_score": 0.62,
        "composite_score": composite,
        "indicators": {
            "interest_rates": rates_score,
            "yield_curve": yield_curve_score,
            "inflation": inflation_score,
            "gdp": gdp_score,
            "commodities": commodity_score,
            "central_bank": central_bank_score,
        },
        "rationale": "Macro score blends rates, curve shape, inflation, growth, commodities, and central-bank tone.",
        "providers": {
            "macro_calendar": bool(settings.macro_calendar_api_key),
            "world_bank": True,
        },
    }
