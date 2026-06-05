from dataclasses import dataclass

from backend.shared.config import settings


@dataclass(frozen=True)
class BlackSwanSignal:
    triggered: bool
    reasons: list[str]
    severity: str


class BlackSwanDetector:
    def evaluate(
        self,
        volatility_zscore: float,
        correlation_spike: float,
        liquidity_drop: float,
    ) -> BlackSwanSignal:
        reasons: list[str] = []
        if volatility_zscore >= settings.black_swan_volatility_zscore:
            reasons.append("volatility_spike")
        if correlation_spike >= settings.black_swan_correlation_threshold:
            reasons.append("correlation_breakdown")
        if liquidity_drop >= settings.black_swan_liquidity_drop_threshold:
            reasons.append("liquidity_drop")

        return BlackSwanSignal(
            triggered=bool(reasons),
            reasons=reasons,
            severity="critical" if len(reasons) >= 2 else "warning" if reasons else "normal",
        )
