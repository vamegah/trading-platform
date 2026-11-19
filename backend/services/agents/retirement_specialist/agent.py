"""
Retirement Specialist Agent.

Deterministic Monte Carlo simulation + LLM narrative. The RNG is seeded
per (job_id, user_id) so results are reproducible across runs, which is
required for the M10 paper-trading and audit evidence.
"""
import hashlib
import json
import logging
import os
import random
from typing import Any, Dict, List

from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")

# Simulation parameters
DEFAULT_NUM_SIMULATIONS = int(os.getenv("RETIREMENT_SIMULATIONS", "1000"))
DEFAULT_RETIREMENT_YEARS = int(os.getenv("RETIREMENT_YEARS", "30"))
DEFAULT_INFLATION_RATE = float(os.getenv("RETIREMENT_INFLATION", "0.03"))
DEFAULT_ANNUAL_CONTRIBUTION = float(os.getenv("RETIREMENT_CONTRIBUTION", "10000"))
DEFAULT_CURRENT_AGE = int(os.getenv("RETIREMENT_CURRENT_AGE", "40"))

# Historical return assumptions
RETURN_PARAMS = {
    "equity":         {"mean": 0.07, "std": 0.18},
    "fixed_income":   {"mean": 0.04, "std": 0.05},
    "real_estate":    {"mean": 0.06, "std": 0.12},
    "commodities":    {"mean": 0.05, "std": 0.15},
    "cash":           {"mean": 0.02, "std": 0.01},
}


def _seeded_rng(job_id: str, user_id: str) -> random.Random:
    """Return a Random instance seeded deterministically from job+user."""
    seed = int(hashlib.sha256(f"{job_id}:{user_id}".encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return rng


# ---------------------------------------------------------- portfolio math

def calculate_portfolio_value(portfolio_data: Dict[str, Any]) -> float:
    """Sum cash plus market value of positions. Missing prices are 0."""
    total = 0.0
    for account in portfolio_data.get("accounts", []):
        total += float(account.get("cash_balance") or 0)
        for position in account.get("positions", []):
            inst = position.get("instrument") or {}
            price = inst.get("current_price")
            if price in (None, ""):
                continue
            total += float(position.get("quantity") or 0) * float(price)
    return round(total, 2)


def calculate_asset_allocation(portfolio_data: Dict[str, Any]) -> Dict[str, float]:
    """Return normalized asset class weights (sum to 1.0)."""
    buckets = {k: 0.0 for k in RETURN_PARAMS}
    total = 0.0

    for account in portfolio_data.get("accounts", []):
        cash = float(account.get("cash_balance") or 0)
        buckets["cash"] += cash
        total += cash

        for position in account.get("positions", []):
            inst = position.get("instrument") or {}
            price = inst.get("current_price")
            if price in (None, ""):
                continue
            value = float(position.get("quantity") or 0) * float(price)
            total += value

            alloc = inst.get("allocation_asset_class") or {}
            for asset_class, pct in alloc.items():
                key = asset_class if asset_class in buckets else None
                if key:
                    buckets[key] += value * (pct / 100.0)

    if total <= 0:
        return {k: 0.0 for k in RETURN_PARAMS}
    return {k: round(v / total, 4) for k, v in buckets.items()}


# ------------------------------------------------------------ simulation

def run_monte_carlo(
    current_value: float,
    years_until_retirement: int,
    target_annual_income: float,
    allocation: Dict[str, float],
    rng: random.Random,
    num_simulations: int = DEFAULT_NUM_SIMULATIONS,
    retirement_years: int = DEFAULT_RETIREMENT_YEARS,
    annual_contribution: float = DEFAULT_ANNUAL_CONTRIBUTION,
) -> Dict[str, Any]:
    """Run Monte Carlo and return aggregate statistics."""
    successful = 0
    final_values: List[float] = []
    years_lasted: List[int] = []

    for _ in range(num_simulations):
        value = current_value

        # Accumulation
        for _ in range(years_until_retirement):
            ret = _portfolio_return(allocation, rng)
            value = value * (1 + ret) + annual_contribution

        # Retirement
        withdrawal = target_annual_income
        lasted = 0
        for _ in range(retirement_years):
            if value <= 0:
                break
            withdrawal *= (1 + DEFAULT_INFLATION_RATE)
            ret = _portfolio_return(allocation, rng)
            value = value * (1 + ret) - withdrawal
            if value > 0:
                lasted += 1

        final_values.append(max(0.0, value))
        years_lasted.append(lasted)
        if lasted >= retirement_years:
            successful += 1

    final_values.sort()
    years_lasted.sort()

    return {
        "success_rate": round(successful / num_simulations * 100, 1),
        "median_final_value": round(final_values[num_simulations // 2], 2),
        "percentile_10": round(final_values[num_simulations // 10], 2),
        "percentile_90": round(final_values[9 * num_simulations // 10], 2),
        "average_years_lasted": round(sum(years_lasted) / len(years_lasted), 1),
        "num_simulations": num_simulations,
    }


def _portfolio_return(allocation: Dict[str, float], rng: random.Random) -> float:
    total = 0.0
    for asset_class, weight in allocation.items():
        if weight <= 0:
            continue
        params = RETURN_PARAMS.get(asset_class)
        if not params:
            continue
        total += weight * rng.gauss(params["mean"], params["std"])
    return total


def generate_projections(
    current_value: float,
    years_until_retirement: int,
    allocation: Dict[str, float],
    current_age: int,
) -> List[Dict[str, Any]]:
    """Produce milestone projections for the frontend chart."""
    expected_return = sum(
        allocation.get(k, 0) * RETURN_PARAMS[k]["mean"] for k in RETURN_PARAMS
    )

    projections: List[Dict[str, Any]] = []
    value = current_value

    for year in range(0, years_until_retirement + 31, 5):
        if year <= years_until_retirement:
            for _ in range(5):
                value = value * (1 + expected_return) + DEFAULT_ANNUAL_CONTRIBUTION
            phase = "accumulation"
            annual_income = 0.0
        else:
            withdrawal = value * 0.04
            for _ in range(5):
                value = value * (1 + expected_return) - withdrawal
            phase = "retirement"
            annual_income = withdrawal

        if value > 0:
            projections.append({
                "year": year,
                "age": current_age + year,
                "portfolio_value": round(value, 2),
                "annual_income": round(annual_income, 2),
                "phase": phase,
            })

    return projections


# -------------------------------------------------------------- agent

def create_agent(
    job_id: str,
    clerk_user_id: str,
    portfolio_data: Dict[str, Any],
    user_preferences: Dict[str, Any],
    db=None,
):
    """Build the retirement agent's model, prompt, and structured payload."""
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    years_until_retirement = int(user_preferences.get("years_until_retirement") or 30)
    target_income = float(user_preferences.get("target_retirement_income") or 80000)
    current_age = int(user_preferences.get("current_age") or DEFAULT_CURRENT_AGE)

    portfolio_value = calculate_portfolio_value(portfolio_data)
    allocation = calculate_asset_allocation(portfolio_data)

    rng = _seeded_rng(job_id, clerk_user_id)

    monte_carlo = run_monte_carlo(
        current_value=portfolio_value,
        years_until_retirement=years_until_retirement,
        target_annual_income=target_income,
        allocation=allocation,
        rng=rng,
    )
    projections = generate_projections(
        current_value=portfolio_value,
        years_until_retirement=years_until_retirement,
        allocation=allocation,
        current_age=current_age,
    )

    safe_withdrawal = round(portfolio_value * 0.04, 2)
    gap = round(target_income - safe_withdrawal, 2)

    task = f"""# Retirement Readiness Analysis

## Current Situation
- Portfolio value: ${portfolio_value:,.0f}
- Asset allocation: {json.dumps(allocation)}
- Years to retirement: {years_until_retirement}
- Current age: {current_age}
- Target annual income: ${target_income:,.0f}

## Monte Carlo ({monte_carlo['num_simulations']} scenarios)
- Success rate: {monte_carlo['success_rate']}%
- Median final value: ${monte_carlo['median_final_value']:,.0f}
- 10th percentile: ${monte_carlo['percentile_10']:,.0f}
- 90th percentile: ${monte_carlo['percentile_90']:,.0f}
- Average years income lasts: {monte_carlo['average_years_lasted']}

## Safe Withdrawal Check
- 4% rule income: ${safe_withdrawal:,.0f}
- Target income: ${target_income:,.0f}
- Gap: ${gap:,.0f}

## Projections (milestone years)
{json.dumps(projections, indent=2)}

Produce a retirement analysis in markdown covering:
1. Retirement readiness assessment
2. Specific recommendations to improve the success rate
3. Risk mitigation strategies
4. Action items with timeline

Use only numbers shown here. Do not invent values."""

    structured_payload = {
        "portfolio_value": portfolio_value,
        "allocation": allocation,
        "years_until_retirement": years_until_retirement,
        "target_annual_income": target_income,
        "current_age": current_age,
        "monte_carlo": monte_carlo,
        "projections": projections,
        "safe_withdrawal_income": safe_withdrawal,
        "target_gap": gap,
    }

    return model, task, structured_payload