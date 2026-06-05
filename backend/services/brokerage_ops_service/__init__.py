from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.services.trader_operating_system import portfolio_command_center
from backend.services.workstation_service import market_microstructure, pause_trading, pre_trade_control


def _now() -> datetime:
    return datetime.now(UTC)


def _audit(prefix: str) -> str:
    return f"audit-{prefix}-{uuid4().hex[:10]}"


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _symbol(value: str | None, fallback: str = "MSFT") -> str:
    raw = (value or fallback).strip().upper()
    return raw if raw else fallback


def _price(symbol: str) -> float:
    return {"MSFT": 421.14, "NVDA": 124.7, "JPM": 207.55, "SPY": 544.2, "TSLA": 188.4, "GME": 28.5}.get(symbol, 100.0)


CASH_TRANSFERS: list[dict[str, Any]] = [
    {
        "transfer_id": "transfer-ach-001",
        "direction": "deposit",
        "method": "ach",
        "amount": 5000.0,
        "status": "settling",
        "submitted_at": (_now() - timedelta(days=1)).isoformat(),
        "settlement_date": (date.today() + timedelta(days=1)).isoformat(),
        "audit_id": "audit-transfer-ach-001",
    }
]

CORPORATE_ACTION_ELECTIONS: list[dict[str, Any]] = []
ADMIN_REVIEWS: list[dict[str, Any]] = [
    {
        "review_id": "admin-risk-001",
        "review_type": "risk_override",
        "status": "open",
        "severity": "review",
        "subject_ref": "order-msft-bracket",
        "audit_id": "audit-admin-risk-001",
    }
]
SUPPORT_CASES: list[dict[str, Any]] = [
    {
        "case_id": "case-reject-001",
        "category": "order_rejection",
        "status": "waiting_on_platform",
        "subject": "Why was GME short sale rejected?",
        "messages": [{"author": "system", "text": "Locate was required before short-sale release."}],
        "audit_id": "audit-case-reject-001",
    }
]
RECURRING_PLANS: list[dict[str, Any]] = [
    {
        "plan_id": "plan-msft-monthly",
        "symbol": "MSFT",
        "dollar_amount": 250.0,
        "cadence": "monthly",
        "status": "active_sandbox",
        "rules": {"fractional": True, "auto_invest_cash": True},
        "audit_id": "audit-plan-msft-monthly",
    }
]
CONDITIONAL_ORDERS: list[dict[str, Any]] = []
MOBILE_STATE: dict[str, Any] = {
    "trading_paused": False,
    "last_mobile_action": None,
}


def brokerage_ops_overview() -> dict[str, Any]:
    command = portfolio_command_center()
    return {
        "generated_at": _now().isoformat(),
        "mode": "sandbox",
        "cash": {"settled": 42800.0, "unsettled": 7400.0, "buying_power": command["totals"]["buying_power"]},
        "modules": [
            {"id": "cash", "label": "Cash and Settlement", "status": "sandbox"},
            {"id": "chart", "label": "Chart Trading", "status": "precheck_required"},
            {"id": "corporate_actions", "label": "Corporate Actions", "status": "ready"},
            {"id": "documents", "label": "Statements and Tax Docs", "status": "ready"},
            {"id": "admin", "label": "Supervision", "status": "role_gated"},
            {"id": "surveillance", "label": "Surveillance", "status": "monitoring"},
            {"id": "entitlements", "label": "Market Data Entitlements", "status": "enforcing"},
            {"id": "recurring", "label": "Recurring Investing", "status": "sandbox"},
            {"id": "conditional_orders", "label": "Conditional Orders", "status": "simulation_required"},
            {"id": "reports", "label": "Client Reports", "status": "ready"},
            {"id": "mobile", "label": "Mobile Companion", "status": "push_ready"},
            {"id": "support", "label": "Support and Disputes", "status": "ready"},
        ],
        "fail_closed_gates": [
            "m10_live_trading_evidence",
            "bank_or_broker_integration_evidence",
            "cash_available",
            "pre_trade_control",
            "market_data_entitlement",
            "immutable_audit_record",
        ],
    }


def cash_settlement_center() -> dict[str, Any]:
    today = date.today()
    ledger = [
        {"ledger_id": "ledger-opening", "entry_type": "opening_cash", "amount": 38800.0, "settled": True, "description": "Opening settled cash", "audit_id": "audit-ledger-opening", "posted_at": (_now() - timedelta(days=2)).isoformat()},
        {"ledger_id": "ledger-msft-sale", "entry_type": "trade_sale", "amount": 7400.0, "settled": False, "description": "MSFT sale proceeds awaiting T+1 settlement", "audit_id": "audit-ledger-msft-sale", "posted_at": (_now() - timedelta(hours=5)).isoformat()},
        {"ledger_id": "ledger-ach", "entry_type": "ach_deposit", "amount": 5000.0, "settled": False, "description": "ACH deposit in progress", "audit_id": "audit-ledger-ach", "posted_at": (_now() - timedelta(days=1)).isoformat()},
    ]
    unsettled = sum(entry["amount"] for entry in ledger if not entry["settled"])
    settled = sum(entry["amount"] for entry in ledger if entry["settled"])
    return {
        "funding_accounts": [
            {
                "funding_account_id": "funding-ach-primary",
                "account_type": "checking",
                "institution_name": "Sandbox National Bank",
                "masked_account": "****4821",
                "status": "verified_for_sandbox",
                "verification_status": "micro_deposit_sandbox",
                "live_transfer_enabled": False,
                "audit_id": "audit-funding-ach-primary",
            }
        ],
        "cash_summary": {
            "settled_cash": settled,
            "unsettled_cash": unsettled,
            "cash_available_to_withdraw": 38800.0,
            "buying_power_before_pending": 69600.0,
            "buying_power_after_pending": 74600.0,
            "currency": "USD",
        },
        "transfer_statuses": CASH_TRANSFERS,
        "settlement_lots": [
            {
                "settlement_id": "settle-msft-sale",
                "symbol": "MSFT",
                "quantity": 18,
                "trade_date": today.isoformat(),
                "settlement_date": (today + timedelta(days=1)).isoformat(),
                "cash_effect": 7400.0,
                "status": "pending_t_plus_1",
            }
        ],
        "ledger_history": ledger,
        "warnings": [
            {"type": "good_faith", "severity": "review", "detail": "Do not use unsettled sale proceeds for a same-day round trip."},
            {"type": "free_riding", "severity": "block", "detail": "Withdrawals are limited to settled cash until T+1 completes."},
        ],
        "live_transfer_gate": {
            "enabled": False,
            "blocked_reason": "Live cash movement requires M10 evidence, bank integration approval, and audit attestation.",
        },
        "audit_id": _audit("cash-center"),
    }


def create_cash_transfer(payload: dict[str, Any]) -> dict[str, Any]:
    live_requested = bool(payload.get("live", False))
    amount = float(payload.get("amount", 0))
    method = str(payload.get("method", "ach")).lower()
    direction = str(payload.get("direction", "deposit")).lower()
    if amount <= 0:
        return {"status": "blocked", "blocked_reason": "Transfer amount must be greater than zero.", "audit_id": _audit("cash-transfer-block")}
    if live_requested and not (payload.get("m10_evidence") and payload.get("bank_integration_approved")):
        return {
            "status": "blocked",
            "blocked_reason": "Live transfers fail closed without M10 and bank-integration evidence.",
            "required_evidence": ["m10_live_trading_gate", "bank_integration_approval", "audit_attestation"],
            "audit_id": _audit("cash-transfer-live-block"),
        }
    transfer = {
        "transfer_id": f"transfer-{uuid4().hex[:8]}",
        "direction": direction,
        "method": method,
        "amount": _round(amount),
        "status": "sandbox_scheduled",
        "submitted_at": _now().isoformat(),
        "settlement_date": (date.today() + timedelta(days=1 if method == "wire" else 2)).isoformat(),
        "buying_power_delta": _round(amount if direction == "deposit" else -amount),
        "audit_id": _audit("cash-transfer"),
    }
    CASH_TRANSFERS.insert(0, transfer)
    return transfer


def chart_trading_workspace(symbol: str = "MSFT") -> dict[str, Any]:
    normalized = _symbol(symbol)
    price = _price(normalized)
    entry = _round(price + 0.35)
    stop = _round(price * 0.972)
    target = _round(price * 1.045)
    risk = max(entry - stop, 0.01)
    reward = max(target - entry, 0.01)
    precheck = pre_trade_control({"symbol": normalized, "side": "BUY", "quantity": 10, "limit_price": entry})
    return {
        "layout_id": f"chart-layout-{normalized.lower()}",
        "symbol": normalized,
        "chart_series": [
            {"time": "09:30", "open": _round(price - 1.2), "high": _round(price + 0.4), "low": _round(price - 1.8), "close": _round(price - 0.4), "volume": 840000},
            {"time": "10:30", "open": _round(price - 0.4), "high": _round(price + 0.8), "low": _round(price - 0.9), "close": _round(price + 0.5), "volume": 620000},
            {"time": "11:30", "open": _round(price + 0.5), "high": _round(price + 1.1), "low": _round(price - 0.1), "close": _round(price + 0.3), "volume": 510000},
        ],
        "levels": {"entry": entry, "stop": stop, "target": target},
        "bracket_preview": {
            "entry_order": {"side": "BUY", "quantity": 10, "limit_price": entry},
            "stop_order": {"side": "SELL", "quantity": 10, "stop_price": stop},
            "target_order": {"side": "SELL", "quantity": 10, "limit_price": target},
            "oco_linked": True,
        },
        "risk_reward": {"risk_per_share": _round(risk), "reward_per_share": _round(reward), "ratio": _round(reward / risk, 2)},
        "position_markers": [{"symbol": normalized, "quantity": 95, "average_price": _round(price * 0.86)}],
        "fill_markers": [{"fill_id": "fill-msft-001", "side": "BUY", "price": _round(price * 0.99), "quantity": 20, "time": "10:07"}],
        "vwap": _round(price - 0.18),
        "volume_profile": [{"price": _round(price - 1), "volume": 1280000}, {"price": _round(price), "volume": 1880000}, {"price": _round(price + 1), "volume": 940000}],
        "microstructure": market_microstructure(normalized, {"quantity": 250}),
        "hotkey_safety": {"enabled": False, "requires_modal_confirmation": True, "cooldown_ms": 750},
        "trade_controls": {"buy_enabled": precheck["allowed"], "sell_enabled": precheck["allowed"], "confirmation_required": True},
        "pre_trade": precheck,
        "audit_id": _audit("chart"),
    }


def preview_chart_order(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = _symbol(payload.get("symbol"))
    side = str(payload.get("side", "BUY")).upper()
    quantity = float(payload.get("quantity", 10))
    entry = float(payload.get("entry", _price(symbol)))
    stop = float(payload.get("stop", entry * 0.97))
    target = float(payload.get("target", entry * 1.04))
    risk = abs(entry - stop)
    reward = abs(target - entry)
    precheck = pre_trade_control({"symbol": symbol, "side": side, "quantity": quantity, "limit_price": entry})
    return {
        "status": "ready_for_confirmation" if precheck["allowed"] else "blocked",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_draft": {"order_type": "limit", "limit_price": entry, "stop": stop, "target": target, "time_in_force": payload.get("time_in_force", "day")},
        "risk_reward": {"risk_per_share": _round(risk), "reward_per_share": _round(reward), "ratio": _round(reward / max(risk, 0.01), 2)},
        "estimated_slippage_bps": 1.8,
        "pre_trade": precheck,
        "audit_id": _audit("chart-order-preview"),
    }


def corporate_actions_center() -> dict[str, Any]:
    actions = [
        {
            "action_id": "corp-msft-div-2026q3",
            "symbol": "MSFT",
            "action_type": "dividend",
            "status": "announced",
            "ex_date": (date.today() + timedelta(days=19)).isoformat(),
            "pay_date": (date.today() + timedelta(days=37)).isoformat(),
            "cash_impact": 78.85,
            "election_required": False,
            "tax_lot_impact": "ordinary dividend reportable",
            "event_risk": "low",
            "audit_id": "audit-corp-msft-div",
        },
        {
            "action_id": "corp-jpm-tender-2026",
            "symbol": "JPM",
            "action_type": "tender_offer",
            "status": "election_required",
            "deadline": (_now() + timedelta(days=9)).isoformat(),
            "election_required": True,
            "position_impact": {"shares_eligible": 40, "cash_offer": 216.0},
            "tax_lot_impact": "specific-lot election recommended before submission",
            "event_risk": "medium",
            "audit_id": "audit-corp-jpm-tender",
        },
        {
            "action_id": "corp-nvda-split-watch",
            "symbol": "NVDA",
            "action_type": "split_watch",
            "status": "monitoring",
            "option_adjustment_notice": "No adjustment currently active.",
            "election_required": False,
            "event_risk": "review",
            "audit_id": "audit-corp-nvda-split",
        },
    ]
    return {
        "actions": actions,
        "elections": CORPORATE_ACTION_ELECTIONS,
        "position_links": [{"symbol": action["symbol"], "linked_to_positions": True, "linked_to_tax_lots": True} for action in actions],
        "signal_policy": {"refresh_required_on_event_change": True, "block_open_orders_on_material_terms_change": True},
        "audit_id": _audit("corporate-actions"),
    }


def record_corporate_action_election(action_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    action = next((item for item in corporate_actions_center()["actions"] if item["action_id"] == action_id), None)
    if not action:
        return {"status": "not_found", "action_id": action_id, "audit_id": _audit("corp-election-missing")}
    if action.get("election_required") and not payload.get("election"):
        return {"status": "blocked", "action_id": action_id, "blocked_reason": "Election choice is required.", "audit_id": _audit("corp-election-block")}
    election = {
        "election_id": f"election-{uuid4().hex[:8]}",
        "action_id": action_id,
        "symbol": action["symbol"],
        "election": payload.get("election", "acknowledged"),
        "lot_selection": payload.get("lot_selection", "tax_optimizer_default"),
        "status": "recorded_for_sandbox",
        "recorded_at": _now().isoformat(),
        "audit_id": _audit("corp-election"),
    }
    CORPORATE_ACTION_ELECTIONS.insert(0, election)
    return election


def account_documents_center() -> dict[str, Any]:
    documents = [
        {"document_id": "stmt-daily-2026-06-03", "document_type": "daily_statement", "period": "2026-06-03", "status": "available", "formats": ["html", "pdf", "csv"], "audit_id": "audit-stmt-daily"},
        {"document_id": "confirm-msft-2026-06-03", "document_type": "trade_confirmation", "period": "2026-06-03", "status": "available", "formats": ["html", "pdf"], "audit_id": "audit-confirm-msft"},
        {"document_id": "gainloss-2026-ytd", "document_type": "realized_gain_loss", "period": "2026-YTD", "status": "available", "formats": ["html", "csv"], "audit_id": "audit-gainloss-ytd"},
        {"document_id": "tax-1099-style-2026-draft", "document_type": "1099_style_tax_export", "period": "2026 draft", "status": "draft", "formats": ["csv", "pdf"], "audit_id": "audit-tax-draft"},
    ]
    return {
        "documents": documents,
        "account_history": {"orders": 42, "fills": 38, "dividends": 4, "cash_ledger_entries": 18},
        "retention_policy": {"years": 7, "audit_ready": True, "tamper_evident_hashes": True},
        "audit_id": _audit("account-documents"),
    }


def account_document(document_id: str) -> dict[str, Any]:
    document = next((item for item in account_documents_center()["documents"] if item["document_id"] == document_id), None)
    if not document:
        return {"status": "not_found", "document_id": document_id, "audit_id": _audit("document-missing")}
    return {
        **document,
        "preview": {
            "title": document["document_type"].replace("_", " ").title(),
            "sections": ["balances", "positions", "transactions", "fees", "audit_metadata"],
            "download_urls": {fmt: f"/brokerage-ops/account-documents/{document_id}?format={fmt}" for fmt in document["formats"]},
        },
    }


def admin_console() -> dict[str, Any]:
    return {
        "role_gate": {"required_role": "supervisor", "current_mode": "sandbox_admin", "actions_require_reason": True},
        "users": [{"user_id": "demo", "email": "analyst@example.com", "suitability_status": "complete", "risk_profile": "balanced"}],
        "accounts": [{"account_id": "ALP-SANDBOX-001", "status": "active", "cash_status": "settlement_pending"}],
        "orders": [{"order_id": "order-msft-bracket", "status": "precheck_required", "risk": "medium"}],
        "alerts": [{"alert_id": "alert-entitlement-l2", "severity": "review", "detail": "Level II request blocked for delayed-data user."}],
        "risk_overrides": ADMIN_REVIEWS,
        "disclosures": [{"disclosure_id": "disc-options", "status": "acknowledged"}],
        "suspicious_activity": surveillance_dashboard()["alerts"],
        "broker_outages": [{"broker": "IBKR", "status": "degraded", "started_at": (_now() - timedelta(minutes=14)).isoformat()}],
        "support_incidents": SUPPORT_CASES,
        "emergency_controls": {"pause_trading": True, "cancel_all": True, "audit_required": True},
        "audit_id": _audit("admin-console"),
    }


def create_admin_override(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("confirmed") or not payload.get("reason"):
        return {
            "status": "blocked",
            "blocked_reason": "Admin overrides require explicit confirmation and a reason.",
            "audit_id": _audit("admin-override-block"),
        }
    review = {
        "review_id": f"admin-{uuid4().hex[:8]}",
        "review_type": payload.get("review_type", "risk_override"),
        "status": "queued_for_supervisory_review",
        "severity": payload.get("severity", "review"),
        "subject_ref": payload.get("subject_ref", "order"),
        "reviewer": payload.get("reviewer", "sandbox-supervisor"),
        "reason": payload["reason"],
        "audit_id": _audit("admin-override"),
    }
    ADMIN_REVIEWS.insert(0, review)
    return review


def surveillance_dashboard() -> dict[str, Any]:
    alerts = [
        {"alert_id": "surv-cancel-001", "alert_type": "excessive_cancellations", "severity": "review", "status": "open", "evidence": {"cancel_rate": 0.41}, "audit_id": "audit-surv-cancel"},
        {"alert_id": "surv-blackout-001", "alert_type": "event_blackout", "severity": "block", "status": "open", "evidence": {"symbol": "JPM", "event": "tender_offer"}, "audit_id": "audit-surv-blackout"},
    ]
    return {
        "alerts": alerts,
        "patterns_monitored": [
            "spoofing_like_layering",
            "wash_trading",
            "excessive_cancellations",
            "restricted_list",
            "insider_or_event_blackout",
            "unusual_options_activity",
            "risky_behavioral_patterns",
        ],
        "case_queue": [{"case_id": "surv-case-001", "status": "open", "linked_alerts": [alert["alert_id"] for alert in alerts]}],
        "audit_id": _audit("surveillance"),
    }


def evaluate_surveillance(payload: dict[str, Any]) -> dict[str, Any]:
    cancellations = int(payload.get("cancellations", 0))
    submitted = max(int(payload.get("submitted", 1)), 1)
    restricted_symbol = _symbol(payload.get("symbol")) in {"GME", "JPM"} and bool(payload.get("event_blackout", False))
    possible_wash = bool(payload.get("same_beneficial_owner_cross", False))
    alerts = []
    cancel_rate = cancellations / submitted
    if cancel_rate > 0.35:
        alerts.append({"alert_type": "excessive_cancellations", "severity": "review", "evidence": {"cancel_rate": _round(cancel_rate, 3)}})
    if restricted_symbol:
        alerts.append({"alert_type": "event_blackout", "severity": "block", "evidence": {"symbol": _symbol(payload.get("symbol"))}})
    if possible_wash:
        alerts.append({"alert_type": "wash_trading", "severity": "block", "evidence": {"same_beneficial_owner_cross": True}})
    return {
        "status": "alert_created" if alerts else "passed",
        "alerts": [{"alert_id": f"surv-{uuid4().hex[:8]}", "status": "open", "audit_id": _audit("surv-alert"), **alert} for alert in alerts],
        "release_allowed": not any(alert["severity"] == "block" for alert in alerts),
        "audit_id": _audit("surveillance-eval"),
    }


def entitlements_dashboard() -> dict[str, Any]:
    entitlements = [
        {"entitlement_id": "ent-real-time-equities", "user_id": "demo", "data_type": "real_time_equities", "access_level": "real_time", "status": "active", "vendor": "sandbox-feed", "audit_id": "audit-ent-rt-equities"},
        {"entitlement_id": "ent-options-delayed", "user_id": "demo", "data_type": "options_chain", "access_level": "delayed", "status": "active", "vendor": "sandbox-options", "audit_id": "audit-ent-options"},
        {"entitlement_id": "ent-level2-blocked", "user_id": "demo", "data_type": "level_ii", "access_level": "none", "status": "not_entitled", "vendor": "depth-vendor", "audit_id": "audit-ent-level2"},
    ]
    usage = [
        {"usage_id": "usage-equities-rt", "data_type": "real_time_equities", "vendor": "sandbox-feed", "units": 12840, "estimated_cost": 12.84, "audit_id": "audit-usage-equities"},
        {"usage_id": "usage-news", "data_type": "news", "vendor": "sandbox-news", "units": 420, "estimated_cost": 4.2, "audit_id": "audit-usage-news"},
    ]
    return {
        "entitlements": entitlements,
        "usage": usage,
        "cost_controls": {"daily_budget": 75.0, "current_spend": 17.04, "block_when_budget_exceeded": True},
        "source_confidence": {"market_data": 0.94, "options_chain": 0.82, "news": 0.76},
        "audit_id": _audit("entitlements"),
    }


def check_market_data_entitlement(payload: dict[str, Any]) -> dict[str, Any]:
    data_type = str(payload.get("data_type", "level_ii")).lower()
    required_level = str(payload.get("required_level", "real_time")).lower()
    entitlement = next((item for item in entitlements_dashboard()["entitlements"] if item["data_type"] == data_type), None)
    allowed_levels = {"none": 0, "delayed": 1, "real_time": 2, "premium": 3}
    actual_level = entitlement["access_level"] if entitlement else "none"
    allowed = allowed_levels.get(actual_level, 0) >= allowed_levels.get(required_level, 2)
    return {
        "data_type": data_type,
        "required_level": required_level,
        "actual_level": actual_level,
        "allowed": allowed,
        "status": "allowed" if allowed else "blocked",
        "blocked_reason": None if allowed else f"{data_type} requires {required_level} entitlement.",
        "usage_logged": True,
        "audit_id": _audit("entitlement-check"),
    }


def recurring_investments() -> dict[str, Any]:
    return {
        "plans": RECURRING_PLANS,
        "cash_sweep": {"enabled": True, "target": "SGOV", "minimum_idle_cash": 2500.0, "status": "sandbox_ready"},
        "dividend_reinvestment": {"enabled_symbols": ["MSFT", "JPM"], "fractional_supported": True},
        "auto_invest_rules": [{"rule_id": "auto-core", "condition": "cash_above_5000", "target_model": "Core Growth"}],
        "audit_id": _audit("recurring-dashboard"),
    }


def create_recurring_plan(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = _symbol(payload.get("symbol"))
    amount = float(payload.get("dollar_amount", payload.get("amount", 0)))
    available_cash = float(payload.get("available_cash", 42800.0))
    if amount <= 0:
        return {"status": "blocked", "blocked_reason": "Dollar amount must be greater than zero.", "audit_id": _audit("recurring-block")}
    if amount > available_cash:
        return {"status": "blocked", "blocked_reason": "Insufficient cash for recurring investment precheck.", "audit_id": _audit("recurring-cash-block")}
    precheck = pre_trade_control({"symbol": symbol, "side": "BUY", "quantity": max(amount / _price(symbol), 0.0001), "limit_price": _price(symbol), "asset_type": "equity"})
    plan = {
        "plan_id": f"plan-{uuid4().hex[:8]}",
        "symbol": symbol,
        "dollar_amount": _round(amount),
        "estimated_fractional_quantity": _round(amount / _price(symbol), 4),
        "cadence": payload.get("cadence", "monthly"),
        "status": "active_sandbox" if precheck["allowed"] else "blocked",
        "rules": {"fractional": True, "dividend_reinvestment": bool(payload.get("dividend_reinvestment", False)), "cash_sweep": bool(payload.get("cash_sweep", False))},
        "pre_trade": precheck,
        "audit_id": _audit("recurring-plan"),
    }
    RECURRING_PLANS.insert(0, plan)
    return plan


def simulate_conditional_order(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = _symbol(payload.get("symbol"))
    side = str(payload.get("side", "BUY")).upper()
    quantity = float(payload.get("quantity", 10))
    triggers = payload.get("triggers") or [{"field": "price", "operator": "<=", "value": _round(_price(symbol) * 0.99)}]
    do_not_execute_if = payload.get("do_not_execute_if") or [{"field": "signal_freshness", "operator": "<", "value": 0.45}]
    current_price = float(payload.get("current_price", _price(symbol)))
    freshness = float(payload.get("signal_freshness", 0.82))
    trigger_results = []
    for trigger in triggers:
        field = trigger.get("field")
        value = float(trigger.get("value", current_price))
        operator = trigger.get("operator", "<=")
        observed = current_price if field == "price" else float(payload.get(field, 0))
        fired = observed <= value if operator == "<=" else observed >= value if operator == ">=" else observed == value
        trigger_results.append({"trigger": trigger, "observed": observed, "fired": fired})
    blockers = []
    for condition in do_not_execute_if:
        if condition.get("field") == "signal_freshness" and freshness < float(condition.get("value", 0)):
            blockers.append({"condition": condition, "observed": freshness})
    precheck = pre_trade_control({"symbol": symbol, "side": side, "quantity": quantity, "limit_price": current_price, "signal_freshness": freshness})
    release_ready = any(item["fired"] for item in trigger_results) and not blockers and precheck["allowed"]
    return {
        "conditional_order_id": payload.get("conditional_order_id", f"cond-{uuid4().hex[:8]}"),
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "trigger_results": trigger_results,
        "do_not_execute_results": blockers,
        "status": "ready_to_release" if release_ready else "waiting_or_blocked",
        "release_ready": release_ready,
        "pre_trade": precheck,
        "audit_id": _audit("conditional-sim"),
    }


def create_conditional_order(payload: dict[str, Any]) -> dict[str, Any]:
    simulation = simulate_conditional_order(payload)
    if not payload.get("confirmed"):
        return {"status": "confirmation_required", "simulation": simulation, "audit_id": _audit("conditional-confirm")}
    order = {
        "conditional_order_id": simulation["conditional_order_id"],
        "symbol": simulation["symbol"],
        "side": simulation["side"],
        "quantity": simulation["quantity"],
        "triggers": payload.get("triggers", []),
        "do_not_execute_if": payload.get("do_not_execute_if", []),
        "status": "armed_sandbox" if simulation["pre_trade"]["allowed"] else "blocked",
        "simulation_result": simulation,
        "audit_id": _audit("conditional-order"),
    }
    CONDITIONAL_ORDERS.insert(0, order)
    return order


def generate_portfolio_review_pack(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    command = portfolio_command_center()
    report_id = payload.get("report_id", f"review-{uuid4().hex[:8]}")
    return {
        "report_id": report_id,
        "title": payload.get("title", "Quarterly portfolio review"),
        "status": "generated",
        "formats": ["html", "pdf", "csv"],
        "performance": {"ytd_return": 0.118, "benchmark_return": 0.091, "excess_return": 0.027},
        "risk": {"portfolio_var_95": 0.032, "largest_drawdown": -0.061, "top_concentration": "MSFT"},
        "attribution": {"security_selection": 0.014, "allocation": 0.009, "costs": -0.001},
        "tax_summary": {"realized_gain_loss": 2840.0, "harvested_losses": 620.0, "wash_sale_flags": 1},
        "ai_rationale": ["MSFT remains a hold due to strong quality factor but elevated concentration.", "NVDA sizing is capped by volatility budget."],
        "holdings": command["positions"],
        "factor_exposure": {"quality": 0.31, "momentum": 0.18, "value": 0.11, "rates": 0.07},
        "next_recommended_actions": ["Review JPM tender election", "Keep Level II blocked until entitlement approved", "Rebalance technology weight below 50%"],
        "source_data": ["portfolio_command_center", "tax_lot_manager", "signal_orchestrator"],
        "model_versions": ["champion-2026-06", "risk-engine-2026-06"],
        "disclosures": ["sandbox_report_not_personalized_advice", "performance_includes_simulated_data"],
        "archive_id": f"archive-{report_id}",
        "audit_id": _audit("portfolio-review"),
    }


def mobile_companion() -> dict[str, Any]:
    return {
        "devices": [
            {"device_id": "mobile-ios-demo", "platform": "ios", "push_enabled": True, "biometric_approval_supported": True, "status": "registered", "audit_id": "audit-mobile-ios"}
        ],
        "alerts": [
            {"alert_id": "mobile-risk-001", "severity": "critical", "title": "JPM corporate action election due"},
            {"alert_id": "mobile-broker-001", "severity": "review", "title": "IBKR broker sync degraded"},
        ],
        "emergency_controls": {"pause_trading": True, "cancel_open_orders": True, "approve_staged_trades": True},
        "trade_approvals": [{"stage_id": "stage-msft-rebalance", "status": "approval_required"}],
        "positions": portfolio_command_center()["positions"],
        "watchlist_alerts": [{"symbol": "MSFT", "condition": "price above 425", "push_ready": True}],
        "push_payloads": [{"topic": "broker_outage", "title": "Broker connection degraded", "body": "Review account sync before release."}],
        "biometric_approval_contract": {"required_for_trade_release": True, "fallback": "password_and_confirmation"},
        "state": MOBILE_STATE,
        "audit_id": _audit("mobile"),
    }


def mobile_emergency_pause(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    action = pause_trading({"reason": payload.get("reason", "mobile_emergency_pause")})
    MOBILE_STATE["trading_paused"] = True
    MOBILE_STATE["last_mobile_action"] = action
    return {"status": "active", "mobile_action": action, "push_sent": True, "audit_id": _audit("mobile-pause")}


def support_center() -> dict[str, Any]:
    return {
        "cases": SUPPORT_CASES,
        "incident_status": [
            {"incident_id": "incident-broker-ibkr", "type": "broker_outage", "status": "degraded", "started_at": (_now() - timedelta(minutes=14)).isoformat()},
            {"incident_id": "incident-data-news", "type": "data_vendor", "status": "resolved", "resolved_at": (_now() - timedelta(hours=2)).isoformat()},
        ],
        "audit_requests": [
            {"request_id": "audit-order-msft", "request_type": "order_trail", "status": "ready", "scope": {"order_id": "order-msft-bracket"}, "audit_id": "audit-request-msft"}
        ],
        "available_actions": ["ask_rejection_reason", "dispute_fill", "download_audit_trail", "contact_support", "view_incident_status"],
        "audit_id": _audit("support-center"),
    }


def create_support_case(payload: dict[str, Any]) -> dict[str, Any]:
    subject = str(payload.get("subject", "Order support request")).strip()
    category = str(payload.get("category", "general")).strip()
    if not subject:
        return {"status": "blocked", "blocked_reason": "Support case subject is required.", "audit_id": _audit("support-block")}
    case = {
        "case_id": f"case-{uuid4().hex[:8]}",
        "category": category,
        "status": "open",
        "subject": subject,
        "messages": [{"author": "user", "text": payload.get("message", subject)}],
        "evidence_refs": payload.get("evidence_refs", []),
        "sla": {"first_response_minutes": 30, "priority": "high" if category in {"fill_dispute", "order_rejection"} else "normal"},
        "audit_id": _audit("support-case"),
    }
    SUPPORT_CASES.insert(0, case)
    return case
