#!/usr/bin/env python3
"""
Seed instruments for the trading platform.

Uses upsert semantics so re-runs are idempotent and do not clash with
instruments populated by InstrumentTagger.
"""
import json
import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import InstrumentCreate

load_dotenv(override=True)

CLUSTER_ARN = os.environ.get("AURORA_CLUSTER_ARN")
SECRET_ARN = os.environ.get("AURORA_SECRET_ARN")
DATABASE = os.environ.get("AURORA_DATABASE", "trading")
REGION = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not CLUSTER_ARN or not SECRET_ARN:
    raise SystemExit("Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN")

client = boto3.client("rds-data", region_name=REGION)


INSTRUMENTS = [
    # ... same list as your original (22 ETFs) ...
]


def _upsert(instrument: InstrumentCreate) -> bool:
    v = instrument.model_dump()
    sql = """
        INSERT INTO instruments (
            symbol, name, instrument_type, current_price,
            allocation_regions, allocation_sectors, allocation_asset_class,
            source, last_updated
        ) VALUES (
            :symbol, :name, :itype, :price::numeric,
            :ar::jsonb, :as::jsonb, :aa::jsonb, 'seed', NOW()
        )
        ON CONFLICT (symbol) DO UPDATE SET
            name = EXCLUDED.name,
            instrument_type = EXCLUDED.instrument_type,
            current_price = EXCLUDED.current_price,
            allocation_regions = EXCLUDED.allocation_regions,
            allocation_sectors = EXCLUDED.allocation_sectors,
            allocation_asset_class = EXCLUDED.allocation_asset_class,
            last_updated = NOW()
    """
    params = [
        {"name": "symbol", "value": {"stringValue": v["symbol"]}},
        {"name": "name", "value": {"stringValue": v["name"]}},
        {"name": "itype", "value": {"stringValue": v["instrument_type"]}},
        {"name": "price", "value": {"stringValue": str(v.get("current_price") or 0)}},
        {"name": "ar", "value": {"stringValue": json.dumps(v["allocation_regions"])}},
        {"name": "as", "value": {"stringValue": json.dumps(v["allocation_sectors"])}},
        {"name": "aa", "value": {"stringValue": json.dumps(v["allocation_asset_class"])}},
    ]
    try:
        client.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
            database=DATABASE, sql=sql, parameters=params,
        )
        return True
    except ClientError as exc:
        print(f"  Error: {exc.response['Error']['Message'][:120]}")
        return False


def main() -> None:
    print(f"Seeding {len(INSTRUMENTS)} instruments")

    validated: list[InstrumentCreate] = []
    for inst in INSTRUMENTS:
        try:
            validated.append(InstrumentCreate(**inst))
        except ValidationError as exc:
            print(f"  Invalid: {inst.get('symbol')}: {exc.errors()[:1]}")

    ok = 0
    for inst in validated:
        if _upsert(inst):
            ok += 1

    print(f"Loaded {ok}/{len(validated)} instruments")

    response = client.execute_statement(
        resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN, database=DATABASE,
        sql="SELECT COUNT(*) FROM instruments",
    )
    print(f"Table now contains {response['records'][0][0]['longValue']} instruments")


if __name__ == "__main__":
    main()