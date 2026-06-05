FACTOR_MAP = {
    "AAPL": {"growth": 0.72, "quality": 0.68, "momentum": 0.54},
    "MSFT": {"quality": 0.78, "growth": 0.64, "low_volatility": 0.42},
    "NVDA": {"growth": 0.86, "momentum": 0.74, "size": 0.62},
}


def tag_factor_exposures(symbol: str, portfolio_context: dict | None = None) -> dict[str, object]:
    exposures = FACTOR_MAP.get(
        symbol.upper(),
        {"value": 0.45, "growth": 0.5, "momentum": 0.5, "quality": 0.5, "low_volatility": 0.45, "size": 0.5},
    )
    for factor in ("value", "growth", "momentum", "quality", "low_volatility", "size"):
        exposures.setdefault(factor, 0.0)
    concentration_warning = max(exposures.values()) >= 0.8
    portfolio_factor_load = (portfolio_context or {}).get("factor_load", {})
    factor_warnings = [
        factor
        for factor, value in exposures.items()
        if value + float(portfolio_factor_load.get(factor, 0.0)) >= 1.2
    ]
    return {
        "agent": "factor_tagging",
        "symbol": symbol.upper(),
        "factor_exposures": exposures,
        "portfolio_context": portfolio_context or {},
        "concentration_warning": concentration_warning,
        "factor_warnings": factor_warnings,
    }
