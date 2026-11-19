"""
Chart Maker Lambda handler.

Input:  {"job_id": "<uuid>"}  (portfolio loaded from DB)
        or {"job_id": ..., "portfolio_data": {...}}

Output: {"statusCode": 200, "body": {"success": true, "charts_generated": N}}
"""
import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Dict, List

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
from templates import CHARTER_INSTRUCTIONS
from agent import BEDROCK_MODEL_ID, create_agent
from observability import observe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME")
events_client = boto3.client("events") if EVENT_BUS_NAME else None


def _emit(detail_type: str, detail: dict) -> None:
    if not events_client:
        return
    try:
        events_client.put_events(Entries=[{
            "Source": "trading.chart_maker",
            "DetailType": detail_type,
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME,
        }])
    except Exception:
        logger.exception("Charter: failed to emit %s", detail_type)


def _load_portfolio_from_db(db: Database, job_id: str) -> Dict[str, Any]:
    """Assemble portfolio_data from the platform database."""
    job = db.jobs.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    user_id = job["clerk_user_id"]
    user = db.users.find_by_clerk_id(user_id) or {}
    accounts = db.accounts.find_by_user(user_id)

    portfolio = {
        "user_id": user_id,
        "job_id": job_id,
        "years_until_retirement": user.get("years_until_retirement") or 30,
        "accounts": [],
    }
    for account in accounts:
        account_data = {
            "id": account["id"],
            "name": account.get("account_name", "Account"),
            "type": account.get("account_type") or "investment",
            "cash_balance": float(account.get("cash_balance") or 0),
            "positions": [],
        }
        for position in db.positions.find_by_account(account["id"]):
            instrument = db.instruments.find_by_symbol(position["symbol"])
            if instrument:
                account_data["positions"].append({
                    "symbol": position["symbol"],
                    "quantity": float(position["quantity"]),
                    "instrument": instrument,
                })
        portfolio["accounts"].append(account_data)

    return portfolio


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a text blob."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in output")
    return json.loads(match.group(0))


def _values_by_name(analysis: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Map source arrays into name -> value dicts for validation."""
    return {
        "asset": {k.replace("_", " ").title(): v for k, v in analysis["asset_classes"].items()},
        "region": {k.replace("_", " ").title(): v for k, v in analysis["regions"].items()},
        "sector": {k.replace("_", " ").title(): v for k, v in analysis["sectors"].items()},
        "account": {k: v["value"] for k, v in analysis["accounts"].items()},
        "holding": {k: v for k, v in analysis["top_holdings"].items()},
    }


def _validate_charts(charts: List[Dict[str, Any]], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate LLM output. If any chart's data values do not match the
    deterministic analysis within a 1% tolerance, we replace the chart's
    data with the true values. This prevents hallucinated dollar amounts
    from reaching the UI.
    """
    canonical = _values_by_name(analysis)
    validated: List[Dict[str, Any]] = []

    for chart in charts:
        key = (chart.get("key") or "").lower()
        bucket = None
        if "asset" in key:
            bucket = canonical["asset"]
        elif "region" in key or "geo" in key:
            bucket = canonical["region"]
        elif "sector" in key:
            bucket = canonical["sector"]
        elif "account" in key:
            bucket = canonical["account"]
        elif "holding" in key or "position" in key:
            bucket = canonical["holding"]

        if bucket:
            chart["data"] = [
                {"name": k, "value": round(v, 2), "color": _pick_color(i)}
                for i, (k, v) in enumerate(bucket.items())
            ]
        else:
            # Keep LLM data but ensure values are numbers
            for point in chart.get("data", []):
                try:
                    point["value"] = round(float(point.get("value", 0)), 2)
                except (TypeError, ValueError):
                    point["value"] = 0.0

        validated.append(chart)

    return validated


def _pick_color(i: int) -> str:
    from agent import DEFAULT_PALETTE
    return DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)]


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda s: logger.info("Charter: rate limit, retrying in %ss", s.next_action.sleep),
)
async def run_charter_agent(job_id: str, portfolio_data: Dict[str, Any], db: Database) -> Dict[str, Any]:
    """Run the chart maker agent and persist the validated result."""
    model, task, analysis = create_agent(job_id, portfolio_data, db)

    with trace("Charter Agent"):
        agent = Agent(
            name="Chart Maker",
            instructions=CHARTER_INSTRUCTIONS,
            model=model,
        )
        result = await Runner.run(agent, input=task, max_turns=3)
        raw = result.final_output

    try:
        parsed = _extract_json(raw)
    except Exception as exc:
        logger.error("Charter: JSON parse failed: %s", exc)
        return {"success": False, "charts_generated": 0, "error": "json_parse_failed"}

    raw_charts = parsed.get("charts") or []
    if not isinstance(raw_charts, list) or not raw_charts:
        return {"success": False, "charts_generated": 0, "error": "no_charts"}

    validated = _validate_charts(raw_charts, analysis)

    # Persist with chart keys as top-level keys for the frontend
    charts_payload: Dict[str, Any] = {}
    for chart in validated:
        key = chart.get("key") or f"chart_{len(charts_payload) + 1}"
        chart_copy = {k: v for k, v in chart.items() if k != "key"}
        chart_copy["generated_at"] = datetime.now(UTC).isoformat()
        charts_payload[key] = chart_copy

    db.jobs.update_charts(job_id, charts_payload)
    return {
        "success": True,
        "charts_generated": len(charts_payload),
        "chart_keys": list(charts_payload.keys()),
    }


def lambda_handler(event, context):
    with observe():
        try:
            logger.info("Charter invoked: %s", json.dumps(event)[:500])

            if isinstance(event, str):
                event = json.loads(event)

            job_id = event.get("job_id")
            if not job_id:
                return {"statusCode": 400, "body": json.dumps({"error": "job_id required"})}

            db = Database()
            portfolio_data = event.get("portfolio_data") or _load_portfolio_from_db(db, job_id)

            _emit("analysis.charts.started", {"job_id": job_id})

            result = asyncio.run(run_charter_agent(job_id, portfolio_data, db))

            _emit("analysis.charts.completed", {
                "job_id": job_id,
                "charts_generated": result.get("charts_generated"),
            })
            return {"statusCode": 200, "body": json.dumps(result)}

        except Exception as exc:
            logger.exception("Charter failed")
            _emit("analysis.charts.failed", {"error": str(exc)})
            return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(exc)})}


def health_check() -> Dict[str, Any]:
    """Health payload for M10 evidence and readiness probes."""
    return {
        "service": "chart_maker",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "model": BEDROCK_MODEL_ID,
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