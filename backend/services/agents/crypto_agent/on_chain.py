def analyze_on_chain(asset: str) -> dict[str, str | float]:
    return {
        "asset": asset.upper(),
        "active_addresses_trend": "rising",
        "network_value_signal": 0.62,
    }

