from dataclasses import dataclass
from datetime import date, datetime, timedelta

from backend.shared.config import settings


@dataclass(frozen=True)
class TaxLotRecord:
    lot_id: str
    symbol: str
    quantity: float
    cost_per_share: float
    acquisition_date: date
    account_id: str | None = None


@dataclass(frozen=True)
class TaxLotSelection:
    lot: TaxLotRecord
    quantity: float
    wash_sale_risk: bool = False


class TaxLotManager:
    def __init__(self, lots: list[TaxLotRecord], recent_transactions: list[dict] | None = None):
        self.lots = lots
        self.recent_transactions = recent_transactions or []
        self.wash_sale_window = timedelta(days=settings.wash_sale_window_days)

    def select_lots_for_sale(
        self,
        quantity: float,
        current_price: float,
        as_of: date | None = None,
    ) -> tuple[list[TaxLotSelection], float]:
        evaluation_date = as_of or date.today()
        ranked_lots = sorted(
            self.lots,
            key=lambda lot: (
                current_price - lot.cost_per_share,
                -lot.quantity,
                lot.acquisition_date,
            ),
        )

        selected: list[TaxLotSelection] = []
        remaining = quantity
        for lot in ranked_lots:
            if remaining <= 0:
                break
            sell_quantity = min(lot.quantity, remaining)
            selected.append(
                TaxLotSelection(
                    lot=lot,
                    quantity=sell_quantity,
                    wash_sale_risk=self.has_wash_sale_risk(lot.symbol, evaluation_date),
                )
            )
            remaining -= sell_quantity

        return selected, round(remaining, 8)

    def has_wash_sale_risk(self, symbol: str, sell_date: date | None = None) -> bool:
        evaluation_date = sell_date or date.today()
        lower = evaluation_date - self.wash_sale_window
        upper = evaluation_date + self.wash_sale_window
        for transaction in self.recent_transactions:
            transaction_date = _coerce_date(transaction.get("date"))
            if (
                _matches_symbol(transaction, symbol)
                and transaction.get("side", "").upper() == "BUY"
                and transaction_date
                and lower <= transaction_date <= upper
            ):
                return True
        return False

    def holding_period_days(self, lot: TaxLotRecord, as_of: date | None = None) -> int:
        evaluation_date = as_of or date.today()
        return max(0, (evaluation_date - lot.acquisition_date).days)

    def is_long_term(self, lot: TaxLotRecord, as_of: date | None = None) -> bool:
        return self.holding_period_days(lot, as_of) >= 365

    def wash_sale_window_bounds(self, sell_date: date | None = None) -> dict[str, str]:
        evaluation_date = sell_date or date.today()
        return {
            "start": (evaluation_date - self.wash_sale_window).isoformat(),
            "end": (evaluation_date + self.wash_sale_window).isoformat(),
        }


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _matches_symbol(transaction: dict, symbol: str) -> bool:
    normalized = symbol.upper()
    candidates = {
        str(transaction.get("symbol", "")).upper(),
        str(transaction.get("replacement_for", "")).upper(),
        str(transaction.get("substantially_identical_to", "")).upper(),
        str(transaction.get("underlying_symbol", "")).upper(),
    }
    return normalized in candidates


def ingest_tax_lot_cost_basis(rows: list[dict]) -> list[TaxLotRecord]:
    return [
        TaxLotRecord(
            lot_id=str(row["lot_id"]),
            symbol=str(row["symbol"]).upper(),
            quantity=float(row["quantity"]),
            cost_per_share=float(row["cost_per_share"]),
            acquisition_date=row["acquisition_date"],
            account_id=row.get("account_id"),
        )
        for row in rows
    ]
