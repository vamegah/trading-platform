"""
Report Writer Lambda handler.

Input:  {"job_id": "<uuid>"}   (portfolio loaded from DB)
        or {"job_id": ..., "portfolio_data": {...}, "user_data": {...}}

Output: {"statusCode": 200, "body": {"success": true, "report_id": ...}}
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
from templates import REPORTER_INSTRUCTIONS
from agent import (
    BEDROCK_MODEL_ID,
    SAGEMAKER_ENDPOINT,
    VECTOR_BUCKET,
    ReporterContext,
    create_agent,
)
from judge import evaluate
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GUARD_AGAINST_SCORE = float(os.getenv("REPORTER_MIN_SCORE", "0.3"))

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
events_client = boto3.client("events") if EVENT_BUS_NAME else None


def _emit(detail_type: str, detail: dict) -> None:
    if not events_client:
        return
    try:
        events_client.put_events(Entries=[{
            "Source": "trading.reporter",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME,
        }])
    except Exception:
        logger.exception("Reporter: failed to emit %s", detail_type)


def _load_portfolio_from_db(db: Database, job_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Build portfolio_data and user_data from the platform database."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    user_id = job["clerk_user_id"]
    user = db.users.find_by_clerk_id(user_id) or {}
    accounts = db.accounts.find_by_user(user_id)

    portfolio_data = {"user_id": user_id, "job_id": job_id, "accounts": []}
    for account in accounts:
        account_data = {
            "id": account["id"],
            "name": account.get("account_name", "Account"),
            "cash_balance": float(account.get("cash_balance") or 0),
            "positions": [],
        }
        for position in db.positions.find_by_account(account["id"]):
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if not instrument:
                continue
            account_data["positions"].append({
                "symbol": position["symbol"],
                "quantity": float(position["quantity"]),
                "instrument": instrument,
            })
        portfolio_data["accounts"].append(account_data)

    user_data = {
        "years_until_retirement": user.get("years_until_retirement") or 30,
        "target_retirement_income": float(user.get("target_retirement_income") or 80000),
    }
    return portfolio_data, user_data


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda s: logger.info("Reporter: rate limit, retrying in %ss", s.next_action.sleep),
)
async def run_reporter_agent(
    job_id: str,
    clerk_user_id: str,
    portfolio_data: Dict[str, Any],
    user_data: Dict[str, Any],
    db: Database,
    observability=None,
) -> Dict[str, Any]:
    model, tools, task, context = create_agent(
        job_id=job_id,
        clerk_user_id=clerk_user_id,
        portfolio_data=portfolio_data,
        user_data=user_data,
        db=db,
    )

    with trace("Reporter Agent"):
        agent = Agent[ReporterContext](
            name="Report Writer",
            instructions=REPORTER_INSTRUCTIONS,
            model=model,
            tools=tools,
        )
        result = await Runner.run(agent, input=task, context=context, max_turns=10)
        markdown = result.final_output

    # Optional LLM judge
    if observability is not None:
        try:
            with observability.start_as_current_span(name="judge") as span:
                evaluation = await evaluate(REPORTER_INSTRUCTIONS, task, markdown)
                score = evaluation.score / 100
                span.score(name="Judge", value=score, data_type="NUMERIC", comment=evaluation.feedback)
                if score < GUARD_AGAINST_SCORE:
                    logger.error("Reporter: quality guard triggered (score=%.2f)", score)
                    raise RuntimeError(f"Report quality below threshold: {score:.2f}")
        except RuntimeError:
            raise
        except Exception:
            logger.exception("Reporter: judge failed; continuing")

    payload = {
        "markdown": markdown,
        "generated_at": datetime.now(UTC).isoformat(),
        "agent": "report_writer",
        "metrics": _summary_metrics(portfolio_data),
    }

    db.jobs.update_report(job_id, payload)
    return {"success": True, "report_length": len(markdown)}


def _summary_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a compact metrics block saved alongside the narrative."""
    total = 0.0
    cash = 0.0
    positions = 0
    for acc in portfolio_data.get("accounts", []):
        cash += float(acc.get("cash_balance") or 0)
        for p in acc.get("positions", []):
            positions += 1
            inst = p.get("instrument") or {}
            if inst.get("current_price"):
                total += float(p.get("quantity") or 0) * float(inst["current_price"])
    return {
        "total_value": round(total + cash, 2),
        "cash": round(cash, 2),
        "num_positions": positions,
    }


def lambda_handler(event, context):
    with observe() as observability:
        try:
            logger.info("Reporter invoked: %s", json.dumps(event)[:500])

            if isinstance(event, str):
                event = json.loads(event)

            job_id = event.get("job_id")
            if not job_id:
                return {"statusCode": 400, "body": json.dumps({"error": "job_id required"})}

            db = Database()
            clerk_user_id = event.get("clerk_user_id")
            portfolio_data = event.get("portfolio_data")
            user_data = event.get("user_data")

            if not portfolio_data or not user_data:
                portfolio_data, user_data = _load_portfolio_from_db(db, job_id)
                clerk_user_id = clerk_user_id or portfolio_data["user_id"]

            _emit("analysis.report.started", {"job_id": job_id, "clerk_user_id": clerk_user_id})

            result = asyncio.run(run_reporter_agent(
                job_id=job_id,
                clerk_user_id=clerk_user_id,
                portfolio_data=portfolio_data,
                user_data=user_data,
                db=db,
                observability=observability,
            ))

            _emit("analysis.report.completed", {
                "job_id": job_id,
                "clerk_user_id": clerk_user_id,
                "report_length": result.get("report_length"),
            })

            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as exc:
            logger.exception("Reporter failed")
            _emit("analysis.report.failed", {"error": str(exc)})
            return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(exc)})}


def health_check() -> Dict[str, Any]:
    """Health payload for M10 evidence and readiness probes."""
    return {
        "service": "report_writer",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "model": BEDROCK_MODEL_ID,
        "knowledge_base_configured": bool(VECTOR_BUCKET and SAGEMAKER_ENDPOINT),
        "events_configured": bool(EVENT_BUS_NAME),
    }


# Local smoke test
if __name__ == "__main__":

    db = Database()
    job_id = db.jobs.create_job(
        clerk_user_id="test_user_001",
        job_type="portfolio_analysis",
        request_payload={"test": True},
    )
    print(json.dumps(lambda_handler({"job_id": job_id}, None), indent=2))