#!/usr/bin/env python3
"""Package, deploy, and test the InstrumentTagger end-to-end."""
import json
import os
import subprocess
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

from db import Database

FUNCTION_NAME = os.getenv("TAGGER_FUNCTION", "trading-tagger")
REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")


def _run(cmd, cwd=None):
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(1)
    return r.stdout


def main() -> int:
    here = Path(__file__).parent
    zip_path = here / "tagger_lambda.zip"

    _run(["uv", "run", "package_docker.py"], cwd=here)

    if not zip_path.exists():
        print("Package missing")
        return 1

    account = boto3.client("sts").get_caller_identity()["Account"]
    bucket = f"trading-lambda-packages-{account}"
    key = f"tagger/{zip_path.name}"

    s3 = boto3.client("s3", region_name=REGION)
    with open(zip_path, "rb") as f:
        s3.upload_fileobj(f, bucket, key)
    print(f"Uploaded to s3://{bucket}/{key}")

    lambda_client = boto3.client("lambda", region_name=REGION)
    lambda_client.update_function_code(
        FunctionName=FUNCTION_NAME, S3Bucket=bucket, S3Key=key
    )
    lambda_client.get_waiter("function_updated").wait(FunctionName=FUNCTION_NAME)

    time.sleep(5)

    test_instruments = [
        {"symbol": "ARKK", "name": "ARK Innovation ETF", "instrument_type": "etf"},
        {"symbol": "SOFI", "name": "SoFi Technologies Inc", "instrument_type": "stock"},
        {"symbol": "TSLA", "name": "Tesla Inc", "instrument_type": "stock"},
    ]
    resp = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"instruments": test_instruments}),
    )
    body = json.loads(resp["Payload"].read())
    print("Response:", json.dumps(body, indent=2)[:500])

    db = Database()
    for inst in test_instruments:
        instrument = db.instruments.find_by_symbol(inst["symbol"])
        status = "ok" if (instrument and instrument.get("allocation_asset_class")) else "missing"
        print(f"  {inst['symbol']}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())