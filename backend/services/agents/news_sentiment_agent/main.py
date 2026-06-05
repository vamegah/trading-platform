from fastapi import FastAPI

from backend.services.agents.news_sentiment_agent.nlp_model import score_sentiment
from backend.shared.observability import instrument_app

app = FastAPI(title="News Sentiment Agent", version="0.1.0")
instrument_app(app, "news_sentiment_agent", {"news": "configured", "social": "optional"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"service": "news_sentiment_agent", "status": "healthy"}


@app.get("/sentiment/{symbol}")
async def sentiment(symbol: str) -> dict[str, str | float]:
    return score_sentiment(symbol)
