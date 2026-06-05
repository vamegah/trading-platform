from dataclasses import dataclass
from datetime import date

from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord, TaxLotSelection
from backend.shared.config import settings


@dataclass(frozen=True)
class TaxImpact:
    realized_gain: float
    estimated_tax: float
    after_tax_proceeds: float
    short_term_gain: float
    long_term_gain: float
    disallowed_wash_sale_loss: float


class TaxOptimizer:
    def __init__(
        self,
        short_term_rate: float | None = None,
        long_term_rate: float | None = None,
    ):
        self.short_term_rate = short_term_rate if short_term_rate is not None else settings.short_term_cap_gains_rate
        self.long_term_rate = long_term_rate if long_term_rate is not None else settings.long_term_cap_gains_rate

    def estimate_tax_impact(
        self,
        selections: list[TaxLotSelection],
        current_price: float,
        as_of: date | None = None,
    ) -> TaxImpact:
        evaluation_date = as_of or date.today()
        realized_gain = 0.0
        estimated_tax = 0.0
        short_term_gain = 0.0
        long_term_gain = 0.0
        disallowed_wash_sale_loss = 0.0

        for selection in selections:
            gain = (current_price - selection.lot.cost_per_share) * selection.quantity
            holding_days = (evaluation_date - selection.lot.acquisition_date).days
            rate = self.long_term_rate if holding_days >= 365 else self.short_term_rate
            taxable_gain = gain
            if gain < 0 and selection.wash_sale_risk:
                disallowed_wash_sale_loss += abs(gain)
                taxable_gain = 0.0
            realized_gain += gain
            estimated_tax += taxable_gain * rate
            if holding_days >= 365:
                long_term_gain += taxable_gain
            else:
                short_term_gain += taxable_gain

        proceeds = sum(selection.quantity * current_price for selection in selections)
        return TaxImpact(
            realized_gain=round(realized_gain, 2),
            estimated_tax=round(estimated_tax, 2),
            after_tax_proceeds=round(proceeds - estimated_tax, 2),
            short_term_gain=round(short_term_gain, 2),
            long_term_gain=round(long_term_gain, 2),
            disallowed_wash_sale_loss=round(disallowed_wash_sale_loss, 2),
        )

    def rank_sell_candidates(
        self,
        lots: list[TaxLotRecord],
        current_price: float,
        as_of: date | None = None,
    ) -> list[TaxLotRecord]:
        evaluation_date = as_of or date.today()

        def score(lot: TaxLotRecord) -> tuple[float, int, float]:
            unrealized_gain = current_price - lot.cost_per_share
            holding_days = (evaluation_date - lot.acquisition_date).days
            long_term_bonus = 1 if holding_days >= 365 else 0
            return (unrealized_gain, -long_term_bonus, -lot.cost_per_share)

        return sorted(lots, key=score)


def optimize_after_tax_sale(
    lots: list[TaxLotRecord],
    quantity: float,
    current_price: float,
    replacement_transactions: list[dict] | None = None,
    as_of: date | None = None,
) -> dict[str, object]:
    from backend.services.portfolio_service.tax_lot_manager import TaxLotManager

    manager = TaxLotManager(lots, replacement_transactions or [])
    evaluation_date = as_of or date.today()
    selections, unfilled = manager.select_lots_for_sale(quantity, current_price, evaluation_date)
    impact = TaxOptimizer().estimate_tax_impact(selections, current_price, evaluation_date)
    return {
        "selections": [
            _selection_payload(selection, current_price, manager, evaluation_date)
            for selection in selections
        ],
        "unfilled_quantity": unfilled,
        "tax_impact": impact.__dict__,
        "wash_sale_window_days": manager.wash_sale_window.days,
        "wash_sale_window": manager.wash_sale_window_bounds(evaluation_date),
        "holding_period_policy": {
            "long_term_threshold_days": 365,
            "short_term_rate": TaxOptimizer().short_term_rate,
            "long_term_rate": TaxOptimizer().long_term_rate,
        },
        "objective": "maximize_after_tax_proceeds_while_prioritizing_realized_losses",
    }


def find_tax_loss_harvests(
    lots: list[TaxLotRecord],
    current_prices: dict[str, float],
    minimum_loss: float = 250.0,
    replacement_transactions: list[dict] | None = None,
) -> list[dict[str, object]]:
    from backend.services.portfolio_service.tax_lot_manager import TaxLotManager

    manager = TaxLotManager(lots, replacement_transactions or [])
    opportunities = []
    for lot in lots:
        current_price = current_prices.get(lot.symbol.upper())
        if current_price is None:
            continue
        unrealized_loss = (current_price - lot.cost_per_share) * lot.quantity
        holding_days = manager.holding_period_days(lot)
        wash_sale_risk = manager.has_wash_sale_risk(lot.symbol)
        if unrealized_loss <= -abs(minimum_loss):
            opportunities.append(
                {
                    "lot_id": lot.lot_id,
                    "symbol": lot.symbol,
                    "quantity": lot.quantity,
                    "unrealized_loss": round(unrealized_loss, 2),
                    "wash_sale_risk": wash_sale_risk,
                    "wash_sale_window_days": manager.wash_sale_window.days,
                    "holding_period_days": holding_days,
                    "term": "long_term" if holding_days >= 365 else "short_term",
                    "disallowed_loss_if_replaced": round(abs(unrealized_loss), 2) if wash_sale_risk else 0.0,
                    "action": "harvest" if not wash_sale_risk else "defer_wash_sale",
                    "replacement_allowed": not wash_sale_risk,
                    "rationale": (
                        "Harvesting is available because no substantially identical purchase was found in the wash-sale window."
                        if not wash_sale_risk
                        else "Harvesting should be deferred because a substantially identical purchase creates wash-sale risk."
                    ),
                }
            )
    return sorted(opportunities, key=lambda item: item["unrealized_loss"])


def _selection_payload(
    selection: TaxLotSelection,
    current_price: float,
    manager,
    evaluation_date: date,
) -> dict[str, object]:
    holding_days = manager.holding_period_days(selection.lot, evaluation_date)
    realized_gain = (current_price - selection.lot.cost_per_share) * selection.quantity
    return {
        **selection.__dict__,
        "lot_details": {
            "lot_id": selection.lot.lot_id,
            "symbol": selection.lot.symbol,
            "quantity": selection.lot.quantity,
            "cost_per_share": selection.lot.cost_per_share,
            "acquisition_date": selection.lot.acquisition_date.isoformat(),
            "account_id": selection.lot.account_id,
        },
        "holding_period_days": holding_days,
        "term": "long_term" if holding_days >= 365 else "short_term",
        "realized_gain": round(realized_gain, 2),
        "deferred_loss": round(abs(realized_gain), 2) if realized_gain < 0 and selection.wash_sale_risk else 0.0,
    }
