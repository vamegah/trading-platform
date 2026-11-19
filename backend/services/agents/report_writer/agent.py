"""
Report Writer Agent.

Generates the portfolio narrative report in markdown form, plus a
structured summary that the frontend and downstream agents consume.
"""
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from agents import RunContextWrapper, function_tool
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")

VECTOR_BUCKET = os.getenv("VECTOR_BUCKET")
INDEX_NAME = os.getenv("INDEX_NAME", "financial-research")
SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT")


@dataclass
class ReporterContext:
    """Context passed to reporter tools."""
    job_id: str
    clerk_user_id: str
    portfolio_data: Dict[str, Any]
    user_data: Dict[str, Any]
    db: Optional[Any] = None


# --------------------------------------------------------------- metrics

def calculate_portfolio_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute lightweight portfolio metrics used in the prompt."""
    total_value = 0.0
    cash = 0.0
    num_positions = 0
    symbols: set[str] = set()

    for account in portfolio_data.get("accounts", []):
        cash += float(account.get("cash_balance") or 0)
        for position in account.get("positions", []):
            num_positions += 1
            if position.get("symbol"):
                symbols.add(position["symbol"])

            instrument = position.get("instrument") or {}
            price = instrument.get("current_price")
            if price:
                total_value += float(position.get("quantity") or 0) * float(price)

    return {
        "total_value": round(total_value + cash, 2),
        "cash_balance": round(cash, 2),
        "num_accounts": len(portfolio_data.get("accounts", [])),
        "num_positions": num_positions,
        "unique_symbols": len(symbols),
    }


def format_portfolio_for_analysis(portfolio_data: Dict[str, Any], user_data: Dict[str, Any]) -> str:
    """Format the portfolio as a compact text block for the LLM."""
    metrics = calculate_portfolio_metrics(portfolio_data)

    lines = [
        "Portfolio Overview:",
        f"- {metrics['num_accounts']} accounts",
        f"- {metrics['num_positions']} positions",
        f"- {metrics['unique_symbols']} unique holdings",
        f"- ${metrics['cash_balance']:,.2f} cash",
        f"- ${metrics['total_value']:,.2f} total value",
        "",
        "Account Details:",
    ]

    for account in portfolio_data.get("accounts", []):
        name = account.get("name", "Unknown")
        cash = float(account.get("cash_balance") or 0)
        lines.append(f"\n{name} (${cash:,.2f} cash):")
        for position in account.get("positions", []):
            symbol = position.get("symbol")
            qty = float(position.get("quantity") or 0)
            inst = position.get("instrument") or {}
            allocs: List[str] = []
            if inst.get("allocation_asset_class"):
                allocs.append(f"Asset: {list(inst['allocation_asset_class'].keys())}")
            alloc_str = f" ({', '.join(allocs)})" if allocs else ""
            lines.append(f"  - {symbol}: {qty:,.2f} shares{alloc_str}")

    lines.extend([
        "",
        "User Profile:",
        f"- Years to retirement: {user_data.get('years_until_retirement', 'unspecified')}",
        f"- Target retirement income: ${user_data.get('target_retirement_income', 0):,.0f}/year",
    ])

    return "\n".join(lines)


# --------------------------------------------------------------- tools

async def _get_embedding(text: str) -> list[float]:
    """Embed via the shared SageMaker endpoint."""
    sagemaker = boto3.client("sagemaker-runtime", region_name=BEDROCK_REGION)
    resp = sagemaker.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    result = json.loads(resp["Body"].read().decode())
    if isinstance(result, list) and result:
        if isinstance(result[0], list):
            return result[0][0] if isinstance(result[0][0], list) else result[0]
    return result


@function_tool
async def get_market_insights(
    wrapper: RunContextWrapper[ReporterContext],
    symbols: List[str],
) -> str:
    """Retrieve relevant knowledge-base articles for these symbols.

    Uses the canonical metadata filters (agent, doc_type) and min_score
    so we do not surface stale or low-signal context.
    """
    if not VECTOR_BUCKET or not SAGEMAKER_ENDPOINT:
        return "Knowledge base not configured."

    try:
        query = f"market analysis for {', '.join(symbols[:5])}" if symbols else "market outlook"
        embedding = await _get_embedding(query)

        s3v = boto3.client("s3vectors", region_name=BEDROCK_REGION)
        resp = s3v.query_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            queryVector={"float32": embedding},
            topK=5,
            returnDistance=True,
            returnMetadata=True,
        )

        insights: List[str] = []
        for v in resp.get("vectors", []):
            meta = v.get("metadata", {}) or {}
            if meta.get("agent") not in {"researcher_agent", "report_writer"}:
                continue
            score = 1.0 - float(v.get("distance", 0.0))
            if score < 0.4:
                continue
            text = (meta.get("text") or "")[:280]
            prefix = "- "
            tickers = meta.get("tickers") or []
            if tickers:
                prefix = f"{','.join(tickers)}: "
            insights.append(f"{prefix}{text}")

        if not insights:
            return "No recent insights found. Proceed with standard analysis."
        return "Market Insights:\n" + "\n".join(insights)
    except Exception:
        logger.exception("Reporter: knowledge base retrieval failed")
        return "Market insights unavailable - proceeding with standard analysis."


def create_agent(job_id: str, clerk_user_id: str, portfolio_data: Dict[str, Any], user_data: Dict[str, Any], db=None):
    """Build the reporter model, tools, prompt, and context."""
    context = ReporterContext(
        job_id=job_id,
        clerk_user_id=clerk_user_id,
        portfolio_data=portfolio_data,
        user_data=user_data,
        db=db,
    )

    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    tools = [get_market_insights]

    portfolio_summary = format_portfolio_for_analysis(portfolio_data, user_data)
    task = f"""Analyze this investment portfolio and write a comprehensive report.

{portfolio_summary}

Steps:
1. Call get_market_insights for the top holdings.
2. Produce a markdown report covering:
   - Executive Summary (3-4 points)
   - Portfolio Composition
   - Diversification Assessment
   - Risk Profile
   - Retirement Readiness
   - Specific Recommendations (5-7 items)
   - Conclusion
3. Return the markdown report as your final output.

Write for a retail investor: clear, specific, actionable, with numbers."""

    return model, tools, task, context