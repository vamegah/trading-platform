class DataClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    async def market_snapshot(self, symbol: str) -> dict[str, str | float]:
        return {"symbol": symbol.upper(), "last_price": 100.0, "source": "sdk_stub"}

    async def feature_vector(self, symbol: str, feature_set: str) -> dict[str, object]:
        return {"symbol": symbol.upper(), "feature_set": feature_set, "features": {}}

