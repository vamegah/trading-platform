#!/usr/bin/env python3
"""Full E2E test through the deployed Lambda."""
import json
import time

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

from db import Database

FUNCTION_NAME = "trading-retirement"


def main() -> int:
    db = Database()
    client = boto3.client("lambda")

    job_id = db.jobs.create_job(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    print("Created job:", job_id)

    resp = client.invoke(
        FunctionName=FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps({"job_id": job_id}),
    )
    body = json.loads(resp["Payload"].read())
    print("Lambda response:", json.dumps(body, indent=2)[:500])

    time.sleep(2)
    job = db.jobs.find_by_id(job_id)
    payload = (job or {}).get("retirement_payload") or {}

    if not payload:
        print("No retirement payload stored")
        db.jobs.delete(job_id)
        return 1

    structured = payload.get("structured", {})
    print("success rate:", structured.get("monte_carlo", {}).get("success_rate"))
    print("projections:", len(structured.get("projections", [])))
    db.jobs.delete(job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())