from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SecurityMasterRecord:
    symbol: str
    name: str
    exchange: str
    asset_type: str
    listing_date: date
    delisting_date: date | None = None

    def is_member_as_of(self, as_of: date) -> bool:
        return self.listing_date <= as_of and (self.delisting_date is None or self.delisting_date > as_of)


DEFAULT_SECURITY_MASTER = [
    SecurityMasterRecord("AAPL", "Apple Inc.", "NASDAQ", "equity", date(1980, 12, 12)),
    SecurityMasterRecord("MSFT", "Microsoft Corp.", "NASDAQ", "equity", date(1986, 3, 13)),
    SecurityMasterRecord("NVDA", "NVIDIA Corp.", "NASDAQ", "equity", date(1999, 1, 22)),
    SecurityMasterRecord("ENRNQ", "Enron Corp.", "NYSE", "equity", date(1985, 1, 2), date(2001, 12, 2)),
    SecurityMasterRecord("LEHMQ", "Lehman Brothers", "NYSE", "equity", date(1994, 1, 1), date(2008, 9, 15)),
]


class SecurityMasterStore:
    def __init__(self, records: list[SecurityMasterRecord] | None = None):
        self.records = records or DEFAULT_SECURITY_MASTER

    def universe_as_of(self, as_of: date, asset_type: str | None = None) -> list[SecurityMasterRecord]:
        return [
            record
            for record in self.records
            if record.is_member_as_of(as_of) and (asset_type is None or record.asset_type == asset_type)
        ]

    def get(self, symbol: str, as_of: date | None = None) -> SecurityMasterRecord | None:
        for record in self.records:
            if record.symbol == symbol.upper() and (as_of is None or record.is_member_as_of(as_of)):
                return record
        return None


def populate_security_master(db=None) -> dict[str, int]:
    return {"records_available": len(DEFAULT_SECURITY_MASTER)}


def universe_as_of(as_of: date, asset_type: str | None = None) -> list[str]:
    return [record.symbol for record in SecurityMasterStore().universe_as_of(as_of, asset_type)]
