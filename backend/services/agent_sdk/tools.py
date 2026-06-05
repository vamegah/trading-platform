from backend.data_pipeline.ingestion.providers import get_market_data_manager


class AgentToolbox:
    def __init__(self, allowed_tools: set[str] | None = None):
        self.allowed_tools = allowed_tools or {"market_data", "feature_store", "model_inference"}

    def require(self, tool_name: str) -> None:
        if tool_name not in self.allowed_tools:
            raise PermissionError(f"Tool is not allowed for this agent: {tool_name}")

    async def get_market_snapshot(self, symbol: str) -> dict[str, str | float]:
        self.require("market_data")
        quote = get_market_data_manager().latest_quote(symbol)
        last_price = (quote.bid + quote.ask) / 2 if quote.ask else quote.bid
        return {
            "symbol": quote.symbol,
            "last_price": round(last_price, 4),
            "source": quote.source,
            "timestamp": quote.timestamp.isoformat(),
        }
