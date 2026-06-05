from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(UTC)


def _symbol(value: str | None, fallback: str = "MSFT") -> str:
    raw = (value or fallback).strip().upper()
    return raw if raw else fallback


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


POSITIONS: list[dict[str, Any]] = [
    {
        "symbol": "MSFT",
        "asset_type": "equity",
        "quantity": 120,
        "average_cost": 338.25,
        "last_price": 421.14,
        "sector": "technology",
        "factor_exposures": {"quality": 0.42, "growth": 0.31, "momentum": 0.18},
    },
    {
        "symbol": "NVDA",
        "asset_type": "equity",
        "quantity": 80,
        "average_cost": 72.4,
        "last_price": 124.7,
        "sector": "technology",
        "factor_exposures": {"growth": 0.51, "momentum": 0.38, "size": 0.22},
    },
    {
        "symbol": "JPM",
        "asset_type": "equity",
        "quantity": 90,
        "average_cost": 184.1,
        "last_price": 207.55,
        "sector": "financials",
        "factor_exposures": {"value": 0.35, "quality": 0.24, "low_vol": 0.14},
    },
    {
        "symbol": "SPY",
        "asset_type": "etf",
        "quantity": 70,
        "average_cost": 508.8,
        "last_price": 544.2,
        "sector": "broad_market",
        "factor_exposures": {"market": 1.0, "size": 0.16, "quality": 0.12},
    },
]

OPEN_ORDERS: list[dict[str, Any]] = [
    {
        "order_id": "ord-bracket-msft",
        "symbol": "MSFT",
        "side": "SELL",
        "quantity": 40,
        "order_type": "bracket",
        "status": "working",
        "broker": "alpaca",
        "time_in_force": "gtc",
        "limit_price": 448.0,
        "stop_price": 398.0,
        "extended_hours": False,
        "routing_decision": {"strategy": "LIMIT", "reason": "profit_target_with_stop_protection"},
        "audit_id": "audit-ord-bracket-msft",
        "created_at": (_now() - timedelta(hours=2)).isoformat(),
    },
    {
        "order_id": "ord-vwap-nvda",
        "symbol": "NVDA",
        "side": "BUY",
        "quantity": 60,
        "order_type": "VWAP",
        "status": "partially_filled",
        "broker": "ibkr",
        "time_in_force": "day",
        "limit_price": 126.2,
        "extended_hours": False,
        "routing_decision": {"strategy": "VWAP", "reason": "medium_participation_volume_slicing"},
        "audit_id": "audit-ord-vwap-nvda",
        "created_at": (_now() - timedelta(minutes=44)).isoformat(),
    },
]

FILLS: list[dict[str, Any]] = [
    {
        "fill_id": "fill-msft-1",
        "order_id": "ord-closed-msft",
        "symbol": "MSFT",
        "side": "BUY",
        "quantity": 20,
        "arrival_price": 419.92,
        "fill_price": 419.88,
        "venue": "ARCA",
        "spread_at_arrival_bps": 2.4,
        "execution_speed_ms": 183,
        "filled_at": (_now() - timedelta(hours=5)).isoformat(),
    },
    {
        "fill_id": "fill-jpm-1",
        "order_id": "ord-closed-jpm",
        "symbol": "JPM",
        "side": "SELL",
        "quantity": 30,
        "arrival_price": 207.48,
        "fill_price": 207.5,
        "venue": "NYSE",
        "spread_at_arrival_bps": 1.8,
        "execution_speed_ms": 211,
        "filled_at": (_now() - timedelta(days=1, hours=1)).isoformat(),
    },
]

WATCHLISTS: list[dict[str, Any]] = [
    {
        "watchlist_id": "wl-core-ai",
        "name": "AI leaders",
        "symbols": ["MSFT", "NVDA", "AMD", "GOOGL"],
        "criteria": {"min_confidence": 0.62, "factor": "growth"},
        "created_at": (_now() - timedelta(days=8)).isoformat(),
    },
    {
        "watchlist_id": "wl-income",
        "name": "Income candidates",
        "symbols": ["JPM", "XOM", "SPY"],
        "criteria": {"dividend_yield_min": 0.02, "max_tail_risk": 0.18},
        "created_at": (_now() - timedelta(days=21)).isoformat(),
    },
]

JOURNAL: list[dict[str, Any]] = [
    {
        "journal_id": "journal-v2-1",
        "symbol": "MSFT",
        "setup": "quality compounder pullback",
        "pre_trade_plan": "Buy only inside entry zone; stop below prior swing low.",
        "thesis": "Cloud margin stabilization and AI revenue durability support positive skew.",
        "confidence_tag": "high",
        "emotion_tag": "calm",
        "rule_checklist": ["position_size_checked", "event_risk_checked", "stop_defined"],
        "mae": -0.012,
        "mfe": 0.038,
        "expectancy": 0.014,
        "setup_quality": 86,
        "ai_post_trade_review": "Execution followed plan; consider tighter alert around event risk.",
        "created_at": (_now() - timedelta(days=2)).isoformat(),
    }
]


def _positions_with_pnl() -> list[dict[str, Any]]:
    rows = []
    for position in POSITIONS:
        market_value = position["quantity"] * position["last_price"]
        cost_basis = position["quantity"] * position["average_cost"]
        rows.append(
            {
                **position,
                "market_value": _round(market_value),
                "unrealized_pnl": _round(market_value - cost_basis),
                "day_pnl": _round(market_value * (0.004 if position["symbol"] in {"MSFT", "JPM"} else -0.006)),
            }
        )
    return rows


def _exposure_breakdown(positions: list[dict[str, Any]]) -> dict[str, Any]:
    total = max(sum(position["market_value"] for position in positions), 1.0)
    sectors: dict[str, float] = {}
    factors: dict[str, float] = {}
    for position in positions:
        weight = position["market_value"] / total
        sectors[position["sector"]] = sectors.get(position["sector"], 0.0) + weight
        for factor, exposure in position.get("factor_exposures", {}).items():
            factors[factor] = factors.get(factor, 0.0) + weight * float(exposure)
    return {
        "sectors": {key: _round(value, 4) for key, value in sectors.items()},
        "factors": {key: _round(value, 4) for key, value in factors.items()},
        "gross_exposure": _round(total / 150000, 4),
        "net_exposure": _round((total - 18420) / 150000, 4),
    }


def portfolio_command_center() -> dict[str, Any]:
    positions = _positions_with_pnl()
    market_value = sum(position["market_value"] for position in positions)
    cash = 18420.0
    equity = market_value + cash
    return {
        "generated_at": _now().isoformat(),
        "mode": "sandbox",
        "accounts": [
            {
                "broker": "alpaca",
                "account_id": "ALP-SANDBOX-001",
                "mode": "sandbox",
                "status": "healthy",
                "equity": _round(equity * 0.58),
                "cash": 10250.0,
                "buying_power": 41000.0,
                "margin_requirement": 28600.0,
                "last_sync_at": (_now() - timedelta(seconds=42)).isoformat(),
            },
            {
                "broker": "ibkr",
                "account_id": "IBKR-PAPER-042",
                "mode": "sandbox",
                "status": "attention",
                "equity": _round(equity * 0.42),
                "cash": 8170.0,
                "buying_power": 28600.0,
                "margin_requirement": 21400.0,
                "last_sync_at": (_now() - timedelta(minutes=7)).isoformat(),
            },
        ],
        "totals": {
            "equity": _round(equity),
            "cash": cash,
            "buying_power": 69600.0,
            "realized_pnl": 3820.42,
            "unrealized_pnl": _round(sum(position["unrealized_pnl"] for position in positions)),
            "day_pnl": _round(sum(position["day_pnl"] for position in positions)),
        },
        "positions": positions,
        "exposure": _exposure_breakdown(positions),
        "open_orders": OPEN_ORDERS,
        "recent_fills": FILLS,
        "risk_alerts": [
            {
                "severity": "review",
                "title": "Technology concentration",
                "detail": "Technology exposure is above the balanced-profile target.",
            },
            {
                "severity": "info",
                "title": "IBKR sync delay",
                "detail": "Last sandbox sync is older than 5 minutes.",
            },
        ],
        "broker_health": broker_reconciliation()["connections"],
    }


def order_blotter() -> dict[str, Any]:
    history = [
        *OPEN_ORDERS,
        {
            "order_id": "ord-closed-msft",
            "symbol": "MSFT",
            "side": "BUY",
            "quantity": 20,
            "order_type": "limit",
            "status": "filled",
            "broker": "alpaca",
            "time_in_force": "day",
            "limit_price": 420.0,
            "routing_decision": {"strategy": "LIMIT", "reason": "explicit_price_control"},
            "audit_id": "audit-ord-closed-msft",
            "created_at": (_now() - timedelta(hours=6)).isoformat(),
        },
    ]
    return {
        "open_orders": OPEN_ORDERS,
        "order_history": history,
        "fills": FILLS,
        "blocked_examples": [
            {
                "symbol": "TSLA",
                "reason": "Order blocked: concentration limit would exceed 35%.",
                "control": "dynamic_margin_and_concentration",
            }
        ],
    }


def submit_order_ticket(payload: dict[str, Any]) -> dict[str, Any]:
    margin = margin_snapshot(payload)
    allowed = not margin["violations"]
    order_id = f"ord-{uuid4().hex[:8]}"
    order = {
        "order_id": order_id,
        "symbol": _symbol(payload.get("symbol")),
        "side": str(payload.get("side", "BUY")).upper(),
        "quantity": float(payload.get("quantity", 1)),
        "order_type": str(payload.get("order_type", "market")).lower(),
        "status": "working" if allowed else "rejected",
        "broker": payload.get("broker", "alpaca"),
        "time_in_force": payload.get("time_in_force", "day"),
        "extended_hours": bool(payload.get("extended_hours", False)),
        "limit_price": payload.get("limit_price"),
        "stop_price": payload.get("stop_price"),
        "blocked_reason": "; ".join(margin["violations"]) if not allowed else None,
        "routing_decision": {
            "strategy": str(payload.get("order_type", "market")).upper(),
            "reason": "user_selected_strategy_passed_pretrade_controls" if allowed else "pretrade_controls_failed",
        },
        "audit_id": f"audit-{uuid4().hex[:10]}",
        "created_at": _now().isoformat(),
    }
    if allowed:
        OPEN_ORDERS.insert(0, order)
    return {"status": order["status"], "order": order, "precheck": margin}


def cancel_order(order_id: str) -> dict[str, Any]:
    for order in OPEN_ORDERS:
        if order["order_id"] == order_id:
            order["status"] = "canceled"
            return {"status": "canceled", "order_id": order_id, "audit_id": f"audit-{uuid4().hex[:10]}"}
    return {"status": "not_found", "order_id": order_id}


def replace_order(order_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    for order in OPEN_ORDERS:
        if order["order_id"] == order_id:
            if payload.get("quantity") is not None:
                order["quantity"] = float(payload["quantity"])
            if payload.get("limit_price") is not None:
                order["limit_price"] = float(payload["limit_price"])
            order["status"] = "replaced"
            order["audit_id"] = f"audit-{uuid4().hex[:10]}"
            return {"status": "replaced", "order": order}
    return {"status": "not_found", "order_id": order_id}


def options_approval(payload: dict[str, Any]) -> dict[str, Any]:
    experience = str(payload.get("experience", "intermediate")).lower()
    objective = str(payload.get("objective", "income")).lower()
    acknowledged = bool(payload.get("risk_disclosure_acknowledged", False))
    level = 0
    if acknowledged and experience in {"intermediate", "advanced"}:
        level = 1
    if acknowledged and experience == "advanced" and objective in {"growth", "income", "hedging"}:
        level = 2
    return {
        "approved": level > 0,
        "options_level": level,
        "allowed_strategies": {
            0: [],
            1: ["covered_call", "cash_secured_put"],
            2: ["covered_call", "cash_secured_put", "defined_risk_spread"],
        }[level],
        "blocked_strategies": ["uncovered_short_call", "undefined_risk_spread"],
        "required_disclosures": ["occ_characteristics_and_risks", "options_strategy_risk", "assignment_risk"],
        "reason": "Risk disclosure and options experience recorded." if level else "Options disclosure acknowledgement is required.",
    }


def options_suite(symbol: str = "MSFT") -> dict[str, Any]:
    underlying = _symbol(symbol)
    base_price = {"MSFT": 421.14, "NVDA": 124.7, "JPM": 207.55}.get(underlying, 150.0)
    expirations = [date.today() + timedelta(days=days) for days in (30, 60)]
    contracts = []
    for expiration in expirations:
        for offset in (-10, 0, 10):
            strike = round(base_price + offset, 2)
            for option_type in ("call", "put"):
                moneyness = (base_price - strike) / base_price
                delta = 0.52 + moneyness if option_type == "call" else -0.48 + moneyness
                premium = max(1.15, abs(offset) * 0.22 + base_price * 0.018)
                contracts.append(
                    {
                        "option_symbol": f"{underlying}-{expiration.isoformat()}-{strike}-{option_type[0].upper()}",
                        "underlying": underlying,
                        "expiration": expiration.isoformat(),
                        "strike": strike,
                        "option_type": option_type,
                        "bid": _round(premium - 0.08),
                        "ask": _round(premium + 0.08),
                        "volume": int(1200 + abs(offset) * 24),
                        "open_interest": int(6000 + abs(offset) * 42),
                        "implied_volatility": _round(0.28 + abs(offset) / base_price, 4),
                        "delta": _round(max(min(delta, 0.95), -0.95), 4),
                        "gamma": 0.018,
                        "theta": -0.041,
                        "vega": 0.114,
                    }
                )
    call = next(contract for contract in contracts if contract["option_type"] == "call" and contract["strike"] >= base_price)
    return {
        "underlying": {"symbol": underlying, "last_price": base_price, "iv_rank": 42, "skew": "call_bid_neutral"},
        "approval": options_approval({"experience": "intermediate", "risk_disclosure_acknowledged": True}),
        "chain": contracts,
        "strategy_builder": [
            {
                "strategy": "covered_call",
                "contracts": [call["option_symbol"]],
                "max_gain": _round((call["strike"] - base_price + call["bid"]) * 100),
                "max_loss": _round((base_price - call["bid"]) * 100),
                "breakeven": _round(base_price - call["bid"]),
                "probability_of_profit": 0.61,
                "assignment_risk": "medium",
            },
            {
                "strategy": "cash_secured_put",
                "contracts": [contract["option_symbol"] for contract in contracts if contract["option_type"] == "put"][1:2],
                "max_gain": 620.0,
                "cash_required": _round(base_price * 100 * 0.92),
                "probability_of_profit": 0.58,
                "assignment_risk": "medium",
            },
        ],
    }


def margin_snapshot(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    account_equity = float(payload.get("equity", 150000))
    buying_power = float(payload.get("buying_power", 69600))
    price = float(payload.get("current_price", payload.get("limit_price") or 100))
    quantity = float(payload.get("quantity", 0) or 0)
    notional = price * quantity
    broker = str(payload.get("broker", "alpaca"))
    asset_type = str(payload.get("asset_type", "equity")).lower()
    concentration_after = float(payload.get("concentration_after", min(0.52, notional / max(account_equity, 1))))
    base_requirement = 0.5 if asset_type == "equity" else 1.0
    if asset_type == "option":
        base_requirement = 1.0
    maintenance = account_equity * 0.28
    intraday_requirement = notional * base_requirement
    deficiency = max(0.0, intraday_requirement - buying_power)
    violations = []
    if deficiency > 0:
        violations.append(f"intraday margin deficiency ${deficiency:,.2f}")
    if concentration_after > 0.35:
        violations.append("concentration limit would exceed 35%")
    if asset_type == "option" and not payload.get("options_approved", False):
        violations.append("options approval is required")
    liquidation_risk = "high" if deficiency > account_equity * 0.1 else "medium" if violations else "low"
    return {
        "broker": broker,
        "account_id": payload.get("account_id", "ALP-SANDBOX-001"),
        "equity": _round(account_equity),
        "buying_power": _round(buying_power),
        "maintenance_margin": _round(maintenance),
        "intraday_margin_requirement": _round(intraday_requirement),
        "intraday_margin_deficiency": _round(deficiency),
        "liquidation_risk": liquidation_risk,
        "ruleset": "FINRA_intraday_margin_transition_sandbox",
        "effective_date": "2026-06-04",
        "transition_phase_in_until": "2027-10-20",
        "violations": violations,
        "allowed": not violations,
    }


def execution_quality() -> dict[str, Any]:
    rows = []
    for fill in FILLS:
        direction = 1 if fill["side"] == "BUY" else -1
        slippage_bps = ((fill["fill_price"] - fill["arrival_price"]) / fill["arrival_price"]) * 10000 * direction
        rows.append(
            {
                **fill,
                "slippage_bps": _round(slippage_bps, 3),
                "price_improvement_bps": _round(max(-slippage_bps, 0), 3),
                "smart_router_reason": "spread_capture" if slippage_bps <= 0 else "liquidity_priority",
            }
        )
    avg_slippage = sum(row["slippage_bps"] for row in rows) / max(len(rows), 1)
    return {
        "summary": {
            "fills": len(rows),
            "average_slippage_bps": _round(avg_slippage, 3),
            "average_speed_ms": int(sum(row["execution_speed_ms"] for row in rows) / max(len(rows), 1)),
            "price_improvement_rate": _round(sum(1 for row in rows if row["price_improvement_bps"] > 0) / max(len(rows), 1), 4),
        },
        "fills": rows,
        "evidence_export": "execution-quality-sandbox.json",
    }


def market_replay(symbol: str = "MSFT", session_date: str | None = None) -> dict[str, Any]:
    underlying = _symbol(symbol)
    start_price = {"MSFT": 418.0, "NVDA": 122.2, "JPM": 206.4}.get(underlying, 150.0)
    bars = []
    current = start_price
    replay_date = session_date or date.today().isoformat()
    for index in range(24):
        drift = math.sin(index / 3) * 0.35 + index * 0.03
        open_price = current
        close = start_price + drift
        high = max(open_price, close) + 0.42
        low = min(open_price, close) - 0.38
        bars.append(
            {
                "time": f"{replay_date}T{9 + (30 + index * 15) // 60:02d}:{(30 + index * 15) % 60:02d}:00Z",
                "open": _round(open_price),
                "high": _round(high),
                "low": _round(low),
                "close": _round(close),
                "volume": 120000 + index * 7800,
            }
        )
        current = close
    return {
        "symbol": underlying,
        "session_date": replay_date,
        "bars": bars,
        "ai_signal_at_start": {
            "signal": "BUY",
            "confidence": 0.71,
            "entry_zone": {"low": _round(start_price * 0.99), "high": _round(start_price * 1.01)},
            "stop_loss": _round(start_price * 0.95),
            "take_profit": _round(start_price * 1.07),
        },
        "simulated_trades": [],
    }


def replay_trade(payload: dict[str, Any]) -> dict[str, Any]:
    price = float(payload.get("price", 100))
    quantity = float(payload.get("quantity", 10))
    side = str(payload.get("side", "BUY")).upper()
    return {
        "trade_id": f"replay-{uuid4().hex[:8]}",
        "symbol": _symbol(payload.get("symbol")),
        "side": side,
        "quantity": quantity,
        "price": price,
        "notional": _round(price * quantity),
        "cost_model": {"commission": 0.0, "slippage_bps": 2.1, "market_impact_bps": 0.4},
        "ai_signal_alignment": "aligned" if side == "BUY" else "contrarian",
    }


def watchlists_and_heatmaps() -> dict[str, Any]:
    return {
        "watchlists": WATCHLISTS,
        "screeners": [
            {"name": "High conviction low tail risk", "criteria": {"min_confidence": 0.7, "max_tail_risk": 0.14}},
            {"name": "Unusual volume gaps", "criteria": {"relative_volume_min": 2.0, "gap_percent_min": 3.0}},
        ],
        "heatmaps": {
            "sectors": [
                {"name": "technology", "return_1d": 0.012, "signal_strength": 0.73},
                {"name": "financials", "return_1d": 0.004, "signal_strength": 0.58},
                {"name": "energy", "return_1d": -0.006, "signal_strength": 0.42},
            ],
            "factors": [
                {"name": "quality", "return_1d": 0.007, "exposure": 0.31},
                {"name": "momentum", "return_1d": 0.011, "exposure": 0.27},
                {"name": "value", "return_1d": -0.002, "exposure": 0.18},
            ],
        },
        "why_moving": [
            {"symbol": "NVDA", "reason": "Unusual volume and positive analyst revision detected."},
            {"symbol": "JPM", "reason": "Rates-sensitive financials are reacting to macro calendar repricing."},
        ],
    }


def event_calendar() -> dict[str, Any]:
    base = _now()
    return {
        "events": [
            {
                "event_id": "evt-msft-earnings",
                "symbol": "MSFT",
                "event_type": "earnings",
                "title": "MSFT earnings",
                "starts_at": (base + timedelta(days=9)).isoformat(),
                "impact": "high",
                "linked_risks": ["gap_risk", "option_iv_crush", "signal_decay"],
                "source": "earnings_calendar",
            },
            {
                "event_id": "evt-fomc",
                "symbol": None,
                "event_type": "macro",
                "title": "FOMC rate decision",
                "starts_at": (base + timedelta(days=13)).isoformat(),
                "impact": "high",
                "linked_risks": ["duration_risk", "market_beta"],
                "source": "economic_calendar",
            },
            {
                "event_id": "evt-jpm-dividend",
                "symbol": "JPM",
                "event_type": "dividend",
                "title": "JPM ex-dividend window",
                "starts_at": (base + timedelta(days=18)).isoformat(),
                "impact": "medium",
                "linked_risks": ["tax_lot", "income_reinvestment"],
                "source": "corporate_actions",
            },
        ]
    }


def trade_journal_v2() -> dict[str, Any]:
    return {
        "entries": JOURNAL,
        "analytics": {
            "average_setup_quality": _round(sum(entry["setup_quality"] for entry in JOURNAL) / max(len(JOURNAL), 1)),
            "expectancy": _round(sum(entry["expectancy"] for entry in JOURNAL) / max(len(JOURNAL), 1), 4),
            "most_common_rule_break": "none_recorded",
        },
    }


def add_journal_plan(payload: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "journal_id": f"journal-v2-{len(JOURNAL) + 1}",
        "symbol": _symbol(payload.get("symbol")),
        "setup": payload.get("setup", "manual plan"),
        "pre_trade_plan": payload.get("pre_trade_plan", "Plan pending."),
        "thesis": payload.get("thesis", "Thesis pending."),
        "confidence_tag": payload.get("confidence_tag", "medium"),
        "emotion_tag": payload.get("emotion_tag", "neutral"),
        "rule_checklist": payload.get("rule_checklist", ["position_size_checked"]),
        "mae": 0.0,
        "mfe": 0.0,
        "expectancy": 0.0,
        "setup_quality": int(payload.get("setup_quality", 70)),
        "ai_post_trade_review": "Review will be generated after fills are reconciled.",
        "created_at": _now().isoformat(),
    }
    JOURNAL.insert(0, entry)
    return entry


def copilot_response(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    lower = question.lower()
    if "hold" in lower or "msft" in lower:
        answer = "MSFT is supported by quality and growth factors, but position sizing should respect current technology concentration and the upcoming earnings catalyst."
        citations = ["signal_orchestrator:MSFT", "portfolio_command_center:exposure", "event_calendar:evt-msft-earnings"]
    elif "rates" in lower or "50" in lower:
        answer = "A 50 bps rate shock would likely raise duration and beta risk. The current portfolio impact is medium because SPY and technology exposure dominate financial diversification."
        citations = ["macro_agent:rate_shock", "portfolio_risk:factor_exposure"]
    elif "hedge" in lower:
        answer = "A sandbox hedge candidate is a defined-risk put spread or reduced technology notional. Any trade would require explicit confirmation and pass risk, suitability, and options-approval gates."
        citations = ["options_suite:defined_risk_spread", "execution_precheck:guardrails"]
    else:
        answer = "I can answer portfolio, signal, risk, replay, journal, and disclosure questions using audited sandbox data. Trade-affecting actions require confirmation and pre-trade controls."
        citations = ["compliance_center:guardrails"]
    return {
        "answer": answer,
        "citations": citations,
        "guardrails": {
            "can_place_trade": False,
            "requires_explicit_confirmation": True,
            "checks": ["suitability", "risk_limits", "stale_signal", "kill_switch", "broker_connectivity"],
        },
        "audit_id": f"audit-copilot-{uuid4().hex[:8]}",
    }


def compliance_center() -> dict[str, Any]:
    return {
        "platform_status": "research_and_sandbox_execution",
        "recommendation_basis": [
            "agent_scores",
            "probability_distribution",
            "tail_risk",
            "factor_exposure",
            "signal_freshness",
            "model_version",
            "data_snapshot",
        ],
        "fees_and_conflicts": [
            "Broker commissions, exchange fees, spread costs, and payment-for-order-flow conflicts must be disclosed by connected brokers.",
            "Sandbox execution quality is illustrative until broker certification evidence is accepted.",
        ],
        "risk_profile_fit": {
            "status": "review",
            "reason": "Technology concentration exceeds balanced profile target.",
        },
        "attestations": [
            {
                "disclosure_id": "disc-research-not-advice",
                "title": "Research and sandbox workflow limitation",
                "status": "required",
                "required_for": ["research", "paper", "live_request"],
            },
            {
                "disclosure_id": "disc-options-risk",
                "title": "Options strategy and assignment risk",
                "status": "required",
                "required_for": ["options"],
            },
            {
                "disclosure_id": "disc-automation",
                "title": "Automated trading consent",
                "status": "required",
                "required_for": ["automated_live"],
            },
        ],
        "regulatory_design_anchors": ["FINRA Rule 5310", "FINRA Rule 2360", "SEC Regulation Best Interest"],
    }


def broker_reconciliation() -> dict[str, Any]:
    return {
        "generated_at": _now().isoformat(),
        "connections": [
            {
                "broker": "alpaca",
                "mode": "sandbox",
                "status": "healthy",
                "last_sync_at": (_now() - timedelta(seconds=42)).isoformat(),
                "mismatches": 0,
            },
            {
                "broker": "ibkr",
                "mode": "sandbox",
                "status": "attention",
                "last_sync_at": (_now() - timedelta(minutes=7)).isoformat(),
                "mismatches": 1,
            },
        ],
        "checks": [
            {"name": "balances", "status": "passed", "difference": 0.0},
            {"name": "positions", "status": "review", "difference": 124.7, "detail": "NVDA partial fill pending broker finalization."},
            {"name": "orders", "status": "passed", "difference": 0.0},
            {"name": "corporate_actions", "status": "passed", "difference": 0.0},
        ],
        "alerts": [
            {
                "severity": "review",
                "title": "Partial fill awaiting broker finalization",
                "detail": "IBKR sandbox NVDA child order has not finalized all fill quantities.",
            }
        ],
    }
