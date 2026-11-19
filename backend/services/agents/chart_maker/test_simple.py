#!/usr/bin/env python3
"""Local smoke test for the Chart Maker."""
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from db import Database
from schemas import JobCreate
from lambda_handler import lambda_handler


def main() -> int:
    db = Database()
    job_id = db.jobs.create_job(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    print("Created job:", job_id)

    event = {
        "job_id": job_id,
        "portfolio_data": {
            "accounts": [{
                "name": "401(k)",
                "type": "401k",
                "cash_balance": 5000,
                "positions": [{
                    "symbol": "SPY",
                    "quantity": 100,
                    "instrument": {
                        "name": "SPDR S&P 500 ETF",
                        "current_price": 450,
                        "allocation_asset_class": {"equity": 100},
                        "allocation_regions": {"north_america": 100},
                        "allocation_sectors": {
                            "technology": 30, "healthcare": 15,
                            "financials": 15, "consumer_discretionary": 20,
                            "industrials": 20,
                        },
                    },
                }],
            }],
        },
    }

    result = lambda_handler(event, None)
    print("status:", result["statusCode"])

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print("success:", body.get("success"), "charts:", body.get("charts_generated"))

        job = db.jobs.find_by_id(job_id)
        payload = (job or {}).get("charts_payload") or {}
        for key, chart in payload.items():
            print(f"  {key}: {chart.get('title')} ({chart.get('type')})")
            for pt in chart.get("data", []):
                print(f"    - {pt['name']}: ${pt['value']:,.2f}")

    db.jobs.delete(job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())