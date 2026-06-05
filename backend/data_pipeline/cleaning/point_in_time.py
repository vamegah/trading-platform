from datetime import date

from backend.services.portfolio_service.tax_lot_manager import TaxLotRecord


def filter_point_in_time(rows: list[dict], as_of: date) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("effective_date", date.min) <= as_of
        and (row.get("expiration_date") is None or row["expiration_date"] > as_of)
    ]


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
