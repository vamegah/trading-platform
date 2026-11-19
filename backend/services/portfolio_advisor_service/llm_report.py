import asyncio
import json
import os
from typing import Any

try:
    from agents import Agent, RunConfig, Runner  # type: ignore[import]
    from agents.extensions.models.litellm_model import LitellmModel  # type: ignore[import]
except ImportError:  # optional dependency; checked when a report is generated
    Agent = RunConfig = Runner = LitellmModel = None


REPORT_INSTRUCTIONS = """Write a concise portfolio research narrative from the supplied calculated facts.
Use only the supplied facts. Do not infer missing market data or invent company information.
Describe concentration, factor exposures, data-quality limitations, and diversification context.
Incorporate cited research items only as attributed context, and preserve their source URLs.
Do not give buy, sell, hold, rebalance, tax, or individualized investment instructions.
Do not make forecasts, guarantee outcomes, or claim fiduciary/advisory status.
Return accessible Markdown with a short summary, observations, and limitations.
This is educational research and does not authorize trades."""

RETIREMENT_INSTRUCTIONS = """Explain the supplied retirement scenario results in clear, cautious language.
Use only the computed statistics and methodology supplied. Explain uncertainty and the
independent-return/correlation limitations. Do not invent user assumptions, recommend specific
securities or trades, or promise a probability of success. This is educational scenario analysis."""


def _report_input(result: dict[str, Any]) -> dict[str, Any]:
    holdings = result["charts"]["top_holdings"]
    allowed_statistics = {
        "known_market_value",
        "position_count",
        "priced_position_count",
        "price_coverage",
        "largest_position_weight",
        "factor_exposures",
    }
    return {
        "known_portfolio_statistics": {
            key: value
            for key, value in result["portfolio"].items()
            if key in allowed_statistics
        },
        "calculated_observations": result["report"]["observations"],
        "data_warnings": result["report"]["data_warnings"],
        "top_holdings": holdings,
        "factor_exposures": result["charts"]["factor_exposures"],
        "source_dates_and_providers": [
            {
                "symbol": holding["symbol"],
                "price_as_of": holding["price_as_of"],
                "price_source": holding["price_source"],
            }
            for holding in holdings
        ],
        "cited_research": [
            {
                "symbol": snapshot["symbol"],
                "summary": snapshot["summary"],
                "sources": snapshot["source_refs"],
                "events": snapshot.get("items", []),
            }
            for snapshot in result.get("research", {}).get("snapshots", [])
        ],
    }


def _retirement_input(result: dict[str, Any]) -> dict[str, Any]:
    projection = result.get("retirement", {})
    methodology = projection.get("methodology", {})
    return {
        "status": projection.get("status"),
        "success_rate": projection.get("success_rate"),
        "ending_balance_percentiles": projection.get("ending_balance_percentiles"),
        "methodology": {
            key: methodology.get(key)
            for key in (
                "asset_return_assumptions",
                "weighted_mean_return",
                "weighted_volatility",
                "correlations",
                "contribution_timing",
                "withdrawal_timing",
                "interpretation",
            )
        },
    }


async def _run_agent(
    *,
    name: str,
    instructions: str,
    agent_input: dict[str, Any],
    model_id: str,
    region: str,
) -> str:
    if Agent is None or Runner is None or RunConfig is None or LitellmModel is None:
        raise ImportError(
            "openai-agents package is required for LLM report generation. "
            "Install it with: pip install openai-agents"
        )
    agent = Agent(
        name=name,
        instructions=instructions,
        model=LitellmModel(model=f"bedrock/converse/{model_id}"),
    )
    run_result = await Runner.run(
        agent,
        input=json.dumps(agent_input, sort_keys=True, default=str),
        max_turns=2,
        run_config=RunConfig(tracing_disabled=True),
    )
    narrative = run_result.final_output
    if not isinstance(narrative, str) or not narrative.strip():
        raise ValueError("The configured model returned an empty report")
    return narrative.strip()


async def _run_agents(result: dict[str, Any], model_id: str, region: str) -> dict[str, str | None]:
    os.environ["AWS_REGION_NAME"] = region
    portfolio_task = _run_agent(
        name="Portfolio Report Writer",
        instructions=REPORT_INSTRUCTIONS,
        agent_input=_report_input(result),
        model_id=model_id,
        region=region,
    )
    retirement = result.get("retirement", {})
    retirement_task = (
        _run_agent(
            name="Retirement Specialist",
            instructions=RETIREMENT_INSTRUCTIONS,
            agent_input=_retirement_input(result),
            model_id=model_id,
            region=region,
        )
        if retirement.get("status") == "calculated"
        else None
    )
    outcomes = await asyncio.gather(
        portfolio_task,
        retirement_task if retirement_task else asyncio.sleep(0, result=None),
        return_exceptions=True,
    )
    return {
        "portfolio_report": outcomes[0] if isinstance(outcomes[0], str) else None,
        "retirement_narrative": outcomes[1] if isinstance(outcomes[1], str) else None,
    }


def generate_llm_narratives(
    result: dict[str, Any], model_id: str, region: str
) -> dict[str, str | None]:
    return asyncio.run(_run_agents(result, model_id, region))


def generate_llm_report(result: dict[str, Any], model_id: str, region: str) -> str:
    narrative = generate_llm_narratives(result, model_id, region)["portfolio_report"]
    if narrative is None:
        raise ValueError("The configured model did not return a portfolio report")
    return narrative