from datetime import date

from fastapi import APIRouter

from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord
from backend.services.portfolio_service.tax_optimizer import find_tax_loss_harvests, optimize_after_tax_sale

router = APIRouter()


@router.post("/optimize")
async def optimize_tax(payload: dict) -> dict[str, object]:
    lots = [
        TaxLotRecord(
            lot_id=str(row["lot_id"]),
            symbol=str(row["symbol"]).upper(),
            quantity=float(row["quantity"]),
            cost_per_share=float(row["cost_per_share"]),
            acquisition_date=date.fromisoformat(row["acquisition_date"]),
            account_id=row.get("account_id"),
        )
        for row in payload.get("lots", [])
    ]
    return optimize_after_tax_sale(
        lots=lots,
        quantity=float(payload["quantity"]),
        current_price=float(payload["current_price"]),
        replacement_transactions=payload.get("replacement_transactions", []),
    )


@router.post("/harvest")
async def harvest_tax_losses(payload: dict) -> dict[str, object]:
    lots = [
        TaxLotRecord(
            lot_id=str(row["lot_id"]),
            symbol=str(row["symbol"]).upper(),
            quantity=float(row["quantity"]),
            cost_per_share=float(row["cost_per_share"]),
            acquisition_date=date.fromisoformat(row["acquisition_date"]),
            account_id=row.get("account_id"),
        )
        for row in payload.get("lots", [])
    ]
    opportunities = find_tax_loss_harvests(
        lots,
        {symbol.upper(): float(price) for symbol, price in payload.get("current_prices", {}).items()},
        minimum_loss=float(payload.get("minimum_loss", 250.0)),
        replacement_transactions=payload.get("replacement_transactions", []),
    )
    return {"opportunities": opportunities, "count": len(opportunities)}
