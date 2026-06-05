from dataclasses import dataclass

from backend.services.execution_service.order_router import AlmgrenChrissImpactModel


@dataclass(frozen=True)
class TransactionCostBreakdown:
    commission: float
    spread_cost: float
    slippage: float
    market_impact: float
    liquidity_penalty: float
    total_cost: float
    return_drag: float
    notional: float
    participation_rate: float
    effective_spread_bps: float
    slippage_bps: float
    market_impact_bps: float
    liquidity_penalty_bps: float
    capacity_warning: bool


def estimate_transaction_cost(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    daily_volume: float = 1_000_000,
    volatility: float = 0.025,
    commission_per_share: float = 0.0035,
    bid_ask_spread_bps: float = 4.0,
) -> TransactionCostBreakdown:
    notional = abs(quantity) * price
    if notional <= 0:
        return TransactionCostBreakdown(
            commission=0.0,
            spread_cost=0.0,
            slippage=0.0,
            market_impact=0.0,
            liquidity_penalty=0.0,
            total_cost=0.0,
            return_drag=0.0,
            notional=0.0,
            participation_rate=0.0,
            effective_spread_bps=0.0,
            slippage_bps=0.0,
            market_impact_bps=0.0,
            liquidity_penalty_bps=0.0,
            capacity_warning=False,
        )
    participation = abs(quantity) / max(daily_volume, 1.0)
    impact = AlmgrenChrissImpactModel().estimate(
        symbol=symbol,
        order_size=abs(quantity),
        side=side,
        current_price=price,
        daily_volume=daily_volume,
        volatility=volatility,
    )
    commission = max(0.35, abs(quantity) * commission_per_share)
    spread_cost = notional * (bid_ask_spread_bps / 10000) / 2
    slippage = notional * volatility * min(participation, 0.25)
    market_impact = abs(impact.expected_execution_price - price) * abs(quantity)
    liquidity_penalty_rate = 0.002 if participation > 0.1 else 0.0
    if participation > 0.25:
        liquidity_penalty_rate += 0.003
    liquidity_penalty = notional * liquidity_penalty_rate
    total = commission + spread_cost + slippage + market_impact + liquidity_penalty
    return TransactionCostBreakdown(
        commission=round(commission, 2),
        spread_cost=round(spread_cost, 2),
        slippage=round(slippage, 2),
        market_impact=round(market_impact, 2),
        liquidity_penalty=round(liquidity_penalty, 2),
        total_cost=round(total, 2),
        return_drag=round(total / notional, 6) if notional else 0.0,
        notional=round(notional, 2),
        participation_rate=round(participation, 6),
        effective_spread_bps=round((spread_cost / notional) * 10000, 4),
        slippage_bps=round((slippage / notional) * 10000, 4),
        market_impact_bps=round((market_impact / notional) * 10000, 4),
        liquidity_penalty_bps=round((liquidity_penalty / notional) * 10000, 4),
        capacity_warning=participation > 0.1,
    )


def estimate_costs(trades: int, notional: float) -> dict[str, float]:
    if trades <= 0 or notional <= 0:
        return {"commission": 0.0, "slippage": 0.0, "market_impact": 0.0, "return_drag": 0.0}
    average_trade_notional = notional / trades
    average_cost = estimate_transaction_cost("SPY", "BUY", average_trade_notional / 100, 100.0)
    total = average_cost.total_cost * trades
    return {
        "commission": round(average_cost.commission * trades, 2),
        "slippage": round((average_cost.spread_cost + average_cost.slippage) * trades, 2),
        "market_impact": round(average_cost.market_impact * trades, 2),
        "liquidity_penalty": round(average_cost.liquidity_penalty * trades, 2),
        "return_drag": round(total / notional, 4),
        "participation_rate": average_cost.participation_rate,
        "capacity_warning": average_cost.capacity_warning,
    }
