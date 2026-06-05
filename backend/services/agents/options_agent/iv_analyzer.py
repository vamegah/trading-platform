def analyze_iv(symbol: str) -> dict[str, float | str]:
    return {
        "symbol": symbol.upper(),
        "iv_rank": 0.58,
        "iv_percentile": 0.64,
        "skew": "moderate_put_skew",
    }

