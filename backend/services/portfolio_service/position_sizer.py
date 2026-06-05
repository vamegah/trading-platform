def kelly_criterion(win_prob: float, avg_win: float, avg_loss: float) -> float:
    """Fraction of capital to risk."""
    if avg_loss == 0:
        return 0
    return (win_prob * avg_win - (1 - win_prob) * abs(avg_loss)) / (
        avg_win * abs(avg_loss)
    )


def volatility_adjusted_position(
    capital: float, risk_per_trade: float, entry_price: float, stop_loss: float
) -> int:
    """Number of shares based on fixed fractional risk."""
    risk_amount = capital * risk_per_trade
    share_risk = abs(entry_price - stop_loss)
    if share_risk == 0:
        return 0
    return int(risk_amount / share_risk)
