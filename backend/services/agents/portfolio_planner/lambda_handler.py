"""
Financial Planner Orchestrator Lambda handler.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, UTC

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
from templates import ORCHESTRATOR_INSTRUCTIONS
from agent import (
    PlannerContext,
    create_agent,
    handle_missing_instruments,
    load_portfolio_summary,
)
from market import update_instrument_prices
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = Database()

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
events_client = boto3.client("events") if EVENT_BUS_NAME else None


def _emit_event(detail_type: str, detail: dict) -> None:
    if not events_client:
        return
    try:
        events_client.put_events(Entries=[{
            "Source": "trading.planner",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME,
        }])
    except Exception:
        logger.exception("Failed to emit event %s", detail_type)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda s: logger.info(
        "Planner: rate limit hit, retrying in %ss", s.next_action.sleep
    ),
)
async def run_orchestrator(job_id: str) -> None:
    """Run the orchestrator end-to-end."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    clerk_user_id = job["clerk_user_id"]

    try:
        db.jobs.update_status(job_id, "running")
        _emit_event("analysis.job.started", {"job_id": job_id, "clerk_user_id": clerk_user_id})

        # 1. Ensure instruments are classified
        await asyncio.to_thread(handle_missing_instruments, job_id, db)

        # 2. Refresh prices from market data
        logger.info("Planner: updating instrument prices")
        await asyncio.to_thread(update_instrument_prices, job_id, db)

        # 3. Load summary
        portfolio_summary = await asyncio.to_thread(load_portfolio_summary, job_id, db)

        # 4. Create agent and run
        model, tools, task, context = create_agent(job_id, clerk_user_id, portfolio_summary, db)

        with trace("Planner Orchestrator"):
            agent = Agent[PlannerContext](
                name="Financial Planner",
                instructions=ORCHESTRATOR_INSTRUCTIONS,
                model=model,
                tools=tools,
            )
            await Runner.run(agent, input=task, context=context, max_turns=20)

        db.jobs.update_status(job_id, "completed")
        _emit_event("analysis.job.completed", {"job_id": job_id, "clerk_user_id": clerk_user_id})
        logger.info("Planner: job %s completed", job_id)

    except Exception as exc:
        logger.exception("Planner: orchestration failed for %s", job_id)
        db.jobs.update_status(job_id, "failed", error_message=str(exc))
        _emit_event("analysis.job.failed", {
            "job_id": job_id,
            "clerk_user_id": clerk_user_id,
            "error": str(exc),
        })
        raise


def lambda_handler(event, context):
    """SQS-triggered or direct-invocation entry point."""
    with observe():
        try:
            logger.info("Planner invoked: %s", json.dumps(event)[:500])

            job_id = None
            if "Records" in event and event["Records"]:
                body = event["Records"][0]["body"]
                if isinstance(body, str) and body.startswith("{"):
                    try:
                        job_id = json.loads(body).get("job_id")
                    except json.JSONDecodeError:
                        pass
                job_id = job_id or body
            elif "job_id" in event:
                job_id = event["job_id"]

            if not job_id:
                return {"statusCode": 400, "body": json.dumps({"error": "No job_id"})}

            logger.info("Planner: starting job %s", job_id)
            asyncio.run(run_orchestrator(job_id))

            return {
                "statusCode": 200,
                "body": json.dumps({"success": True, "job_id": job_id}),
            }

        except Exception as exc:
            logger.exception("Planner handler failed")
            return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(exc)})}


def health_check():
    """Return a health payload; used by M10 verification and readiness probes."""
    return {
        "service": "portfolio_planner",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "model": BEDROCK_MODEL_ID if (BEDROCK_MODEL_ID := os.getenv("BEDROCK_MODEL_ID")) else None,
        "tagger": os.getenv("TAGGER_FUNCTION"),
        "reporter": os.getenv("REPORTER_FUNCTION"),
        "charter": os.getenv("CHARTER_FUNCTION"),
        "retirement": os.getenv("RETIREMENT_FUNCTION"),
        "events_configured": bool(EVENT_BUS_NAME),
    }


# Local smoke test
if __name__ == "__main__":
    from schemas import JobCreate, UserCreate

    test_user_id = "test_user_planner_local"
    if not db.users.find_by_clerk_id(test_user_id):
        db.users.create_user(clerk_user_id=test_user_id, display_name="Test Planner User")

    job = db.jobs.create_job(
        clerk_user_id=test_user_id,
        job_type="portfolio_analysis",
        request_payload={"analysis_type": "comprehensive", "test": True},
    )
    print(f"Created test job: {job}")
    print(json.dumps(lambda_handler({"job_id": job}, None), indent=2))