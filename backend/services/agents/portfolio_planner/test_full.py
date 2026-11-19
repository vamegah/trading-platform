#!/usr/bin/env python3
"""
End-to-end test for the Planner orchestrator via SQS.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, UTC

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from db import Database

QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "trading-analysis-jobs")
TIMEOUT_SECONDS = int(os.getenv("PLANNER_TEST_TIMEOUT", "180"))


def queue_url(sqs) -> str:
    urls = sqs.list_queues(QueueNamePrefix=QUEUE_NAME).get("QueueUrls", [])
    for u in urls:
        if QUEUE_NAME in u:
            return u
    raise RuntimeError(f"Queue {QUEUE_NAME} not found")


def main() -> int:
    print("Planner E2E test")
    print("=" * 60)

    db = Database()
    sqs = boto3.client("sqs")
    sts = boto3.client("sts")

    print(f"AWS account: {sts.get_caller_identity()['Account']}")
    print(f"Bedrock region: {os.getenv('BEDROCK_REGION', 'us-west-2')}")

    test_user_id = "test_user_001"
    if not db.users.find_by_clerk_id(test_user_id):
        print("Test user missing. Run: cd backend/db && uv run reset_db.py --dev --with-test-data")
        return 1

    job_id = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={
            "analysis_type": "full",
            "requested_at": datetime.now(UTC).isoformat(),
            "test_run": True,
        },
    )
    print(f"Created job {job_id}")

    q = queue_url(sqs)
    sqs.send_message(QueueUrl=q, MessageBody=json.dumps({"job_id": job_id}))
    print(f"Sent to {q}")

    start = time.time()
    last = None
    while time.time() - start < TIMEOUT_SECONDS:
        job = db.jobs.find_by_id(job_id)
        status = job["status"]
        if status != last:
            print(f"[{int(time.time() - start):3d}s] {status}")
            last = status

        if status == "completed":
            print("Job completed")
            _print_results(job)
            return 0
        if status == "failed":
            print(f"Job failed: {job.get('error_message')}")
            return 1

        time.sleep(2)

    print("Timed out")
    return 1


def _print_results(job: dict) -> None:
    print("\nResults:")
    if job.get("report_payload"):
        length = len(job["report_payload"].get("analysis", ""))
        print(f"  report: {length} chars")
    if job.get("charts_payload"):
        print(f"  charts: {len(job['charts_payload'])}")
    if job.get("retirement_payload"):
        ret = job["retirement_payload"]
        print(f"  retirement success rate: {ret.get('success_rate')}%")
        print(f"  projected value: ${ret.get('projected_value', 0):,.0f}")


if __name__ == "__main__":
    sys.exit(main())