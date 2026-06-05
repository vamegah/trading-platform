class OptionsPricingNN:
    def predict_price(self, features: dict[str, float]) -> float:
        intrinsic = max(features.get("underlying_price", 0.0) - features.get("strike", 0.0), 0.0)
        volatility_value = features.get("implied_volatility", 0.0) * 10
        return round(intrinsic + volatility_value, 4)

