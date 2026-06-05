from collections import defaultdict, deque
from typing import Any

from backend.services.agents.base_agent import BaseAgent
from backend.services.agents.technical_agent.analyzer import analyze_technicals


class TechnicalAgent(BaseAgent):
    def __init__(self, max_points: int = 512):
        super().__init__("TechnicalAgent")
        self.price_cache: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=max_points))

    async def analyze(self, symbol: str, asset_type: str | None = None, **kwargs) -> dict[str, Any]:
        candles = kwargs.get("candles")
        return analyze_technicals(symbol, candles, asset_type or "equity")

    def consume_tick(self, symbol: str, price: float) -> dict[str, object]:
        cache = self.price_cache[symbol.upper()]
        cache.append(float(price))
        return {"symbol": symbol.upper(), "points": len(cache), "last_price": float(price)}

    def recent_prices(self, symbol: str) -> list[float]:
        return list(self.price_cache[symbol.upper()])
