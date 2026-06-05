# backend/agents/fundamentals_agent.py
from .base_agent import BaseAgent
from typing import Dict, Any
import yfinance as yf
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FundamentalsAgent(BaseAgent):
    def __init__(self):
        super().__init__("FundamentalsAgent")

    async def analyze(self, symbol: str, **kwargs) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Extract key metrics
            pe_ratio = info.get("trailingPE", np.nan)
            pb_ratio = info.get("priceToBook", np.nan)
            debt_to_equity = info.get("debtToEquity", np.nan)
            roe = info.get("returnOnEquity", np.nan)
            current_ratio = info.get("currentRatio", np.nan)
            earnings_growth = info.get("earningsQuarterlyGrowth", np.nan)
            revenue_growth = info.get("revenueGrowth", np.nan)

            # Simple scoring (0-100), higher is better
            score = 50
            red_flags = []

            if not np.isnan(pe_ratio):
                if pe_ratio < 0:
                    red_flags.append("Negative earnings")
                    score -= 20
                elif pe_ratio < 15:
                    score += 10
                elif pe_ratio > 30:
                    score -= 10
                    red_flags.append("High P/E ratio")
            if not np.isnan(debt_to_equity) and debt_to_equity > 200:
                red_flags.append("High debt/equity")
                score -= 15
            if not np.isnan(roe) and roe > 0.15:
                score += 10
            if not np.isnan(current_ratio) and current_ratio < 1:
                red_flags.append("Current ratio < 1")
                score -= 10
            if not np.isnan(earnings_growth) and earnings_growth > 0:
                score += 10
            elif not np.isnan(earnings_growth):
                score -= 5
                red_flags.append("Declining earnings")

            # Normalize score 0-100
            score = max(0, min(100, score))

            return {
                "score": score,
                "red_flags": red_flags,
                "metrics": {
                    "pe_ratio": pe_ratio,
                    "pb_ratio": pb_ratio,
                    "debt_to_equity": debt_to_equity,
                    "roe": roe,
                    "current_ratio": current_ratio,
                    "earnings_growth": earnings_growth,
                    "revenue_growth": revenue_growth,
                },
            }
        except Exception as e:
            logger.error(f"Fundamentals analysis failed for {symbol}: {e}")
            return {"score": 50, "red_flags": ["Data unavailable"], "metrics": {}}
