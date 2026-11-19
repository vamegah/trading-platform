#!/usr/bin/env python3
"""Local smoke test for the Retirement Specialist."""
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

    event = {
        "job_id": job_id,
        "portfolio_data": {
            "accounts": [{
                "name": "401(k)",
                "type": "retirement",
                "cash_balance": 10000,
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
                    {
                        "symbol": "BND",
                        "quantity": 100,
                        "instrument": {
                            "name": "Vanguard Total Bond Market ETF",
                            "current_price": 75,
                            "allocation_asset_class": {"fixed_income": 100},
                        },
                    },
                ],
            }],
        },
    }

    result = lambda_handler(event, None)
    print("status:", result["statusCode"])

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print("success_rate:", body.get("success_rate"))
        print("analysis length:", body.get("analysis_length"))

        job = db.jobs.find_by_id(job_id)
        payload = (job or {}).get("retirement_payload") or {}
        structured = payload.get("structured", {})
        mc = structured.get("monte_carlo", {})
        print("monte_carlo:", json.dumps(mc, indent=2))
        print("projections:", len(structured.get("projections", [])))

    db.jobs.delete(job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())