def analyze_alt_data(symbol: str) -> dict[str, object]:
    seed = sum(ord(char) for char in symbol.upper())
    score = round(0.45 + (seed % 25) / 100, 2)
    return {
        "symbol": symbol.upper(),
        "agent": "alt_data",
        "score": score,
        "signals": {
            "job_postings_trend": "stable",
            "web_interest": score,
            "supply_chain_pressure": "normal",
        },
    }
