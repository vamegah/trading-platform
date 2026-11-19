#!/usr/bin/env python3
"""Simple integration test for the Planner orchestrator (mocked specialists)."""
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)
os.environ["MOCK_LAMBDAS"] = "true"

from db import Database  # noqa: E402


def setup_job() -> str:
    """Ensure the test user exists, then create a fresh job."""
    db = Database()
    test_user_id = "test_user_001"

    if not db.users.find_by_clerk_id(test_user_id):
        raise SystemExit(
            "Test user missing. Run: cd backend/db && uv run reset_db.py --dev --with-test-data"
        )

    job_id = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={"analysis_type": "comprehensive", "test": True},
    )
    print(f"Created job {job_id}")
    return job_id


def run() -> int:
    job_id = setup_job()

    from lambda_handler import lambda_handler

    result = lambda_handler({"job_id": job_id}, None)
    status = result.get("statusCode")
    body = json.loads(result.get("body", "{}"))
    print(f"status={status} success={body.get('success')}")

    if status != 200:
        print(f"Error: {body}")
        return 1

    db = Database()
    job = db.jobs.find_by_id(job_id)
    print(f"final status: {job['status']}")
    return 0 if job["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(run())