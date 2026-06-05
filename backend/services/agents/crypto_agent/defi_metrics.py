def get_defi_metrics(asset: str) -> dict[str, str | float]:
    return {
        "asset": asset.upper(),
        "total_value_locked_change": 0.08,
        "protocol_revenue_trend": "stable",
    }

