from math import sqrt
from statistics import mean, pstdev


def max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 1.0
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        worst = min(worst, (value - peak) / peak)
    return round(abs(worst), 4)


def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = [value - daily_rf for value in returns]
    volatility = pstdev(excess)
    return round((mean(excess) / volatility) * sqrt(252), 4) if volatility else 0.0


def sortino_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252
    downside = [min(0.0, value - daily_rf) for value in returns]
    downside_deviation = sqrt(mean([value * value for value in downside])) if downside else 0.0
    return round((mean(returns) - daily_rf) / downside_deviation * sqrt(252), 4) if downside_deviation else 0.0


def profit_factor(trades: list[dict]) -> float:
    gains = sum(max(float(trade.get("pnl", 0.0)), 0.0) for trade in trades)
    losses = abs(sum(min(float(trade.get("pnl", 0.0)), 0.0) for trade in trades))
    return round(gains / losses, 4) if losses else round(gains, 4)


def win_rate(trades: list[dict]) -> float:
    closed = [trade for trade in trades if "pnl" in trade]
    if not closed:
        return 0.0
    wins = [trade for trade in closed if float(trade.get("pnl", 0.0)) > 0]
    return round(len(wins) / len(closed), 4)


def calmar_ratio(annualized_return: float, drawdown: float) -> float:
    return round(annualized_return / drawdown, 4) if drawdown else 0.0


def summarize_performance(
    equity_curve: list[float],
    returns: list[float],
    trades: list[dict],
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    if not equity_curve:
        return {
            "annualized_return": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "calmar": 0.0,
            "total_return": 0.0,
            "annualized_volatility": 0.0,
            "trade_count": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "expectancy": 0.0,
        }
    total_return = equity_curve[-1] / equity_curve[0] - 1
    annualized = (1 + total_return) ** (252 / max(len(equity_curve), 1)) - 1
    drawdown = max_drawdown(equity_curve)
    closed_pnls = [float(trade.get("pnl", 0.0)) for trade in trades if "pnl" in trade]
    wins = [pnl for pnl in closed_pnls if pnl > 0]
    losses = [pnl for pnl in closed_pnls if pnl < 0]
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    annualized_volatility = pstdev(returns) * sqrt(252) if len(returns) > 1 else 0.0
    return {
        "total_return": round(total_return, 4),
        "annualized_return": round(annualized, 4),
        "annualized_volatility": round(annualized_volatility, 4),
        "sharpe": sharpe_ratio(returns, risk_free_rate),
        "sortino": sortino_ratio(returns, risk_free_rate),
        "max_drawdown": drawdown,
        "win_rate": win_rate(trades),
        "profit_factor": profit_factor(trades),
        "calmar": calmar_ratio(annualized, drawdown),
        "trade_count": len(closed_pnls),
        "average_win": round(average_win, 4),
        "average_loss": round(average_loss, 4),
        "expectancy": round(sum(closed_pnls) / len(closed_pnls), 4) if closed_pnls else 0.0,
    }
