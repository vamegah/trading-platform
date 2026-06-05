async def call_agent(symbol: str) -> dict[str, float]:
    normalized = symbol.upper()
    base = 0.6 if normalized else 0.5
    return {
        "fundamentals": min(base + 0.08, 0.95),
        "technical": min(base + 0.04, 0.95),
        "news_sentiment": max(base - 0.02, 0.05),
        "macro": base,
        "risk": max(base - 0.05, 0.05),
    }

