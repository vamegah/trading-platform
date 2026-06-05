from statistics import quantiles


def _sample_returns(symbol: str, lookback_days: int) -> list[float]:
    seed = sum(ord(char) for char in symbol.upper())
    return [((seed + day) % 11 - 5) / 1000 for day in range(max(lookback_days, 10))]


def portfolio_historical_var(
    positions: dict[str, float],
    lookback_days: int = 252,
    confidence: float = 0.95,
    prices: dict[str, float] | None = None,
) -> float:
    if not positions:
        return 0.0
    price_map = prices or {symbol: 100.0 for symbol in positions}
    gross_value = sum(abs(quantity) * price_map.get(symbol, 100.0) for symbol, quantity in positions.items()) or 1.0
    weights = {
        symbol: abs(quantity) * price_map.get(symbol, 100.0) / gross_value
        for symbol, quantity in positions.items()
    }
    portfolio_returns = []
    samples = {symbol: _sample_returns(symbol, lookback_days) for symbol in positions}
    for index in range(lookback_days):
        portfolio_returns.append(
            sum(weights[symbol] * samples[symbol][index % len(samples[symbol])] for symbol in positions)
        )
    percentile_index = max(0, min(98, int((1 - confidence) * 100)))
    cutoffs = quantiles(portfolio_returns, n=100)
    return round(abs(cutoffs[percentile_index]), 6)
