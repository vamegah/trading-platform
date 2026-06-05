def analyze_exchange_flow(asset: str) -> dict[str, str | float]:
    return {
        "asset": asset.upper(),
        "net_exchange_flow": -1250000.0,
        "interpretation": "net_outflow_supportive",
    }

