# backend/agents/news_sentiment_agent.py
from .base_agent import BaseAgent
from typing import Dict, Any
import requests
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging

logger = logging.getLogger(__name__)


class NewsSentimentAgent(BaseAgent):
    def __init__(self, api_key: str):
        super().__init__("NewsSentimentAgent")
        self.api_key = api_key
        self.vader = SentimentIntensityAnalyzer()

    async def analyze(self, symbol: str, **kwargs) -> Dict[str, Any]:
        # Fetch news from Alpha Vantage or newsapi.org
        # For simplicity, we'll use Alpha Vantage NEWS_SENTIMENT endpoint
        # But we'll simulate if key missing
        if not self.api_key:
            logger.warning("No API key for news; returning neutral sentiment")
            return {"score": 50, "sentiment": "neutral", "articles": []}

        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={self.api_key}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            feed = data.get("feed", [])
            if not feed:
                return {"score": 50, "sentiment": "neutral", "articles": []}

            sentiments = []
            articles = []
            for item in feed[:10]:  # last 10 articles
                title = item.get("title", "")
                summary = item.get("summary", "")
                text = title + ". " + summary
                vs = self.vader.polarity_scores(text)
                compound = vs["compound"]  # -1 to 1
                sentiments.append(compound)
                articles.append(
                    {"title": title, "sentiment": compound, "url": item.get("url", "")}
                )

            avg_sentiment = np.mean(sentiments)
            # Scale to 0-100 score (50 neutral)
            score = 50 + (avg_sentiment * 50)
            score = max(0, min(100, score))

            sentiment_label = (
                "positive"
                if avg_sentiment > 0.1
                else ("negative" if avg_sentiment < -0.1 else "neutral")
            )
            return {"score": score, "sentiment": sentiment_label, "articles": articles}
        except Exception as e:
            logger.error(f"News sentiment failed: {e}")
            return {"score": 50, "sentiment": "neutral", "articles": []}
