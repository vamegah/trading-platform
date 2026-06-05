from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter


@dataclass(frozen=True)
class RiskLimits:
    var_limit: float = 5000.0
    cvar_limit: float = 7500.0
    beta_limit: float = 1.4
    dollar_risk_limit: float = 12000.0
    correlation_limit: float = 0.85
    margin_usage_limit: float = 0.5
    target_latency_ms: float = 500.0


CRITICAL_ACTIONS = {
    "var": "halt_new_orders_cancel_pending",
    "cvar": "halt_new_orders_cancel_pending",
    "dollar_risk": "halt_new_orders_cancel_pending",
    "margin_usage": "halt_new_orders_cancel_pending",
    "beta": "halt_new_orders_review_hedge",
    "max_correlation": "halt_new_orders_review_hedge",
}


class LiveRiskMonitor:
    def evaluate(self, portfolio: list[dict], limits: RiskLimits | None = None) -> dict[str, object]:
        started = perf_counter()
        evaluated_at = datetime.now(UTC).isoformat()
        limits = limits or RiskLimits()
        total_value = sum(float(position.get("market_value", 0.0)) for position in portfolio) or 1.0
        weighted_beta = sum(
            float(position.get("market_value", 0.0)) * float(position.get("beta", 1.0))
            for position in portfolio
        ) / total_value
        weighted_volatility = sum(
            float(position.get("market_value", 0.0)) * float(position.get("volatility", 0.015))
            for position in portfolio
        ) / total_value
        max_pairwise_correlation = max(
            [float(position.get("correlation", 0.0)) for position in portfolio] or [0.0]
        )
        margin_usage = sum(float(position.get("margin", 0.0)) for position in portfolio) / total_value
        dollar_risk = sum(
            abs(float(position.get("market_value", 0.0)) * float(position.get("stop_loss_pct", 0.08)))
            for position in portfolio
        )
        var = total_value * weighted_volatility * 1.645
        cvar = var * 1.45
        metrics = {
            "var": round(var, 2),
            "cvar": round(cvar, 2),
            "beta": round(weighted_beta, 4),
            "dollar_risk": round(dollar_risk, 2),
            "max_correlation": round(max_pairwise_correlation, 4),
            "margin_usage": round(margin_usage, 4),
        }
        breaches = []
        checks = {
            "var": (metrics["var"], limits.var_limit),
            "cvar": (metrics["cvar"], limits.cvar_limit),
            "beta": (metrics["beta"], limits.beta_limit),
            "dollar_risk": (metrics["dollar_risk"], limits.dollar_risk_limit),
            "max_correlation": (metrics["max_correlation"], limits.correlation_limit),
            "margin_usage": (metrics["margin_usage"], limits.margin_usage_limit),
        }
        for name, (value, limit) in checks.items():
            if value > limit:
                event_id = f"risk-{name}-{len(breaches) + 1}"
                action = CRITICAL_ACTIONS.get(name, "halt_new_orders_review")
                breaches.append(
                    {
                        "event_id": event_id,
                        "metric": name,
                        "value": value,
                        "limit": limit,
                        "severity": "critical",
                        "action": action,
                    }
                )
        latency_ms = round((perf_counter() - started) * 1000, 3)
        risk_breach_events = [
            {
                "event_id": breach["event_id"],
                "event_type": "portfolio_risk_breach",
                "metric": breach["metric"],
                "value": breach["value"],
                "limit": breach["limit"],
                "severity": breach["severity"],
                "action": breach["action"],
                "created_at": evaluated_at,
                "portfolio_value": round(total_value, 2),
            }
            for breach in breaches
        ]
        kill_switch_required = any(breach["severity"] == "critical" for breach in breaches)
        recommended_actions = sorted({str(event["action"]) for event in risk_breach_events})
        return {
            "portfolio_value": round(total_value, 2),
            "metrics": metrics,
            "breaches": breaches,
            "risk_breach_events": risk_breach_events,
            "kill_switch_required": kill_switch_required,
            "new_orders_blocked": kill_switch_required,
            "cancel_pending_orders": kill_switch_required,
            "manual_review_required": bool(breaches),
            "recommended_actions": recommended_actions,
            "evaluated_at": evaluated_at,
            "latency_ms": latency_ms,
            "target_latency_ms": limits.target_latency_ms,
            "within_target_latency": latency_ms <= limits.target_latency_ms,
        }


async def compute_var(portfolio_id: str, confidence: float = 0.95) -> float:
    z_score = 1.645 if confidence == 0.95 else 2.33
    portfolio_value = 100000.0
    daily_volatility = 0.015
    return round(portfolio_value * daily_volatility * z_score, 2)


async def check_kill_switch(portfolio_id: str, var_limit: float = 5000.0) -> bool:
    return await compute_var(portfolio_id) > var_limit
