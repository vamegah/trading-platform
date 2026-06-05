class RegimeHmm:
    def classify(self, features: dict[str, float]) -> str:
        volatility = features.get("volatility", 0.0)
        trend = features.get("trend", 0.0)
        liquidity = features.get("liquidity", 0.5)
        if volatility > 0.3:
            return "high_volatility"
        if liquidity < 0.35 or volatility > 0.25:
            return "risk_off"
        if abs(trend) < 0.02:
            return "sideways"
        return "bull" if trend > 0 else "bear"
