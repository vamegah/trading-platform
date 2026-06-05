from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord
from backend.services.portfolio_service.tax_optimizer import optimize_after_tax_sale


DEFAULT_FACTOR_MAP = {
    "AAPL": {"growth": 0.35, "quality": 0.28, "momentum": 0.22},
    "MSFT": {"growth": 0.26, "quality": 0.35, "momentum": 0.18},
    "NVDA": {"growth": 0.48, "momentum": 0.34, "size": 0.2},
    "SPY": {"market": 1.0, "size": 0.1},
    "QQQ": {"growth": 0.42, "momentum": 0.25, "market": 1.1},
}

DEFAULT_SECTORS = {
    "AAPL": "technology",
    "MSFT": "technology",
    "NVDA": "semiconductors",
    "SPY": "broad_market",
    "QQQ": "technology",
}


def _weights(holdings: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in holdings.values()) or 1.0
    return {symbol.upper(): round(max(value, 0.0) / total, 4) for symbol, value in holdings.items()}


def _aggregate_exposure(weights: dict[str, float], exposure_map: dict[str, dict[str, float]]) -> dict[str, float]:
    exposures: dict[str, float] = {}
    for symbol, weight in weights.items():
        for factor, value in exposure_map.get(symbol, {"market": 1.0}).items():
            exposures[factor] = exposures.get(factor, 0.0) + weight * value
    return {factor: round(value, 4) for factor, value in exposures.items()}


def _sector_weights(weights: dict[str, float], sectors: dict[str, str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for symbol, weight in weights.items():
        sector = sectors.get(symbol, "unknown")
        result[sector] = result.get(sector, 0.0) + weight
    return {sector: round(weight, 4) for sector, weight in result.items()}


def _expected_sharpe(weights: dict[str, float], factor_exposures: dict[str, float]) -> float:
    concentration_penalty = sum(weight**2 for weight in weights.values()) * 0.35
    factor_penalty = max(factor_exposures.values(), default=0.0) * 0.25
    diversification_bonus = min(len(weights) * 0.04, 0.2)
    return round(0.75 + diversification_bonus - concentration_penalty - factor_penalty, 4)


def _concentration_summary(weights: dict[str, float]) -> dict[str, object]:
    if not weights:
        return {
            "max_position_weight": 0.0,
            "top_position": None,
            "herfindahl_index": 0.0,
            "position_count": 0,
        }
    top_position, max_weight = max(weights.items(), key=lambda item: item[1])
    return {
        "max_position_weight": round(max_weight, 4),
        "top_position": top_position,
        "herfindahl_index": round(sum(weight**2 for weight in weights.values()), 4),
        "position_count": len(weights),
    }


def optimize_portfolio(holdings: dict[str, float], constraints: dict | None = None) -> dict[str, object]:
    constraints = constraints or {}
    max_weight = constraints.get("max_weight", 1.0)
    weights = {
        symbol: min(weight, max_weight)
        for symbol, weight in _weights(holdings).items()
    }
    factor_exposures = _aggregate_exposure(weights, constraints.get("factor_exposures", DEFAULT_FACTOR_MAP))
    sector_weights = _sector_weights(weights, constraints.get("sectors", DEFAULT_SECTORS))
    breaches = []
    max_factor = constraints.get("max_factor_exposure", 0.45)
    max_sector = constraints.get("max_sector_weight", 0.5)
    max_correlation = constraints.get("max_correlation", 0.85)

    breaches.extend(
        {
            "type": "factor_concentration",
            "name": factor,
            "value": value,
            "limit": max_factor,
        }
        for factor, value in factor_exposures.items()
        if value > max_factor
    )
    breaches.extend(
        {
            "type": "sector_concentration",
            "name": sector,
            "value": value,
            "limit": max_sector,
        }
        for sector, value in sector_weights.items()
        if value > max_sector
    )
    for pair, correlation in constraints.get("correlations", {}).items():
        if correlation > max_correlation:
            breaches.append({"type": "correlation", "name": pair, "value": correlation, "limit": max_correlation})

    return {
        "weights": weights,
        "factor_exposures": factor_exposures,
        "sector_weights": sector_weights,
        "concentration": _concentration_summary(weights),
        "expected_sharpe": _expected_sharpe(weights, factor_exposures),
        "constraint_breaches": breaches,
        "objective": "after_tax_risk_adjusted_return",
        "constraints": constraints,
        "recommendation": "rebalance_required" if breaches else "portfolio_within_limits",
    }


def evaluate_trade_impact(
    holdings: dict[str, float],
    proposed_trade: dict[str, float | str],
    constraints: dict | None = None,
) -> dict[str, object]:
    before = optimize_portfolio(holdings, constraints)
    symbol = str(proposed_trade["symbol"]).upper()
    notional = float(proposed_trade.get("notional", 0.0))
    side = str(proposed_trade.get("side", "BUY")).upper()
    after_holdings = {key.upper(): value for key, value in holdings.items()}
    after_holdings[symbol] = after_holdings.get(symbol, 0.0) + (notional if side == "BUY" else -notional)
    after = optimize_portfolio(after_holdings, constraints)
    expected_sharpe_delta = round(float(after["expected_sharpe"]) - float(before["expected_sharpe"]), 4)
    before_concentration = before["concentration"]
    after_concentration = after["concentration"]
    concentration_delta = round(
        float(after_concentration["herfindahl_index"]) - float(before_concentration["herfindahl_index"]),
        4,
    )
    before_breach_keys = {
        f"{breach['type']}:{breach['name']}"
        for breach in before["constraint_breaches"]
    }
    after_breach_keys = {
        f"{breach['type']}:{breach['name']}"
        for breach in after["constraint_breaches"]
    }
    new_breaches = sorted(after_breach_keys - before_breach_keys)
    resolved_breaches = sorted(before_breach_keys - after_breach_keys)
    trade_allowed = not after["constraint_breaches"]
    improves_expected_sharpe = expected_sharpe_delta > 0
    improves_concentration = concentration_delta <= 0
    return {
        "before": before,
        "after": after,
        "expected_sharpe_delta": expected_sharpe_delta,
        "before_concentration": before_concentration,
        "after_concentration": after_concentration,
        "concentration_delta": concentration_delta,
        "improves_expected_sharpe": improves_expected_sharpe,
        "improves_concentration": improves_concentration,
        "trade_allowed": trade_allowed,
        "review_required": not trade_allowed or not improves_expected_sharpe or not improves_concentration,
        "constraint_impact": {
            "new_breaches": new_breaches,
            "resolved_breaches": resolved_breaches,
            "breach_count_delta": len(after["constraint_breaches"]) - len(before["constraint_breaches"]),
            "after_breach_count": len(after["constraint_breaches"]),
        },
        "explanation": (
            "Trade improves expected Sharpe and stays within factor, sector, and correlation limits."
            if improves_expected_sharpe and trade_allowed
            else "Trade requires review because it worsens Sharpe or breaches concentration limits."
        ),
    }


def optimize_weights_with_max_weight(holdings: dict[str, float], constraints: dict | None = None) -> dict[str, object]:
    constraints = constraints or {}
    max_weight = (constraints or {}).get("max_weight", 1.0)
    weights = {
        symbol: min(weight, max_weight)
        for symbol, weight in _weights(holdings).items()
    }
    return {
        "weights": weights,
        "objective": "after_tax_risk_adjusted_return",
        "constraints": constraints or {},
    }


def optimize_portfolio_after_tax(
    holdings: dict[str, float],
    lots: list[TaxLotRecord],
    proposed_sales: dict[str, float],
    current_prices: dict[str, float],
) -> dict[str, object]:
    base = optimize_portfolio(holdings)
    tax_plan = {}
    for symbol, quantity in proposed_sales.items():
        symbol_lots = [lot for lot in lots if lot.symbol == symbol.upper()]
        tax_plan[symbol.upper()] = optimize_after_tax_sale(
            lots=symbol_lots,
            quantity=quantity,
            current_price=current_prices[symbol.upper()],
        )
    return {**base, "tax_plan": tax_plan}
