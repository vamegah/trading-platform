def score_sentiment(symbol: str) -> dict[str, object]:
    news_score = 0.61
    social_score = 0.56
    insider_score = 0.52
    event_risk_score = 0.35 if symbol.upper() == "NVDA" else 0.22
    combined = round(news_score * 0.45 + social_score * 0.25 + insider_score * 0.15 + (1 - event_risk_score) * 0.15, 4)
    return {
        "symbol": symbol.upper(),
        "agent": "news_sentiment",
        "sentiment": "neutral-positive",
        "score": combined,
        "scores": {
            "news": news_score,
            "social": social_score,
            "insider_transactions": insider_score,
            "event_risk": event_risk_score,
        },
        "event_impacts": [
            {"event_type": "earnings", "days_until_event": 18, "impact_score": event_risk_score}
        ],
    }
