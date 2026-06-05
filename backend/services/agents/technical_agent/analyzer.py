from statistics import mean

from backend.services.agents.technical_agent.multi_tf import aggregate_timeframes
from backend.services.agents.technical_agent.pattern_engine import detect_patterns


def _moving_average(values: list[float], window: int) -> float:
    if not values:
        return 0.0
    sample = values[-window:] if len(values) >= window else values
    return mean(sample)


def _momentum_score(closes: list[float]) -> float:
    if len(closes) < 2 or closes[0] == 0:
        return 0.5
    change = (closes[-1] - closes[0]) / closes[0]
    return max(0.0, min(1.0, 0.5 + change * 5))


def _volume_confirmation(volumes: list[float]) -> bool:
    if len(volumes) < 6:
        return False
    return mean(volumes[-3:]) > mean(volumes[-6:-3])


def _volume_profile(volumes: list[float]) -> dict[str, float]:
    if not volumes:
        return {"recent_volume": 0.0, "average_volume": 0.0, "relative_volume": 0.0}
    average_volume = mean(volumes)
    recent_volume = volumes[-1]
    return {
        "recent_volume": round(recent_volume, 4),
        "average_volume": round(average_volume, 4),
        "relative_volume": round(recent_volume / average_volume, 4) if average_volume else 0.0,
    }


class TechnicalAnalyzer:
    def analyze(self, symbol: str, candles: list[dict], asset_type: str = "equity") -> dict[str, object]:
        closes = [float(candle["close"]) for candle in candles if "close" in candle]
        volumes = [float(candle.get("volume", 0.0)) for candle in candles]
        short_ma = _moving_average(closes, 20)
        long_ma = _moving_average(closes, 50)
        trend = "uptrend" if short_ma >= long_ma else "downtrend"
        momentum = _momentum_score(closes)
        volume_confirmed = _volume_confirmation(volumes)
        patterns = detect_patterns(symbol, candles)
        timeframe_summary = aggregate_timeframes(symbol, {"daily": candles, "weekly": candles[::2] or candles})
        levels = patterns["levels"]
        gap_signal = "gap_up" if len(closes) >= 2 and closes[-1] > closes[-2] * 1.02 else "none"

        confidence = momentum
        if trend == "uptrend":
            confidence += 0.08
        if volume_confirmed:
            confidence += 0.05
        if patterns["patterns"]:
            confidence += 0.04

        return {
            "symbol": symbol.upper(),
            "asset_type": asset_type,
            "agent": "technical",
            "trend": trend,
            "short_ma": round(short_ma, 4),
            "long_ma": round(long_ma, 4),
            "momentum_score": round(momentum, 4),
            "volume_confirmed": volume_confirmed,
            "patterns": patterns["patterns"],
            "support_resistance": levels,
            "volume_profile": _volume_profile(volumes),
            "gap_signal": gap_signal,
            "timeframes": timeframe_summary,
            "regime_awareness": "trending" if trend == "uptrend" else "mean_reverting",
            "confidence": round(max(0.0, min(confidence, 1.0)), 4),
        }


def analyze_technicals(symbol: str, candles: list[dict] | None = None, asset_type: str = "equity") -> dict[str, object]:
    sample = candles or [
        {"open": 98, "high": 101, "low": 97, "close": 100, "volume": 1200000},
        {"open": 100, "high": 103, "low": 99, "close": 102, "volume": 1300000},
        {"open": 102, "high": 104, "low": 101, "close": 103, "volume": 1500000},
        {"open": 103, "high": 106, "low": 102, "close": 105, "volume": 1700000},
        {"open": 105, "high": 107, "low": 104, "close": 106, "volume": 1800000},
        {"open": 106, "high": 109, "low": 105, "close": 108, "volume": 2100000},
    ]
    return TechnicalAnalyzer().analyze(symbol, sample, asset_type)
