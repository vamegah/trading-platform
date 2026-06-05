from statistics import pstdev
from typing import Any

from backend.services.agents.base_agent import BaseAgent


class TraderRiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("TraderRiskAgent")

    async def analyze(self, symbol: str, asset_type: str | None = None, **kwargs) -> dict[str, Any]:
        fundamentals = kwargs.get("fundamentals", {})
        sentiment = kwargs.get("sentiment", {})
        price = float(kwargs.get("current_price", 100.0))
        return await self.synthesize(symbol, fundamentals, sentiment, price)

    async def synthesize(
        self,
        symbol: str,
        fundamentals: dict[str, Any],
        sentiment: dict[str, Any],
        current_price: float,
        volatility: float = 0.02,
    ) -> dict[str, Any]:
        f_score = float(fundamentals.get("score", 50))
        s_score = float(sentiment.get("score", 50))
        combined_score = 0.6 * f_score + 0.4 * s_score
        signal = "BUY" if combined_score > 70 else "SELL" if combined_score < 30 else "HOLD"
        confidence = max(30.0, min(100.0, 100 - pstdev([f_score, s_score]) * 2))
        stop_loss = current_price * (1 - 2 * volatility)
        take_profit = current_price * (1 + 3 * volatility)
        win_probability = max(0.1, min(0.9, 0.5 + (combined_score - 50) / 250))
        return {
            "symbol": symbol.upper(),
            "signal": signal,
            "confidence": round(confidence, 2),
            "combined_score": round(combined_score, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "position_size": self.kelly_position_size(win_probability, 1.5, 100000.0),
            "probability_distribution": {
                "win_probability": round(win_probability, 2),
                "loss_probability": round(1 - win_probability, 2),
            },
        }

    @staticmethod
    def kelly_position_size(
        win_prob: float,
        win_loss_ratio: float,
        capital: float,
        max_risk: float = 0.02,
    ) -> float:
        kelly_fraction = win_prob - (1 - win_prob) / max(win_loss_ratio, 0.01)
        bet_fraction = min(max(kelly_fraction, 0.0) * 0.5, max_risk)
        return round(bet_fraction * capital, 2)
