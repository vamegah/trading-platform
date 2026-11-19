#!/usr/bin/env python3
"""Full E2E test of the InstrumentTagger through Lambda."""
import json

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

from db import Database  # noqa: E402

FUNCTION_NAME = "trading-tagger"


def main() -> int:
    db = Database()
    client = boto3.client("lambda")

    test_instruments = [
        {"symbol": "ARKK", "name": "ARK Innovation ETF", "instrument_type": "etf"},
        {"symbol": "SOFI", "name": "SoFi Technologies Inc", "instrument_type": "stock"},
        {"symbol": "TSLA", "name": "Tesla Inc", "instrument_type": "stock"},
    ]

    resp = client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"instruments": test_instruments}),
    )
    body = json.loads(resp["Payload"].read())
    print("Lambda response:", json.dumps(body, indent=2)[:500])

    for inst in test_instruments:
        instrument = db.instruments.find_by_symbol(inst["symbol"])
        if instrument and instrument.get("allocation_asset_class"):
            print(f"  {inst['symbol']}: tagged (source={instrument.get('source')})")
        else:
            print(f"  {inst['symbol']}: NOT tagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())