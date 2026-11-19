"""
Chart Maker Agent.

Computes portfolio allocations deterministically and uses the LLM to
produce Recharts-compatible JSON. All dollar values come from Python;
the LLM only chooses titles, ordering, colors, and narrative framing.
"""
import logging
import os
from typing import Any, Dict

from agents.extensions.models.litellm_model import LitellmModel

from templates import create_charter_task

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")

# Deterministic palette so chart colors are stable across runs
DEFAULT_PALETTE = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#EC4899", "#6366F1",
    "#14B8A6", "#F97316", "#7C3AED", "#DC2626",
]


def _value_of(position: Dict[str, Any]) -> float:
    """Return dollar value of a position; 0 if no price is available."""
    inst = position.get("instrument") or {}
    price = inst.get("current_price")
    if price in (None, ""):
        return 0.0
    return float(position.get("quantity") or 0) * float(price)


def _cash(account: Dict[str, Any]) -> float:
    cb = account.get("cash_balance")
    return float(cb) if cb not in (None, "") else 0.0


def analyze_portfolio(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically compute portfolio allocations.

    Returns a structured dict with totals, account breakdown, holdings,
    and allocations by asset class, region, and sector. Consumed by both
    the LLM prompt and the post-processing validator.
    """
    total_value = 0.0
    cash_total = 0.0
    account_totals: Dict[str, Dict[str, Any]] = {}
    position_values: Dict[str, float] = {}
    asset_classes: Dict[str, float] = {}
    regions: Dict[str, float] = {}
    sectors: Dict[str, float] = {}

    for account in portfolio_data.get("accounts", []):
        name = account.get("name") or "Unknown"
        acct_type = account.get("type") or "investment"
        cash = _cash(account)
        cash_total += cash
        total_value += cash

        account_totals.setdefault(name, {"value": 0.0, "type": acct_type, "positions": []})
        account_totals[name]["value"] += cash

        for position in account.get("positions", []):
            symbol = position.get("symbol")
            value = _value_of(position)
            inst = position.get("instrument") or {}

            position_values[symbol] = position_values.get(symbol, 0.0) + value
            account_totals[name]["value"] += value
            account_totals[name]["positions"].append({"symbol": symbol, "value": value})
            total_value += value

            for asset_class, pct in (inst.get("allocation_asset_class") or {}).items():
                asset_classes[asset_class] = asset_classes.get(asset_class, 0.0) + value * (pct / 100)
            for region, pct in (inst.get("allocation_regions") or {}).items():
                regions[region] = regions.get(region, 0.0) + value * (pct / 100)
            for sector, pct in (inst.get("allocation_sectors") or {}).items():
                sectors[sector] = sectors.get(sector, 0.0) + value * (pct / 100)

    if cash_total > 0:
        asset_classes["cash"] = asset_classes.get("cash", 0.0) + cash_total

    # Round to cents for stable output
    def _round(d: Dict[str, float]) -> Dict[str, float]:
        return {k: round(v, 2) for k, v in d.items() if v > 0}

    return {
        "total_value": round(total_value, 2),
        "cash_total": round(cash_total, 2),
        "num_accounts": len(account_totals),
        "num_positions": sum(len(a["positions"]) for a in account_totals.values()),
        "accounts": {k: {"value": round(v["value"], 2), "type": v["type"]} for k, v in account_totals.items()},
        "top_holdings": dict(sorted(position_values.items(), key=lambda x: -x[1])[:10]),
        "asset_classes": _round(asset_classes),
        "regions": _round(regions),
        "sectors": _round(sectors),
    }


def analyze_portfolio_for_prompt(portfolio_data: Dict[str, Any]) -> str:
    """Format the deterministic analysis as a compact text block for the LLM."""
    a = analyze_portfolio(portfolio_data)

    lines = [
        "Portfolio Analysis:",
        f"  Total Value: ${a['total_value']:,.2f}",
        f"  Accounts: {a['num_accounts']}",
        f"  Positions: {a['num_positions']}",
        "",
        "Account Breakdown (dollar values):",
    ]
    for name, info in a["accounts"].items():
        pct = (info["value"] / a["total_value"] * 100) if a["total_value"] else 0
        lines.append(f"  {name} ({info['type']}): ${info['value']:,.2f} ({pct:.1f}%)")

    lines.append("")
    lines.append("Top Holdings (dollar values):")
    for symbol, value in a["top_holdings"].items():
        pct = (value / a["total_value"] * 100) if a["total_value"] else 0
        lines.append(f"  {symbol}: ${value:,.2f} ({pct:.1f}%)")

    lines.append("")
    lines.append("Asset Classes (dollar values):")
    for k, v in sorted(a["asset_classes"].items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: ${v:,.2f}")

    lines.append("")
    lines.append("Regions (dollar values):")
    for k, v in sorted(a["regions"].items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: ${v:,.2f}")

    lines.append("")
    lines.append("Sectors (dollar values):")
    for k, v in sorted(a["sectors"].items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  {k}: ${v:,.2f}")

    return "\n".join(lines)


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db=None):
    """Build the chart maker model, task, and deterministic analysis."""
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")

    analysis = analyze_portfolio_for_prompt(portfolio_data)
    task = create_charter_task(analysis, portfolio_data)

    logger.info("Charter: task built, analysis length=%d", len(analysis))
    return model, task, analyze_portfolio(portfolio_data)