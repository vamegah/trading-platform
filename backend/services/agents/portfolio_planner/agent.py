"""
Financial Planner Orchestrator.

Coordinates portfolio analysis by delegating to specialist agents:
  * InstrumentTagger   - fills missing allocations
  * ReportWriter       - narrative report
  * ChartMaker         - allocation visualizations
  * RetirementSpecialist - Monte Carlo projections

Runs as a Lambda invoked via SQS from the API Gateway when a user submits
a portfolio_analysis job. Uses Bedrock Claude via LiteLLM.
"""
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

import boto3
from agents import RunContextWrapper, function_tool
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")

# Agent Lambda names (configurable per environment)
TAGGER_FUNCTION = os.getenv("TAGGER_FUNCTION", "trading-tagger")
REPORTER_FUNCTION = os.getenv("REPORTER_FUNCTION", "trading-reporter")
CHARTER_FUNCTION = os.getenv("CHARTER_FUNCTION", "trading-charter")
RETIREMENT_FUNCTION = os.getenv("RETIREMENT_FUNCTION", "trading-retirement")
MOCK_LAMBDAS = os.getenv("MOCK_LAMBDAS", "false").lower() == "true"

# Model
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


@dataclass
class PlannerContext:
    """Context passed to planner tools."""
    job_id: str
    clerk_user_id: str


async def invoke_lambda_agent(agent_name: str, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a specialist Lambda and unwrap the standard response envelope."""
    if MOCK_LAMBDAS:
        logger.info("[MOCK] %s payload=%s", agent_name, json.dumps(payload)[:200])
        return {"success": True, "mock": True, "agent": agent_name}

    try:
        logger.info("Invoking %s Lambda: %s", agent_name, function_name)
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        result = json.loads(response["Payload"].read())

        if isinstance(result, dict) and "statusCode" in result and "body" in result:
            body = result["body"]
            if isinstance(body, str):
                try:
                    result = json.loads(body)
                except json.JSONDecodeError:
                    result = {"message": body}
            else:
                result = body

        logger.info("%s completed", agent_name)
        return result

    except Exception as exc:
        logger.exception("Error invoking %s", agent_name)
        return {"error": str(exc)}


def handle_missing_instruments(job_id: str, db) -> None:
    """Ensure all portfolio symbols have allocation data before analysis."""
    logger.info("Planner: checking for instruments missing allocation data")

    job = db.jobs.find_by_id(job_id)
    if not job:
        logger.error("Planner: job %s not found", job_id)
        return

    user_id = job["clerk_user_id"]
    accounts = db.accounts.find_by_user(user_id)

    missing: list[dict] = []
    seen: set[str] = set()
    for account in accounts:
        for position in db.positions.find_by_account(account["id"]):
            symbol = position["symbol"]
            if symbol in seen:
                continue
            seen.add(symbol)

            instrument = db.instruments.find_by_symbol(symbol)
            if not instrument:
                missing.append({"symbol": symbol, "name": ""})
                continue

            if not (
                instrument.get("allocation_regions")
                and instrument.get("allocation_sectors")
                and instrument.get("allocation_asset_class")
            ):
                missing.append({"symbol": symbol, "name": instrument.get("name", "")})

    if not missing:
        logger.info("Planner: all instruments have allocation data")
        return

    logger.info(
        "Planner: found %d instruments needing classification: %s",
        len(missing), [m["symbol"] for m in missing],
    )
    try:
        lambda_client.invoke(
            FunctionName=TAGGER_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"instruments": missing}),
        )
    except Exception:
        logger.exception("Planner: instrument tagging failed")


def load_portfolio_summary(job_id: str, db) -> Dict[str, Any]:
    """Load lightweight portfolio summary used to steer the orchestrator."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    user_id = job["clerk_user_id"]
    user = db.users.find_by_clerk_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    accounts = db.accounts.find_by_user(user_id)
    total_value = 0.0
    total_positions = 0
    total_cash = 0.0

    for account in accounts:
        total_cash += float(account.get("cash_balance") or 0)
        for position in db.positions.find_by_account(account["id"]):
            total_positions += 1
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if instrument and instrument.get("current_price"):
                total_value += float(instrument["current_price"]) * float(position["quantity"])

    total_value += total_cash

    return {
        "total_value": round(total_value, 2),
        "num_accounts": len(accounts),
        "num_positions": total_positions,
        "years_until_retirement": user.get("years_until_retirement") or 30,
        "target_retirement_income": float(user.get("target_retirement_income") or 80000),
    }


# ------------------------------------------------------------------ tools

async def _invoke_reporter(ctx: PlannerContext) -> str:
    result = await invoke_lambda_agent(
        "Reporter", REPORTER_FUNCTION,
        {"job_id": ctx.job_id, "clerk_user_id": ctx.clerk_user_id},
    )
    return "Reporter completed" if "error" not in result else f"Reporter failed: {result['error']}"


async def _invoke_charter(ctx: PlannerContext) -> str:
    result = await invoke_lambda_agent(
        "Charter", CHARTER_FUNCTION,
        {"job_id": ctx.job_id, "clerk_user_id": ctx.clerk_user_id},
    )
    return "Charter completed" if "error" not in result else f"Charter failed: {result['error']}"


async def _invoke_retirement(ctx: PlannerContext) -> str:
    result = await invoke_lambda_agent(
        "Retirement", RETIREMENT_FUNCTION,
        {"job_id": ctx.job_id, "clerk_user_id": ctx.clerk_user_id},
    )
    return "Retirement completed" if "error" not in result else f"Retirement failed: {result['error']}"


@function_tool
async def invoke_reporter(wrapper: RunContextWrapper[PlannerContext]) -> str:
    """Generate the portfolio narrative report."""
    return await _invoke_reporter(wrapper.context)


@function_tool
async def invoke_charter(wrapper: RunContextWrapper[PlannerContext]) -> str:
    """Generate portfolio allocation charts."""
    return await _invoke_charter(wrapper.context)


@function_tool
async def invoke_retirement(wrapper: RunContextWrapper[PlannerContext]) -> str:
    """Calculate retirement projections via Monte Carlo."""
    return await _invoke_retirement(wrapper.context)


def create_agent(job_id: str, clerk_user_id: str, portfolio_summary: Dict[str, Any], db):
    """Build the orchestrator model, tools, prompt, and context."""
    context = PlannerContext(job_id=job_id, clerk_user_id=clerk_user_id)

    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    tools = [invoke_reporter, invoke_charter, invoke_retirement]

    task = (
        f"Job {job_id} for user {clerk_user_id}. "
        f"{portfolio_summary['num_positions']} positions across "
        f"{portfolio_summary['num_accounts']} accounts. "
        f"Retirement horizon: {portfolio_summary['years_until_retirement']} years, "
        f"target income ${portfolio_summary['target_retirement_income']:,.0f}.\n\n"
        f"Call the appropriate agents in this order:\n"
        f"  1. invoke_reporter   (always, if positions > 0)\n"
        f"  2. invoke_charter    (if positions >= 2)\n"
        f"  3. invoke_retirement (if retirement goals exist)\n"
        f"Respond with 'Done' when finished."
    )

    return model, tools, task, context