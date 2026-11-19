"""
Retirement Specialist Lambda handler.
"""
import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict

import boto3
from agents import Agent, Runner, trace
from litellm.exceptions import RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from db import Database
from templates import RETIREMENT_INSTRUCTIONS
from agent import create_agent
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
events_client = boto3.client("events") if EVENT_BUS_NAME else None


class AgentTemporaryError(Exception):
    """Raised for retryable agent failures."""


def _emit(detail_type: str, detail: dict) -> None:
    if not events_client:
        return
    try:
        events_client.put_events(Entries=[{
            "Source": "trading.retirement_specialist",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME,
        }])
    except Exception:
        logger.exception("Retirement: failed to emit %s", detail_type)


def get_user_preferences(db: Database, job_id: str) -> Dict[str, Any]:
    """Load user retirement preferences from the platform DB."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        return {"years_until_retirement": 30, "target_retirement_income": 80000.0, "current_age": 40}

    user = db.users.find_by_clerk_id(job["clerk_user_id"]) or {}
    return {
        "years_until_retirement": user.get("years_until_retirement") or 30,
        "target_retirement_income": float(user.get("target_retirement_income") or 80000),
        "current_age": int(user.get("current_age") or 40),
    }


def _load_portfolio_from_db(db: Database, job_id: str) -> Dict[str, Any]:
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    user_id = job["clerk_user_id"]
    portfolio = {"user_id": user_id, "job_id": job_id, "accounts": []}
    for account in db.accounts.find_by_user(user_id):
        account_data = {
            "id": account["id"],
            "name": account.get("account_name", "Account"),
            "type": account.get("account_type") or "investment",
            "cash_balance": float(account.get("cash_balance") or 0),
            "positions": [],
        }
        for position in db.positions.find_by_account(account["id"]):
            inst = db.instruments.find_by_symbol(position["symbol"])
            if not inst:
                continue
            account_data["positions"].append({
                "symbol": position["symbol"],
                "quantity": float(position["quantity"]),
                "instrument": inst,
            })
        portfolio["accounts"].append(account_data)
    return portfolio


@retry(
    retry=retry_if_exception_type((RateLimitError, AgentTemporaryError, TimeoutError, asyncio.TimeoutError)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda s: logger.info("Retirement: retrying in %ss", s.next_action.sleep),
)
async def run_retirement_agent(
    job_id: str,
    clerk_user_id: str,
    portfolio_data: Dict[str, Any],
    db: Database,
) -> Dict[str, Any]:
    user_preferences = get_user_preferences(db, job_id)

    model, task, structured = create_agent(
        job_id=job_id,
        clerk_user_id=clerk_user_id,
        portfolio_data=portfolio_data,
        user_preferences=user_preferences,
        db=db,
    )

    with trace("Retirement Agent"):
        agent = Agent(
            name="Retirement Specialist",
            instructions=RETIREMENT_INSTRUCTIONS,
            model=model,
        )
        try:
            result = await Runner.run(agent, input=task, max_turns=10)
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise AgentTemporaryError(f"timeout: {exc}") from exc

    payload = {
        "analysis": result.final_output,
        "structured": structured,
        "generated_at": datetime.now(UTC).isoformat(),
        "agent": "retirement_specialist",
    }

    db.jobs.update_retirement(job_id, payload)

    # Also persist a snapshot for trend tracking
    try:
        db.client.insert("retirement_projections", {
            "clerk_user_id": clerk_user_id,
            "target_income": structured["target_annual_income"],
            "years_until_retirement": structured["years_until_retirement"],
            "success_probability": structured["monte_carlo"]["success_rate"] / 100.0,
            "projection_data": structured["projections"],
        })
    except Exception:
        logger.exception("Retirement: snapshot persist failed (non-blocking)")

    return {
        "success": True,
        "success_rate": structured["monte_carlo"]["success_rate"],
        "analysis_length": len(result.final_output),
    }


def lambda_handler(event, context):
    with observe():
        try:
            logger.info("Retirement invoked: %s", json.dumps(event)[:500])

            if isinstance(event, str):
                event = json.loads(event)

            job_id = event.get("job_id")
            if not job_id:
                return {"statusCode": 400, "body": json.dumps({"error": "job_id required"})}

            db = Database()
            job = db.jobs.find_by_id(job_id)
            if not job:
                return {"statusCode": 404, "body": json.dumps({"error": f"job {job_id} not found"})}

            clerk_user_id = job["clerk_user_id"]
            portfolio_data = event.get("portfolio_data") or _load_portfolio_from_db(db, job_id)

            _emit("analysis.retirement.started", {"job_id": job_id, "clerk_user_id": clerk_user_id})

            result = asyncio.run(run_retirement_agent(job_id, clerk_user_id, portfolio_data, db))

            _emit("analysis.retirement.completed", {
                "job_id": job_id,
                "clerk_user_id": clerk_user_id,
                "success_rate": result.get("success_rate"),
            })
            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as exc:
            logger.exception("Retirement failed")
            _emit("analysis.retirement.failed", {"error": str(exc)})
            return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(exc)})}


def health_check() -> Dict[str, Any]:
    """Health payload for M10 evidence and readiness probes."""
    return {
        "service": "retirement_specialist",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "model": BEDROCK_MODEL_ID,
        "simulations": DEFAULT_NUM_SIMULATIONS,
        "events_configured": bool(EVENT_BUS_NAME),
    }


# Local smoke test
if __name__ == "__main__":
    from db import Database
    db = Database()
    job_id = db.jobs.create_job(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    print(json.dumps(lambda_handler({"job_id": job_id}, None), indent=2))