#!/usr/bin/env python3
"""Simple local test for the Report Writer."""
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from db import Database  # noqa: E402
from lambda_handler import lambda_handler  # noqa: E402


def main() -> int:
    db = Database()
    job_id = db.jobs.create_job(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    print("Created job:", job_id)

    test_event = {
        "job_id": job_id,
        "portfolio_data": {
            "accounts": [{
                "name": "401(k)",
                "cash_balance": 5000,
                "positions": [
                    {
                        "symbol": "SPY",
                        "quantity": 100,
                        "instrument": {
                            "name": "SPDR S&P 500 ETF",
                            "current_price": 450,
                            "allocation_asset_class": {"equity": 100},
                        },
                    },
                ],
            }],
        },
        "user_data": {"years_until_retirement": 25, "target_retirement_income": 75000},
    }

    result = lambda_handler(test_event, None)
    print(f"status={result['statusCode']}")

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print("success:", body.get("success"), "length:", body.get("report_length"))

        job = db.jobs.find_by_id(job_id)
        payload = (job or {}).get("report_payload") or {}
        md = payload.get("markdown", "")
        print("stored markdown length:", len(md))
        print("first 300 chars:\n", md[:300])

    db.jobs.delete(job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())