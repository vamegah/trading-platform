from dataclasses import dataclass

from backend.shared.config import settings


@dataclass(frozen=True)
class PositionSizingInput:
    equity: float
    entry_price: float
    stop_loss: float
    win_probability: float
    average_win_pct: float
    average_loss_pct: float
    volatility: float
    portfolio_volatility: float
    max_drawdown_tolerance: float
    current_portfolio_risk: float = 0.0
    risk_profile: str = "balanced"


@dataclass(frozen=True)
class PositionSizingResult:
    method: str
    quantity: int
    notional: float
    portfolio_weight: float
    risk_budget: float
    limiting_constraint: str
    components: dict[str, float]
    remaining_drawdown_budget: float
    current_portfolio_risk: float
    max_drawdown_tolerance: float
    risk_profile_multiplier: float
    per_share_risk: float
    constraints: dict[str, float | str]


RISK_PROFILE_MULTIPLIER = {
    "conservative": 0.55,
    "low": 0.55,
    "balanced": 0.85,
    "medium": 0.85,
    "aggressive": 1.15,
    "high": 1.15,
}


def kelly_fraction(win_probability: float, average_win_pct: float, average_loss_pct: float) -> float:
    loss = abs(average_loss_pct)
    if loss <= 0 or average_win_pct <= 0:
        return 0.0
    odds = average_win_pct / loss
    raw_fraction = win_probability - ((1 - win_probability) / odds)
    return max(0.0, raw_fraction)


def volatility_adjusted_notional(
    equity: float,
    entry_price: float,
    stop_loss: float,
    risk_budget: float,
) -> float:
    per_share_risk = abs(entry_price - stop_loss)
    if per_share_risk <= 0 or entry_price <= 0:
        return 0.0
    shares = (equity * risk_budget) / per_share_risk
    return shares * entry_price


def risk_parity_notional(equity: float, volatility: float, portfolio_volatility: float) -> float:
    target_risk_share = max(0.02, min(0.18, portfolio_volatility / max(volatility, 0.001) * 0.08))
    return equity * target_risk_share


def calculate_position_size(payload: PositionSizingInput) -> PositionSizingResult:
    profile_multiplier = RISK_PROFILE_MULTIPLIER.get(payload.risk_profile, 0.85)
    remaining_drawdown_budget = max(0.0, payload.max_drawdown_tolerance - payload.current_portfolio_risk)
    risk_budget = min(0.025 * profile_multiplier, remaining_drawdown_budget / 4)
    per_share_risk = abs(payload.entry_price - payload.stop_loss)

    kelly_notional = payload.equity * min(
        kelly_fraction(payload.win_probability, payload.average_win_pct, payload.average_loss_pct) * 0.5,
        settings.max_position_pct,
    )
    volatility_notional = volatility_adjusted_notional(
        payload.equity,
        payload.entry_price,
        payload.stop_loss,
        risk_budget,
    )
    parity_notional = risk_parity_notional(payload.equity, payload.volatility, payload.portfolio_volatility)
    max_weight_notional = payload.equity * settings.max_position_pct

    candidates = {
        "kelly": kelly_notional,
        "volatility_adjusted": volatility_notional,
        "risk_parity": parity_notional,
        "max_position_weight": max_weight_notional,
        "drawdown_budget": payload.equity * max(remaining_drawdown_budget, 0.0),
    }
    limiting_constraint, notional = min(candidates.items(), key=lambda item: item[1])
    quantity = int(max(0.0, notional) / max(payload.entry_price, 0.01))
    final_notional = round(quantity * payload.entry_price, 2)
    return PositionSizingResult(
        method="min_of_kelly_volatility_risk_parity",
        quantity=quantity,
        notional=final_notional,
        portfolio_weight=round(final_notional / payload.equity, 4) if payload.equity else 0.0,
        risk_budget=round(risk_budget, 4),
        limiting_constraint=limiting_constraint,
        components={key: round(value, 2) for key, value in candidates.items()},
        remaining_drawdown_budget=round(remaining_drawdown_budget, 4),
        current_portfolio_risk=round(payload.current_portfolio_risk, 4),
        max_drawdown_tolerance=round(payload.max_drawdown_tolerance, 4),
        risk_profile_multiplier=round(profile_multiplier, 4),
        per_share_risk=round(per_share_risk, 4),
        constraints={
            "max_position_pct": settings.max_position_pct,
            "risk_profile": payload.risk_profile,
            "drawdown_guard": remaining_drawdown_budget,
            "portfolio_volatility": payload.portfolio_volatility,
        },
    )


def size_position(equity: float, risk_score: float) -> float:
    risk_budget = max(0.0025, 0.02 * (1 - risk_score))
    return round(equity * risk_budget, 2)
