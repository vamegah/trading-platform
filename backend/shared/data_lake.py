from datetime import datetime, timezone


def record_data_lake_edge(service: str, operation: str, entity: str) -> dict[str, str]:
    return {
        "store": "data_lake_postgresql",
        "service": service,
        "operation": operation,
        "entity": entity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def agent_db_edges(symbol: str) -> dict[str, dict[str, str]]:
    return {
        "fundamentals_agent": record_data_lake_edge("fundamentals_agent", "read", f"filings:{symbol}"),
        "technical_agent": record_data_lake_edge("technical_agent", "read", f"ohlcv:{symbol}"),
        "news_sentiment_agent": record_data_lake_edge("news_sentiment_agent", "read", f"news:{symbol}"),
        "macro_agent": record_data_lake_edge("macro_agent", "read", "economic_indicators"),
        "bull_bear_debate_agent": record_data_lake_edge("bull_bear_debate_agent", "write", f"debate:{symbol}"),
        "trader_risk_agent": record_data_lake_edge("trader_risk_agent", "read_write", f"risk:{symbol}"),
    }
