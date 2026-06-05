from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.services.trader_operating_system import (
    broker_reconciliation,
    execution_quality,
    margin_snapshot,
    portfolio_command_center,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _symbol(value: str | None, fallback: str = "MSFT") -> str:
    raw = (value or fallback).strip().upper()
    return raw if raw else fallback


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _audit(prefix: str) -> str:
    return f"audit-{prefix}-{uuid4().hex[:10]}"


def _price(symbol: str) -> float:
    return {"MSFT": 421.14, "NVDA": 124.7, "JPM": 207.55, "SPY": 544.2, "TSLA": 188.4, "GME": 28.5}.get(symbol, 100.0)


def _portfolio_positions() -> list[dict[str, Any]]:
    return portfolio_command_center()["positions"]


def _current_weights() -> dict[str, float]:
    positions = _portfolio_positions()
    total = max(sum(position["market_value"] for position in positions), 1.0)
    return {position["symbol"]: _round(position["market_value"] / total, 4) for position in positions}


def _default_targets() -> dict[str, float]:
    return {"MSFT": 0.32, "NVDA": 0.18, "JPM": 0.18, "SPY": 0.32}


STAGED_ORDERS: list[dict[str, Any]] = [
    {
        "stage_id": "stage-msft-rebalance",
        "symbol": "MSFT",
        "side": "SELL",
        "quantity": 18,
        "order_type": "limit",
        "limit_price": 424.0,
        "status": "approval_required",
        "approvals": [{"role": "maker", "status": "prepared", "actor": "sandbox-user"}],
        "compliance_holds": [],
        "allocations": {"ALP-SANDBOX-001": 0.6, "IBKR-PAPER-042": 0.4},
        "notes": "Trim technology concentration after rebalance preview.",
        "audit_id": "audit-stage-msft-rebalance",
        "created_at": (_now() - timedelta(minutes=31)).isoformat(),
    }
]

RISK_CONSTITUTION_RULES: list[dict[str, Any]] = [
    {"rule_id": "risk-max-daily-loss", "rule_type": "max_daily_loss", "threshold": 2500, "enforcement": "never_override", "enabled": True},
    {"rule_id": "risk-max-position", "rule_type": "max_position_pct", "threshold": 0.25, "enforcement": "never_override", "enabled": True},
    {"rule_id": "risk-no-earnings", "rule_type": "no_trade_around_earnings_days", "threshold": 2, "enforcement": "approval_required", "enabled": True},
    {"rule_id": "risk-options-level", "rule_type": "max_options_level", "threshold": 2, "enforcement": "never_override", "enabled": True},
    {"rule_id": "risk-cooldown", "rule_type": "loss_cooldown_minutes", "threshold": 30, "enforcement": "approval_required", "enabled": True},
]

EMERGENCY_STATE: dict[str, Any] = {
    "trading_paused": False,
    "last_action": None,
    "open_order_count": 3,
}


def workstation_overview() -> dict[str, Any]:
    command = portfolio_command_center()
    return {
        "generated_at": _now().isoformat(),
        "mode": "sandbox",
        "modules": [
            {"id": "basket", "label": "Basket Workbench", "status": "ready"},
            {"id": "pre_trade", "label": "Pre-Trade Control", "status": "enforcing"},
            {"id": "tax_lots", "label": "Tax Lots", "status": "ready"},
            {"id": "borrow", "label": "Borrow Desk", "status": "sandbox"},
            {"id": "microstructure", "label": "Microstructure", "status": "ready"},
            {"id": "emergency", "label": "Emergency Controls", "status": "paused" if EMERGENCY_STATE["trading_paused"] else "armed"},
        ],
        "portfolio": {
            "equity": command["totals"]["equity"],
            "cash": command["totals"]["cash"],
            "buying_power": command["totals"]["buying_power"],
            "risk_alerts": command["risk_alerts"],
        },
        "broker_health": broker_reconciliation()["connections"],
    }


def preview_basket(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    target_weights = {_symbol(symbol): float(weight) for symbol, weight in payload.get("target_weights", _default_targets()).items()}
    name = payload.get("name", "Core rebalance")
    positions = _portfolio_positions()
    current_by_symbol = {position["symbol"]: position for position in positions}
    portfolio_value = float(payload.get("portfolio_value", sum(position["market_value"] for position in positions)))
    current_weights = _current_weights()
    orders = []
    drift = {}

    for symbol, target_weight in target_weights.items():
        current_value = float(current_by_symbol.get(symbol, {}).get("market_value", 0.0))
        target_value = portfolio_value * target_weight
        delta_value = target_value - current_value
        if abs(delta_value) < 250:
            continue
        price = _price(symbol)
        side = "BUY" if delta_value > 0 else "SELL"
        quantity = max(1, int(abs(delta_value) / price))
        drift[symbol] = _round(target_weight - current_weights.get(symbol, 0.0), 4)
        orders.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": "limit",
                "limit_price": _round(price * (1.002 if side == "BUY" else 0.998)),
                "estimated_notional": _round(quantity * price),
                "allocations": {"ALP-SANDBOX-001": 0.6, "IBKR-PAPER-042": 0.4},
            }
        )

    impact = {
        "estimated_tax_cost": _round(sum(order["estimated_notional"] for order in orders if order["side"] == "SELL") * 0.018),
        "estimated_margin_delta": _round(sum(order["estimated_notional"] for order in orders if order["side"] == "BUY") * 0.5),
        "technology_weight_after": _round(target_weights.get("MSFT", 0) + target_weights.get("NVDA", 0), 4),
        "expected_tracking_error": 0.032,
        "estimated_commission": 0.0,
    }
    precheck = pre_trade_control({"scope": "basket", "orders": orders, "target_weights": target_weights, "buying_power": 69600})
    return {
        "basket_id": payload.get("basket_id", "basket-core-rebalance"),
        "name": name,
        "status": "ready_to_stage" if precheck["allowed"] else "blocked",
        "target_weights": target_weights,
        "current_weights": current_weights,
        "drift": drift,
        "orders": orders,
        "account_allocations": {"ALP-SANDBOX-001": 0.6, "IBKR-PAPER-042": 0.4},
        "impact_preview": impact,
        "pre_trade": precheck,
        "audit_id": _audit("basket-preview"),
    }


def basket_workbench() -> dict[str, Any]:
    preview = preview_basket({})
    return {
        "drafts": [preview],
        "templates": [
            {"name": "Quality growth balance", "target_weights": _default_targets()},
            {"name": "Income tilt", "target_weights": {"JPM": 0.28, "SPY": 0.42, "MSFT": 0.2, "NVDA": 0.1}},
        ],
        "release_controls": ["explicit_confirmation", "pre_trade_control", "tax_lot_review", "audit_record"],
    }


def submit_basket(payload: dict[str, Any]) -> dict[str, Any]:
    preview = preview_basket(payload)
    if not payload.get("confirmed", False):
        return {
            "status": "confirmation_required",
            "basket": preview,
            "required_actions": ["explicit_confirmation"],
            "audit_id": _audit("basket-submit"),
        }
    if not preview["pre_trade"]["allowed"]:
        return {"status": "blocked", "basket": preview, "audit_id": _audit("basket-block")}
    staged = []
    for order in preview["orders"]:
        staged.append(stage_order({**order, "notes": f"Basket {preview['basket_id']} rebalance child"}))
    return {
        "status": "staged",
        "basket_id": preview["basket_id"],
        "staged_orders": staged,
        "release_queue": [order["stage_id"] for order in staged],
        "audit_id": _audit("basket-staged"),
    }


def _check(name: str, passed: bool, detail: str, severity: str = "block") -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "blocked", "severity": "info" if passed else severity, "detail": detail}


def pre_trade_control(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    orders = payload.get("orders")
    if not orders:
        orders = [payload]
    symbol = _symbol(payload.get("symbol") or (orders[0] or {}).get("symbol"))
    buying_power = float(payload.get("buying_power", 69600))
    notional = sum(float(order.get("quantity", 0)) * float(order.get("limit_price") or order.get("current_price") or _price(_symbol(order.get("symbol")))) for order in orders)
    liquidity_score = float(payload.get("liquidity_score", 0.72))
    signal_freshness = float(payload.get("signal_freshness", 0.81))
    concentration_after = float(payload.get("concentration_after", 0.28))
    day_trades = int(payload.get("day_trades", 1))
    equity = float(payload.get("equity", 135706))
    side = str(payload.get("side") or (orders[0] or {}).get("side", "BUY")).upper()
    locate_status = str(payload.get("locate_status", "located")).lower()
    kill_switch_active = bool(payload.get("kill_switch_active", EMERGENCY_STATE["trading_paused"]))
    market_access_ok = bool(payload.get("market_access_ok", True))
    duplicate_order = bool(payload.get("duplicate_order", False))

    margin = margin_snapshot(
        {
            "quantity": sum(float(order.get("quantity", 0)) for order in orders),
            "current_price": notional / max(sum(float(order.get("quantity", 0)) for order in orders), 1),
            "buying_power": buying_power,
            "equity": equity,
            "concentration_after": concentration_after,
            "asset_type": payload.get("asset_type", "equity"),
            "options_approved": payload.get("options_approved", True),
        }
    )

    checks = [
        _check("suitability", bool(payload.get("suitability_complete", True)), "Suitability profile permits this sandbox workflow."),
        _check("buying_power", buying_power >= notional * 0.5, "Buying power covers projected initial requirement."),
        _check("margin", margin["allowed"], "Dynamic margin engine has no blocking violations." if margin["allowed"] else "; ".join(margin["violations"])),
        _check("concentration", concentration_after <= 0.35, "Post-trade concentration remains inside 35% limit."),
        _check("signal_freshness", signal_freshness >= 0.35, "Signal freshness is above release threshold."),
        _check("liquidity", liquidity_score >= 0.35, "Liquidity score supports the proposed order size."),
        _check("borrow_availability", side != "SELL_SHORT" or locate_status == "located", "Short sale requires an approved locate."),
        _check("pdt_day_trading", not (day_trades >= 4 and equity < 25000), "PDT/day-trading equity treatment passes."),
        _check("kill_switch", not kill_switch_active, "Trading kill switch is not active."),
        _check("market_access", market_access_ok, "Market-access credit and erroneous-order controls pass."),
        _check("duplicate_order", not duplicate_order, "No duplicate order detected in staged queue."),
    ]
    violations = [check["detail"] for check in checks if check["status"] != "passed"]
    return {
        "check_id": f"precheck-{uuid4().hex[:8]}",
        "scope": payload.get("scope", "basket" if len(orders) > 1 else "order"),
        "symbol": symbol,
        "allowed": not violations,
        "status": "allowed" if not violations else "blocked",
        "notional": _round(notional),
        "checks": checks,
        "violations": violations,
        "required_actions": [] if not violations else ["resolve_blocks", "refresh_data_or_reduce_order"],
        "audit_id": _audit("pretrade"),
    }


def tax_lot_decision(symbol: str = "MSFT", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    normalized = _symbol(symbol)
    lots = [
        {"lot_id": f"{normalized}-lot-1", "quantity": 40, "cost_basis": _round(_price(normalized) * 0.72), "acquired_at": (date.today() - timedelta(days=420)).isoformat(), "holding_period": "long_term", "unrealized_gain": 4800.0},
        {"lot_id": f"{normalized}-lot-2", "quantity": 35, "cost_basis": _round(_price(normalized) * 0.92), "acquired_at": (date.today() - timedelta(days=92)).isoformat(), "holding_period": "short_term", "unrealized_gain": 1175.0},
        {"lot_id": f"{normalized}-lot-3", "quantity": 20, "cost_basis": _round(_price(normalized) * 1.04), "acquired_at": (date.today() - timedelta(days=21)).isoformat(), "holding_period": "short_term", "unrealized_gain": -336.0},
    ]
    sell_quantity = float(payload.get("quantity", 25))
    best_lot = min(lots, key=lambda lot: lot["unrealized_gain"])
    after_tax = -max(sum(max(lot["unrealized_gain"], 0) for lot in lots[:2]) * 0.22, 0) + abs(min(best_lot["unrealized_gain"], 0)) * 0.22
    return {
        "decision_id": f"tax-{uuid4().hex[:8]}",
        "symbol": normalized,
        "sell_quantity": sell_quantity,
        "lots": lots,
        "methods": [
            {"method": "fifo", "estimated_tax": -1285.0},
            {"method": "lifo", "estimated_tax": 73.92},
            {"method": "specific_lot", "estimated_tax": 73.92},
        ],
        "recommended_method": "specific_lot",
        "best_lot_to_sell": best_lot["lot_id"],
        "wash_sale_risk": "medium" if best_lot["unrealized_gain"] < 0 else "low",
        "after_tax_estimate": _round(after_tax),
        "audit_id": _audit("taxlot"),
    }


def borrow_desk(symbol: str = "MSFT") -> dict[str, Any]:
    normalized = _symbol(symbol)
    hard = normalized in {"GME", "TSLA"}
    fee = 0.0475 if hard else 0.0065
    located = not hard
    return {
        "symbol": normalized,
        "short_eligible": True,
        "locate_status": "located" if located else "required",
        "hard_to_borrow": hard,
        "borrow_fee_rate": fee,
        "recall_risk": "high" if hard else "low",
        "short_sale_restriction": normalized == "GME",
        "dividend_liability": _round(_price(normalized) * 0.012),
        "squeeze_risk": "high" if hard else "medium",
        "workflow": ["check_eligibility", "request_locate", "pre_trade_control", "release_order"],
        "blocked_reason": None if located else "Approved locate required before short sale release.",
    }


def request_locate(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = _symbol(payload.get("symbol"))
    desk = borrow_desk(symbol)
    approved = not desk["hard_to_borrow"] and float(payload.get("quantity", 1)) <= 1000
    return {
        "locate_id": f"locate-{uuid4().hex[:8]}",
        "symbol": symbol,
        "status": "located" if approved else "review_required",
        "approved_quantity": float(payload.get("quantity", 0)) if approved else 0,
        "borrow_fee_rate": desk["borrow_fee_rate"],
        "expires_at": (_now() + timedelta(hours=4)).isoformat(),
        "audit_id": _audit("locate"),
    }


def portfolio_construction(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    objective = str(payload.get("objective", "balanced growth with tax awareness"))
    income_goal = float(payload.get("income_goal", 0.018))
    volatility_target = float(payload.get("volatility_target", 0.14))
    allocations = {"SPY": 0.36, "MSFT": 0.24, "JPM": 0.18, "NVDA": 0.12, "SGOV": 0.10}
    if "income" in objective.lower():
        allocations = {"SPY": 0.30, "JPM": 0.24, "SGOV": 0.20, "MSFT": 0.16, "XOM": 0.10}
    return {
        "model_id": f"model-{uuid4().hex[:8]}",
        "name": payload.get("name", "Objective-aware model portfolio"),
        "objective": objective,
        "target_allocations": allocations,
        "risk_budget": {"market": 0.52, "stock_specific": 0.24, "rates": 0.12, "liquidity": 0.07, "tail": 0.05},
        "factor_tilts": {"quality": 0.28, "momentum": 0.14, "value": 0.12, "low_vol": 0.08},
        "income_goal": income_goal,
        "expected_volatility": volatility_target,
        "tax_aware": bool(payload.get("tax_aware", True)),
        "contribution_plan": payload.get("contribution_plan", {"monthly": 1000, "withdrawal": 0}),
        "comparison": {"expected_tracking_error": 0.041, "concentration_improvement": 0.11, "estimated_tax_cost": 320.0},
        "rebalance_plan": preview_basket({"target_weights": {key: value for key, value in allocations.items() if key != "SGOV"}}),
    }


def market_microstructure(symbol: str = "MSFT", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    normalized = _symbol(symbol)
    price = _price(normalized)
    quantity = float(payload.get("quantity", 250))
    avg_daily_volume = {"MSFT": 24_000_000, "NVDA": 320_000_000, "JPM": 10_500_000, "GME": 8_000_000}.get(normalized, 5_000_000)
    participation = quantity / max(avg_daily_volume, 1)
    impact = max(0.4, math.sqrt(participation) * 100)
    return {
        "symbol": normalized,
        "nbbo": {"bid": _round(price - 0.02), "ask": _round(price + 0.02), "spread_bps": _round(0.04 / price * 10000, 3)},
        "depth": [
            {"venue": "NASDAQ", "bid_size": 1200, "ask_size": 980, "bid": _round(price - 0.02), "ask": _round(price + 0.02)},
            {"venue": "NYSE", "bid_size": 800, "ask_size": 1100, "bid": _round(price - 0.03), "ask": _round(price + 0.03)},
            {"venue": "IEX", "bid_size": 420, "ask_size": 390, "bid": _round(price - 0.04), "ask": _round(price + 0.04)},
        ],
        "spread_history_bps": [1.1, 1.3, 1.0, 1.2, 1.4],
        "liquidity_score": 0.82 if normalized != "GME" else 0.46,
        "auction_imbalance": {"side": "buy", "quantity": 18500, "severity": "low"},
        "volume_participation": _round(participation, 6),
        "route_visibility": {"lit": 0.72, "ats_or_dark": 0.28, "available": True},
        "estimated_market_impact_bps": _round(impact, 3),
        "likely_to_move_market": impact > 8,
    }


def trade_staging() -> dict[str, Any]:
    return {
        "staged_orders": STAGED_ORDERS,
        "release_queue": [order for order in STAGED_ORDERS if order["status"] in {"approval_required", "approved"}],
        "post_trade_allocation_reviews": [
            {"review_id": "alloc-review-1", "status": "passed", "detail": "Sandbox fills allocated by target account percentages."}
        ],
    }


def stage_order(payload: dict[str, Any]) -> dict[str, Any]:
    precheck = pre_trade_control(payload)
    stage = {
        "stage_id": f"stage-{uuid4().hex[:8]}",
        "symbol": _symbol(payload.get("symbol")),
        "side": str(payload.get("side", "BUY")).upper(),
        "quantity": float(payload.get("quantity", 1)),
        "order_type": payload.get("order_type", "limit"),
        "limit_price": payload.get("limit_price", _price(_symbol(payload.get("symbol")))),
        "status": "approval_required" if precheck["allowed"] else "blocked",
        "approvals": [{"role": "maker", "status": "prepared", "actor": "sandbox-user"}],
        "compliance_holds": [] if precheck["allowed"] else precheck["violations"],
        "allocations": payload.get("allocations", {"ALP-SANDBOX-001": 0.6, "IBKR-PAPER-042": 0.4}),
        "notes": payload.get("notes", ""),
        "pre_trade": precheck,
        "audit_id": _audit("stage"),
        "created_at": _now().isoformat(),
    }
    STAGED_ORDERS.insert(0, stage)
    return stage


def approve_staged_order(stage_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    for order in STAGED_ORDERS:
        if order["stage_id"] == stage_id:
            if order["status"] == "blocked":
                return {"status": "blocked", "stage_id": stage_id, "reason": "Compliance holds must be resolved first."}
            order["status"] = "approved"
            order.setdefault("approvals", []).append({"role": "checker", "status": "approved", "actor": payload.get("actor", "approver")})
            return {"status": "approved", "order": order, "audit_id": _audit("stage-approve")}
    return {"status": "not_found", "stage_id": stage_id}


def release_staged_order(stage_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    for order in STAGED_ORDERS:
        if order["stage_id"] == stage_id:
            if order["status"] != "approved" or not payload.get("confirmed", False):
                return {"status": "confirmation_or_approval_required", "stage_id": stage_id}
            order["status"] = "released_to_sandbox"
            return {"status": "released_to_sandbox", "order": order, "allocation_review": {"status": "pending_fills"}, "audit_id": _audit("stage-release")}
    return {"status": "not_found", "stage_id": stage_id}


def data_quality_dashboard() -> dict[str, Any]:
    return {
        "generated_at": _now().isoformat(),
        "overall_status": "degraded",
        "vendor_health": [
            {"source": "polygon", "status": "healthy", "latency_ms": 92, "freshness_score": 0.96},
            {"source": "alpha_vantage", "status": "degraded", "latency_ms": 740, "freshness_score": 0.61},
            {"source": "broker_positions", "status": "healthy", "latency_ms": 128, "freshness_score": 0.91},
        ],
        "checks": [
            {"name": "missing_bars", "status": "review", "symbols": ["JPM"], "detail": "One late 1m bar backfilled."},
            {"name": "corporate_actions", "status": "passed", "symbols": []},
            {"name": "model_input_drift", "status": "review", "features": ["relative_volume"], "severity": "medium"},
            {"name": "outliers", "status": "passed", "symbols": []},
        ],
        "source_confidence": [
            {"source": "market_data", "confidence": 0.92, "impacted_signals": []},
            {"source": "news_sentiment", "confidence": 0.74, "impacted_signals": ["NVDA"]},
            {"source": "corporate_actions", "confidence": 0.98, "impacted_signals": []},
        ],
        "signal_policy": {"block_threshold": 0.45, "degrade_threshold": 0.75, "degraded_signals": ["NVDA"], "blocked_signals": []},
    }


def strategy_research(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    universe = [_symbol(symbol) for symbol in payload.get("universe", ["MSFT", "NVDA", "JPM", "SPY"])]
    rules = payload.get("rules", [{"field": "freshness_score", "operator": ">", "value": 0.65}, {"field": "tail_risk", "operator": "<", "value": 0.18}])
    seed = sum(ord(character) for character in "".join(universe)) + len(rules) * 17
    win_rate = 0.52 + (seed % 9) / 100
    return {
        "strategy_id": payload.get("strategy_id", f"strategy-{uuid4().hex[:8]}"),
        "name": payload.get("name", "Fresh signal pullback"),
        "universe": universe,
        "rules": rules,
        "screen_results": [{"symbol": symbol, "passed": index % 2 == 0, "score": _round(0.61 + index * 0.07, 3)} for index, symbol in enumerate(universe)],
        "walk_forward_report": {
            "windows": 8,
            "annualized_return": _round(0.11 + (seed % 7) / 100, 4),
            "max_drawdown": -0.087,
            "sharpe": _round(1.12 + (seed % 5) / 10, 3),
            "win_rate": _round(win_rate, 3),
            "costs_included": True,
        },
        "ai_comparison": {"agreement_rate": 0.68, "outperformance_vs_ai_bps": 42},
        "paper_deploy": {"eligible": win_rate > 0.55, "status": "ready_for_paper" if win_rate > 0.55 else "research_only"},
        "drift_monitor": {"status": "armed", "retire_if_sharpe_below": 0.75},
    }


def deploy_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    research = strategy_research(payload)
    eligible = research["paper_deploy"]["eligible"] and payload.get("confirmed", False)
    return {
        "strategy_id": research["strategy_id"],
        "status": "paper_deployed" if eligible else "confirmation_or_eligibility_required",
        "monitoring": {"drift": "armed", "kill_switch": "linked", "review_frequency": "daily"},
        "audit_id": _audit("strategy-deploy"),
    }


def risk_constitution() -> dict[str, Any]:
    return {
        "rules": RISK_CONSTITUTION_RULES,
        "enforcement": "fail_closed",
        "last_reviewed_at": (_now() - timedelta(days=3)).isoformat(),
        "applies_to": ["single_order", "basket", "strategy", "emergency_release"],
    }


def update_risk_constitution(payload: dict[str, Any]) -> dict[str, Any]:
    rule = {
        "rule_id": payload.get("rule_id", f"risk-{uuid4().hex[:8]}"),
        "rule_type": payload.get("rule_type", "restricted_symbol"),
        "threshold": payload.get("threshold", payload.get("symbol", "TSLA")),
        "enforcement": payload.get("enforcement", "never_override"),
        "enabled": bool(payload.get("enabled", True)),
    }
    RISK_CONSTITUTION_RULES.insert(0, rule)
    return {"status": "saved", "rule": rule, "audit_id": _audit("risk-constitution")}


def evaluate_risk_constitution(payload: dict[str, Any]) -> dict[str, Any]:
    violations = []
    daily_loss = float(payload.get("daily_loss", 0))
    position_pct = float(payload.get("position_pct", 0))
    options_level = int(payload.get("options_level", 0))
    symbol = _symbol(payload.get("symbol"))
    for rule in RISK_CONSTITUTION_RULES:
        if not rule.get("enabled", True):
            continue
        if rule["rule_type"] == "max_daily_loss" and daily_loss <= -float(rule["threshold"]):
            violations.append("max daily loss rule triggered")
        if rule["rule_type"] == "max_position_pct" and position_pct > float(rule["threshold"]):
            violations.append("max position size rule triggered")
        if rule["rule_type"] == "max_options_level" and options_level > int(rule["threshold"]):
            violations.append("options level rule triggered")
        if rule["rule_type"] == "restricted_symbol" and symbol == _symbol(str(rule["threshold"])):
            violations.append(f"{symbol} is restricted by user constitution")
    return {
        "allowed": not violations,
        "status": "allowed" if not violations else "blocked",
        "violations": violations,
        "enforcement": "fail_closed",
        "audit_id": _audit("risk-eval"),
    }


def disclosure_archive(query: str | None = None) -> dict[str, Any]:
    records = [
        {"archive_id": "archive-rec-msft", "record_type": "recommendation", "title": "MSFT hold rationale", "source_refs": ["signal_orchestrator:MSFT"], "model_version": "champion-2026-06", "audit_id": "audit-rec-msft", "created_at": (_now() - timedelta(hours=5)).isoformat()},
        {"archive_id": "archive-disc-options", "record_type": "disclosure", "title": "Options assignment risk acknowledgement", "source_refs": ["disclosure:options"], "model_version": None, "audit_id": "audit-disc-options", "created_at": (_now() - timedelta(days=1)).isoformat()},
        {"archive_id": "archive-alert-broker", "record_type": "alert", "title": "IBKR stale sync warning", "source_refs": ["broker_reconciliation:ibkr"], "model_version": None, "audit_id": "audit-alert-ibkr", "created_at": (_now() - timedelta(minutes=7)).isoformat()},
        {"archive_id": "archive-ai-hedge", "record_type": "ai_response", "title": "Hedged trade copilot response", "source_refs": ["copilot:hedge", "options_suite"], "model_version": "copilot-policy-guarded", "audit_id": "audit-ai-hedge", "created_at": (_now() - timedelta(minutes=22)).isoformat()},
    ]
    if query:
        lowered = query.lower()
        records = [record for record in records if lowered in record["title"].lower() or lowered in record["record_type"].lower()]
    return {
        "records": records,
        "retention_policy": {"default_years": 7, "exportable": True, "privacy_review_required": True},
        "search": {"query": query or "", "count": len(records)},
    }


def emergency_status() -> dict[str, Any]:
    return {
        "trading_paused": EMERGENCY_STATE["trading_paused"],
        "open_order_count": EMERGENCY_STATE["open_order_count"],
        "last_action": EMERGENCY_STATE["last_action"],
        "critical_alerts": [
            {"severity": "critical", "title": "Manual pause available", "detail": "Emergency pause cancels new releases immediately."},
            {"severity": "review", "title": "IBKR sync delay", "detail": "Broker connection requires acknowledgement."},
        ],
        "staged_trade_decisions": [{"stage_id": order["stage_id"], "status": order["status"]} for order in STAGED_ORDERS[:3]],
        "push_ready": True,
    }


def pause_trading(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    EMERGENCY_STATE["trading_paused"] = True
    action = {"action_id": f"emergency-{uuid4().hex[:8]}", "action_type": "pause_trading", "status": "active", "reason": payload.get("reason", "user_requested"), "audit_id": _audit("emergency-pause")}
    EMERGENCY_STATE["last_action"] = action
    return action


def cancel_all_orders(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    canceled = EMERGENCY_STATE["open_order_count"]
    EMERGENCY_STATE["open_order_count"] = 0
    action = {"action_id": f"emergency-{uuid4().hex[:8]}", "action_type": "cancel_all_orders", "status": "submitted", "canceled_orders": canceled, "reason": payload.get("reason", "user_requested"), "audit_id": _audit("emergency-cancel")}
    EMERGENCY_STATE["last_action"] = action
    return action


def emergency_stage_decision(stage_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision", "deny")).lower()
    for order in STAGED_ORDERS:
        if order["stage_id"] == stage_id:
            order["status"] = "approved" if decision == "approve" else "denied_by_emergency_control"
            return {"status": order["status"], "stage_id": stage_id, "audit_id": _audit("emergency-stage")}
    return {"status": "not_found", "stage_id": stage_id}


def execution_and_quality_evidence() -> dict[str, Any]:
    quality = execution_quality()
    return {
        "fill_quality": quality["summary"],
        "best_execution_anchor": "FINRA Rule 5310",
        "market_access_anchor": "SEC Rule 15c3-5",
        "evidence_export": quality["evidence_export"],
    }
