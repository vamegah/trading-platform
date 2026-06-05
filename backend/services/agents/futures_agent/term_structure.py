def analyze_term_structure(root_symbol: str) -> dict[str, str | float]:
    return {
        "root_symbol": root_symbol.upper(),
        "shape": "contango",
        "front_spread": 0.014,
        "roll_risk": "medium",
    }

