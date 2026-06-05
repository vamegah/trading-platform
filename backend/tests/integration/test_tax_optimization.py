from datetime import date

from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord
from backend.services.portfolio_service.tax_optimizer import optimize_after_tax_sale


def test_tax_optimizer_prioritizes_loss_lots() -> None:
    lots = [
        TaxLotRecord("gain", "AAPL", 10, 80, date(2020, 1, 1)),
        TaxLotRecord("loss", "AAPL", 10, 150, date(2024, 1, 1)),
    ]

    result = optimize_after_tax_sale(lots, quantity=5, current_price=100)

    first_selection = result["selections"][0]
    assert first_selection["lot"].lot_id == "loss"
    assert result["tax_impact"]["realized_gain"] < 0

