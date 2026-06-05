def _closes(candles: list[dict]) -> list[float]:
    return [float(candle["close"]) for candle in candles if "close" in candle]


def detect_higher_highs(candles: list[dict]) -> bool:
    highs = [float(candle["high"]) for candle in candles if "high" in candle]
    if len(highs) < 3:
        return False
    return highs[-1] > highs[-2] > highs[-3]


def detect_head_and_shoulders(candles: list[dict]) -> bool:
    highs = [float(candle["high"]) for candle in candles if "high" in candle]
    if len(highs) < 5:
        return False
    left, head, right = highs[-5], highs[-3], highs[-1]
    shoulders_close = abs(left - right) / max(head, 1.0) < 0.05
    return head > left and head > right and shoulders_close


def detect_support_resistance(candles: list[dict]) -> dict[str, float]:
    closes = _closes(candles)
    if not closes:
        return {"support": 0.0, "resistance": 0.0}
    recent = closes[-20:]
    return {"support": round(min(recent), 4), "resistance": round(max(recent), 4)}


def detect_patterns(symbol: str, candles: list[dict] | None = None) -> dict[str, object]:
    sample = candles or [
        {"high": 101, "low": 97, "close": 100, "volume": 1200000},
        {"high": 103, "low": 99, "close": 102, "volume": 1300000},
        {"high": 104, "low": 101, "close": 103, "volume": 1500000},
        {"high": 106, "low": 102, "close": 105, "volume": 1700000},
        {"high": 107, "low": 104, "close": 106, "volume": 1800000},
    ]
    patterns: list[str] = []
    if detect_higher_highs(sample):
        patterns.append("higher_highs")
    if detect_head_and_shoulders(sample):
        patterns.append("head_and_shoulders")

    levels = detect_support_resistance(sample)
    return {
        "symbol": symbol.upper(),
        "agent": "technical",
        "patterns": patterns,
        "levels": levels,
        "score": round(0.55 + min(len(patterns) * 0.08, 0.24), 4),
    }
