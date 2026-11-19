from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.shared.models import DataSnapshot, Instrument, MarketData, Position
from backend.services.portfolio_advisor_service.schemas import RetirementAssumptions


SNAPSHOT_SCHEMA = "portfolio-advisor.snapshot.v1"
MODEL_ASSUMPTIONS = {
    "equity": {"mean": 0.07, "stddev": 0.18},
    "fixed_income": {"mean": 0.035, "stddev": 0.06},
    "real_estate": {"mean": 0.055, "stddev": 0.13},
    "commodities": {"mean": 0.035, "stddev": 0.20},
    "cash": {"mean": 0.02, "stddev": 0.005},
}


def build_source_snapshot(
    db: Session,
    *,
    portfolio_id: int,
    max_market_data_age_days: int,
) -> dict[str, Any]:
    today = date.today()
    positions = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .order_by(Position.symbol)
        .all()
    )
    instrument_symbols = {position.symbol.upper() for position in positions}
    instruments = {
        instrument.symbol.upper(): instrument
        for instrument in (
            db.query(Instrument).filter(Instrument.symbol.in_(instrument_symbols)).all()
            if instrument_symbols
            else []
        )
    }
    position_snapshots = []
    for position in positions:
        instrument = instruments.get(position.symbol.upper())
        metadata = (instrument.instrument_metadata or {}) if instrument else {}
        market_data = (
            db.query(MarketData)
            .filter(MarketData.symbol == position.symbol.upper())
            .order_by(MarketData.date.desc(), MarketData.id.desc())
            .first()
        )
        age_days = (today - market_data.date).days if market_data else None
        fresh = bool(
            market_data
            and market_data.close is not None
            and market_data.close > 0
            and age_days is not None
            and 0 <= age_days <= max_market_data_age_days
        )
        position_snapshots.append(
            {
                "symbol": position.symbol.upper(),
                "asset_type": position.asset_type,
                "quantity": float(position.quantity),
                "average_cost": float(position.average_cost),
                "factor_exposures": position.factor_exposures or metadata.get("factor_exposures", {}),
                "instrument_name": instrument.name if instrument else None,
                "instrument_type": instrument.asset_type if instrument else position.asset_type,
                "instrument_metadata": metadata,
                "price": float(market_data.close) if market_data and market_data.close else None,
                "price_as_of": market_data.date.isoformat() if market_data else None,
                "price_source": market_data.source if market_data else None,
                "price_age_days": age_days,
                "price_fresh": fresh,
                "market_value": round(float(position.quantity) * float(market_data.close), 2)
                if fresh and market_data
                else None,
            }
        )

    source_data = {
        "schema": SNAPSHOT_SCHEMA,
        "portfolio_id": portfolio_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "max_market_data_age_days": max_market_data_age_days,
        "positions": position_snapshots,
    }
    content_hash = hashlib.sha256(
        json.dumps(source_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    snapshot_key = f"portfolio-advisor:{portfolio_id}:{uuid4().hex}"
    data_snapshot = DataSnapshot(
        snapshot_key=snapshot_key,
        dataset="portfolio_advisor",
        version=SNAPSHOT_SCHEMA,
        source="platform_market_data",
        schema_hash=hashlib.sha256(SNAPSHOT_SCHEMA.encode()).hexdigest(),
        row_count=len(position_snapshots),
    )
    db.add(data_snapshot)
    db.flush()
    source_data["snapshot_id"] = snapshot_key
    source_data["data_snapshot_row_id"] = data_snapshot.id
    source_data["content_hash"] = content_hash
    return source_data


def _weighted_exposures(positions: list[dict[str, Any]], total_value: float) -> dict[str, float]:
    exposures: dict[str, float] = {}
    if total_value <= 0:
        return exposures
    for position in positions:
        value = position.get("market_value")
        if value is None:
            continue
        for factor, exposure in position.get("factor_exposures", {}).items():
            exposures[factor] = exposures.get(factor, 0.0) + float(value) * float(exposure)
    return {key: round(value / total_value, 4) for key, value in sorted(exposures.items())}


def attach_instrument_classifications(
    result: dict[str, Any],
    source_snapshot: dict[str, Any],
    classifications: list[dict[str, Any]],
    *,
    status: str,
    skipped_symbols: list[str] | None = None,
) -> None:
    by_symbol = {item["symbol"].upper(): item for item in classifications}
    buckets = {name: {} for name in ("asset_class", "region", "sector")}
    classified_symbols = []
    for position in source_snapshot["positions"]:
        value = position.get("market_value")
        if value is None:
            continue
        symbol = position["symbol"].upper()
        metadata = position.get("instrument_metadata") or {}
        classification = by_symbol.get(symbol)
        mappings = {
            "asset_class": (
                classification.get("allocation_asset_class") if classification
                else metadata.get("allocation_asset_class")
            ),
            "region": (
                classification.get("allocation_regions") if classification
                else metadata.get("allocation_regions")
            ),
            "sector": (
                classification.get("allocation_sectors") if classification
                else metadata.get("allocation_sectors")
            ),
        }
        recognized = False
        for dimension, allocation in mappings.items():
            if not isinstance(allocation, dict):
                continue
            allocation = allocation.get("allocations", allocation)
            total = sum(float(weight) for weight in allocation.values())
            if abs(total - 100) > 3:
                continue
            recognized = True
            for key, weight in allocation.items():
                buckets[dimension][key] = buckets[dimension].get(key, 0.0) + float(value) * float(weight) / 100
        if recognized:
            classified_symbols.append(symbol)

    total_value = float(result["portfolio"]["known_market_value"])
    result["charts"]["allocation"] = {
        dimension: [
            {
                "category": category,
                "value": round(value, 2),
                "weight": round(value / total_value, 4) if total_value else 0.0,
            }
            for category, value in sorted(values.items(), key=lambda item: item[1], reverse=True)
        ]
        for dimension, values in buckets.items()
    }
    result["instrument_tagging"] = {
        "status": status,
        "classified_symbols": sorted(set(classified_symbols)),
        "llm_classifications": [by_symbol[symbol] for symbol in sorted(by_symbol)],
        "skipped_symbols": skipped_symbols or [],
        "price_source": "platform market data only; tagger price output is not requested or accepted",
    }


def run_retirement_projection(
    portfolio_value: float,
    assumptions: RetirementAssumptions,
) -> dict[str, Any]:
    rng = random.Random(assumptions.seed)
    allocation = assumptions.allocation
    annual_means = sum(
        allocation[key] * MODEL_ASSUMPTIONS[key]["mean"] for key in allocation
    )
    annual_volatility = math.sqrt(
        sum((allocation[key] * MODEL_ASSUMPTIONS[key]["stddev"]) ** 2 for key in allocation)
    )
    ending_balances = []
    successful_scenarios = 0
    for _ in range(assumptions.simulations):
        balance = portfolio_value
        for _year in range(assumptions.years_until_retirement):
            annual_return = sum(
                allocation[key]
                * rng.gauss(MODEL_ASSUMPTIONS[key]["mean"], MODEL_ASSUMPTIONS[key]["stddev"])
                for key in allocation
            )
            balance = max(0.0, balance * (1 + annual_return) + assumptions.annual_contribution)
        for year in range(assumptions.years_in_retirement):
            withdrawal = assumptions.target_annual_income * (1 + assumptions.inflation_rate) ** year
            annual_return = sum(
                allocation[key]
                * rng.gauss(MODEL_ASSUMPTIONS[key]["mean"], MODEL_ASSUMPTIONS[key]["stddev"])
                for key in allocation
            )
            balance = max(0.0, balance * (1 + annual_return) - withdrawal)
            if balance == 0:
                break
        ending_balances.append(balance)
        if balance > 0:
            successful_scenarios += 1

    ending_balances.sort()

    def percentile(fraction: float) -> float:
        index = round((len(ending_balances) - 1) * fraction)
        return round(ending_balances[index], 2)

    return {
        "status": "calculated",
        "success_rate": round(successful_scenarios / assumptions.simulations, 4),
        "ending_balance_percentiles": {
            "p10": percentile(0.10),
            "p50": percentile(0.50),
            "p90": percentile(0.90),
        },
        "assumptions": assumptions.model_dump(),
        "methodology": {
            "model": "independent_normal_asset_returns_v1",
            "asset_return_assumptions": MODEL_ASSUMPTIONS,
            "weighted_mean_return": round(annual_means, 6),
            "weighted_volatility": round(annual_volatility, 6),
            "correlations": "asset-class returns are sampled independently; covariance is not modeled",
            "allocation_policy": "target weights are assumed to remain constant and are rebalanced annually",
            "contribution_timing": "end of each accumulation year",
            "withdrawal_timing": "end of each retirement year",
            "interpretation": "Illustrative scenario analysis, not a forecast or guarantee.",
        },
    }


def analyze_portfolio_snapshot(
    source_snapshot: dict[str, Any],
    retirement: RetirementAssumptions | None = None,
) -> dict[str, Any]:
    positions = source_snapshot["positions"]
    priced_positions = [position for position in positions if position["market_value"] is not None]
    total_value = round(sum(position["market_value"] or 0 for position in priced_positions), 2)
    missing = [position["symbol"] for position in positions if position["market_value"] is None]
    warnings = [
        {
            "symbol": position["symbol"],
            "reason": "missing_market_data" if position["price"] is None else "stale_or_invalid_price",
            "price_as_of": position["price_as_of"],
            "price_age_days": position["price_age_days"],
        }
        for position in positions
        if position["market_value"] is None
    ]
    holdings = sorted(
        [
            {
                "symbol": position["symbol"],
                "market_value": position["market_value"],
                "weight": round(position["market_value"] / total_value, 4) if total_value else 0,
                "price_as_of": position["price_as_of"],
                "price_source": position["price_source"],
            }
            for position in priced_positions
        ],
        key=lambda item: item["market_value"],
        reverse=True,
    )
    concentration = holdings[0]["weight"] if holdings else 0.0
    observations = [
        f"{len(positions)} positions were captured; {len(priced_positions)} have fresh, usable market prices.",
        f"Known market value is ${total_value:,.2f}; cash and unpriced positions are excluded.",
    ]
    if holdings:
        observations.append(
            f"{holdings[0]['symbol']} is the largest priced holding at {concentration:.1%} of known market value."
        )
    if warnings:
        observations.append(f"{len(warnings)} positions were excluded because price data was missing or stale.")

    retirement_result: dict[str, Any]
    if retirement is None:
        retirement_result = {"status": "not_requested"}
    elif not positions:
        retirement_result = {"status": "not_calculated", "reason": "portfolio_has_no_positions"}
    elif missing:
        retirement_result = {
            "status": "not_calculated",
            "reason": "fresh_prices_required_for_all_positions",
            "unpriced_symbols": missing,
        }
    elif total_value <= 0:
        retirement_result = {"status": "not_calculated", "reason": "portfolio_value_not_positive"}
    else:
        retirement_result = run_retirement_projection(total_value, retirement)

    return {
        "contract_version": "portfolio-advisor.result.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "disclosure": "Research and educational analysis only; not investment, tax, or legal advice. This report does not place or authorize trades.",
        "portfolio": {
            "portfolio_id": source_snapshot["portfolio_id"],
            "known_market_value": total_value,
            "position_count": len(positions),
            "priced_position_count": len(priced_positions),
            "price_coverage": round(len(priced_positions) / len(positions), 4) if positions else 0.0,
            "largest_position_weight": round(concentration, 4),
            "factor_exposures": _weighted_exposures(priced_positions, total_value),
        },
        "report": {
            "generator": "deterministic_portfolio_summary_v1",
            "status": "partial" if warnings or not positions else "complete",
            "observations": observations,
            "data_warnings": warnings,
            "methodology": "Values use platform positions multiplied by the latest valid market-data close within the requested freshness window. Unpriced positions and cash are excluded.",
        },
        "charts": {
            "top_holdings": [
                {"symbol": row["symbol"], "value": row["market_value"], "weight": row["weight"]}
                for row in holdings[:10]
            ],
            "factor_exposures": [
                {"factor": factor, "weight": weight}
                for factor, weight in _weighted_exposures(priced_positions, total_value).items()
            ],
        },
        "retirement": retirement_result,
        "source_snapshot": {
            key: source_snapshot[key]
            for key in ("snapshot_id", "data_snapshot_row_id", "content_hash", "captured_at", "max_market_data_age_days")
        },
    }