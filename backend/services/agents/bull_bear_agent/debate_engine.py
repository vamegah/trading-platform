def run_debate(symbol: str, agent_outputs: dict | None = None) -> dict[str, object]:
    outputs = agent_outputs or {}
    technical_score = float(outputs.get("technical", {}).get("confidence", 0.62))
    fundamentals_score = float(outputs.get("fundamentals", {}).get("score", 0.6))
    if fundamentals_score > 1:
        fundamentals_score = fundamentals_score / 100

    bull_score = round(5 + fundamentals_score * 3 + technical_score * 2, 2)
    bear_score = round(10 - bull_score + 1.5, 2)
    conviction = round((bull_score - bear_score) / 10, 4)

    return {
        "symbol": symbol.upper(),
        "agent": "bull_bear_debate",
        "bull_thesis": [
            "Fundamental quality and technical posture support upside optionality.",
            "Risk can be defined with stop-loss and position sizing controls.",
        ],
        "bear_thesis": [
            "Valuation, macro shocks, or stale signal decay could invalidate the setup.",
            "Execution impact and portfolio concentration must be checked before entry.",
        ],
        "unresolved_risks": [
            "Signal may decay before entry zone is reached.",
            "Factor concentration can reduce diversification benefit.",
        ],
        "bull_score": max(1.0, min(bull_score, 10.0)),
        "bear_score": max(1.0, min(bear_score, 10.0)),
        "balanced_score": round((bull_score + (10 - bear_score)) / 2, 4),
        "conviction": max(-1.0, min(conviction, 1.0)),
    }


class DebateEngine:
    def debate(self, stock_data: dict, agent_outputs: dict) -> dict[str, object]:
        return run_debate(stock_data["symbol"], agent_outputs)
