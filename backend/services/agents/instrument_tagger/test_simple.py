#!/usr/bin/env python3
"""Local smoke test for the InstrumentTagger."""
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from db import Database
from lambda_handler import lambda_handler


def main() -> int:
    event = {
        "instruments": [
            {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "instrument_type": "etf"},
            {"symbol": "BND", "name": "Vanguard Total Bond Market ETF", "instrument_type": "bond_fund"},
            {"symbol": "AAPL", "name": "Apple Inc.", "instrument_type": "stock"},
        ],
    }

    result = lambda_handler(event, None)
    print("status:", result["statusCode"])

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print("tagged:", body.get("tagged"))
        print("updated:", body.get("updated"))
        print("errors:", body.get("errors"))

        db = Database()
        for symbol in body.get("updated", []):
            instrument = db.instruments.find_by_symbol(symbol)
            if instrument:
                print(f"  {symbol}: source={instrument.get('source')} "
                      f"asset={instrument.get('allocation_asset_class')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())