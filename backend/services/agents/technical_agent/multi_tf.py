def _timeframe_bias(candles: list[dict]) -> dict[str, object]:
    closes = [float(candle["close"]) for candle in candles if "close" in candle]
    if len(closes) < 2:
        return {"bias": "neutral", "posture": "range_bound", "return": 0.0, "confidence": 0.5}
    period_return = (closes[-1] - closes[0]) / closes[0]
    bias = "bullish" if period_return > 0.01 else "bearish" if period_return < -0.01 else "neutral"
    posture = "trend_following" if bias in {"bullish", "bearish"} else "range_bound"
    confidence = min(0.95, 0.5 + abs(period_return) * 5)
    return {"bias": bias, "posture": posture, "return": round(period_return, 4), "confidence": round(confidence, 4)}


def aggregate_timeframes(symbol: str, timeframe_candles: dict[str, list[dict]]) -> dict[str, object]:
    summaries = {
        timeframe: _timeframe_bias(candles)
        for timeframe, candles in timeframe_candles.items()
    }
    bullish = sum(1 for item in summaries.values() if item["bias"] == "bullish")
    bearish = sum(1 for item in summaries.values() if item["bias"] == "bearish")
    confluence = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "mixed"
    return {
        "symbol": symbol.upper(),
        "confluence": confluence,
        "timeframes": summaries,
    }
