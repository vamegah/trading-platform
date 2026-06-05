def calculate_greeks(symbol: str) -> dict[str, float | str]:
    return {
        "symbol": symbol.upper(),
        "delta": 0.42,
        "gamma": 0.06,
        "theta": -0.03,
        "vega": 0.18,
    }

