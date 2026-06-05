from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

from backend.services.brokerage_ops_service import check_market_data_entitlement
from backend.services.trader_operating_system import portfolio_command_center
from backend.services.workstation_service import pre_trade_control, strategy_research


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


ALERT_RULES: list[dict[str, Any]] = [
    {
        "alert_rule_id": "alert-msft-price",
        "name": "MSFT price breakout",
        "event_type": "price",
        "conditions": [{"field": "last", "operator": ">=", "value": 425.0}],
        "destinations": ["in_app", "push"],
        "status": "active",
        "audit_id": "audit-alert-msft-price",
    }
]

AUTOMATION_POLICIES: list[dict[str, Any]] = [
    {
        "policy_id": "auto-vol-pause",
        "name": "Pause on volatility spike",
        "policy_type": "risk_pause",
        "guardrails": ["pre_trade_control", "kill_switch_link", "approval_required_for_live"],
        "status": "simulation_ready",
        "audit_id": "audit-auto-vol-pause",
    }
]

COLLABORATION_SPACES: list[dict[str, Any]] = [
    {
        "space_id": "club-core-alpha",
        "name": "Core Alpha Club",
        "privacy": "private",
        "members": ["analyst@example.com", "mentor@example.com"],
        "shared_assets": ["watchlist:quality-growth", "model:core-growth"],
        "moderation_status": "active",
        "audit_id": "audit-club-core-alpha",
    }
]

NOTIFICATION_POLICIES: list[dict[str, Any]] = [
    {
        "policy_id": "notif-risk-critical",
        "channel": "push",
        "category": "critical_risk",
        "enabled": True,
        "quiet_hours": {"enabled": False},
        "escalation_rules": [{"after_minutes": 5, "channel": "sms"}],
        "audit_id": "audit-notif-risk-critical",
    }
]

NOTIFICATION_LOGS: list[dict[str, Any]] = []


def one_stop_overview() -> dict[str, Any]:
    return {
        "generated_at": _now().isoformat(),
        "mode": "sandbox",
        "modules": [
            {"id": "terminal", "label": "Market Data Terminal", "status": "entitlement_gated"},
            {"id": "research", "label": "Fundamental Research Lab", "status": "ready"},
            {"id": "brokers", "label": "Broker Connectivity Hub", "status": "monitoring"},
            {"id": "transfers", "label": "ACATS Transfer Center", "status": "sandbox"},
            {"id": "account_rules", "label": "Account-Type Rules", "status": "enforcing"},
            {"id": "analytics", "label": "Portfolio Analytics Pro", "status": "ready"},
            {"id": "alerts", "label": "Real-Time Alert Builder", "status": "armed"},
            {"id": "automation", "label": "Trading Automation Studio", "status": "simulation_only"},
            {"id": "backtests", "label": "Advanced Backtest Marketplace", "status": "ready"},
            {"id": "document_ai", "label": "News, Filings, Transcript AI", "status": "source_linked"},
            {"id": "coaching", "label": "Learning and Coaching Center", "status": "education_only"},
            {"id": "collaboration", "label": "Social Collaboration", "status": "private"},
            {"id": "fees", "label": "Fee, Interest, Yield Center", "status": "ready"},
            {"id": "trust", "label": "Security and Trust Center", "status": "armed"},
            {"id": "notifications", "label": "Full Notification System", "status": "delivery_testable"},
        ],
        "fail_closed_gates": [
            "market_data_entitlement",
            "broker_connection_health",
            "account_type_rule",
            "pre_trade_control",
            "explicit_approval",
            "source_evidence",
            "delivery_provider_status",
            "immutable_audit_record",
        ],
    }


def market_data_terminal(symbol: str = "MSFT") -> dict[str, Any]:
    normalized = _symbol(symbol)
    price = _price(normalized)
    level_two = check_market_data_entitlement({"data_type": "level_ii", "required_level": "real_time"})
    real_time = check_market_data_entitlement({"data_type": "real_time_equities", "required_level": "real_time"})
    depth_blocked = not level_two["allowed"]
    return {
        "symbol": normalized,
        "quote": {
            "quote_id": f"quote-{normalized.lower()}",
            "bid": _round(price - 0.02),
            "ask": _round(price + 0.02),
            "last": price,
            "change": 1.84,
            "change_pct": 0.0044,
            "entitlement_level": real_time["actual_level"],
            "source_confidence": 0.96,
            "stale": False,
            "audit_id": _audit("terminal-quote"),
        },
        "level_ii": {
            "entitlement": level_two,
            "bids": [] if depth_blocked else [{"venue": "NASDAQ", "price": _round(price - 0.02), "size": 1200}],
            "asks": [] if depth_blocked else [{"venue": "NASDAQ", "price": _round(price + 0.02), "size": 980}],
            "blocked_reason": level_two["blocked_reason"] if depth_blocked else None,
        },
        "time_and_sales": [
            {"print_id": "print-1", "price": _round(price + 0.01), "size": 100, "venue": "IEX", "time": "10:07:14"},
            {"print_id": "print-2", "price": _round(price), "size": 400, "venue": "NASDAQ", "time": "10:07:18"},
        ],
        "option_flow": [
            {"flow_id": "flow-msft-call", "contract": f"{normalized} 2026-07-17 440C", "side": "buyer_initiated", "premium": 812000, "unusual_score": 0.82},
            {"flow_id": "flow-msft-put", "contract": f"{normalized} 2026-07-17 400P", "side": "seller_initiated", "premium": 265000, "unusual_score": 0.44},
        ],
        "sector_map": [
            {"sector": "Technology", "change_pct": 0.007, "relative_strength": 0.72},
            {"sector": "Financials", "change_pct": -0.002, "relative_strength": 0.48},
            {"sector": "Energy", "change_pct": 0.003, "relative_strength": 0.55},
        ],
        "events": [
            {"event_id": "econ-cpi", "type": "economic_release", "title": "CPI release", "scheduled_at": (_now() + timedelta(days=7)).isoformat(), "alertable": True},
            {"event_id": "filing-msft-10q", "type": "sec_filing", "title": f"{normalized} 10-Q filed", "source": "SEC", "alertable": True},
            {"event_id": "analyst-msft", "type": "analyst_change", "title": "Target price raised", "source": "sandbox analyst feed", "alertable": True},
        ],
        "news": [
            {"headline": f"{normalized} cloud demand remains resilient", "sentiment": "positive", "confidence": 0.78, "source": "sandbox-news"},
            {"headline": "Rates edge higher before jobs report", "sentiment": "macro_review", "confidence": 0.71, "source": "sandbox-news"},
        ],
        "source_health": {"market_data": "healthy", "news": "healthy", "filings": "healthy", "stale_feed_flags": []},
        "audit_id": _audit("terminal"),
    }


def research_lab(symbol: str = "MSFT", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    normalized = _symbol(symbol)
    price = _price(normalized)
    revenue_growth = float(payload.get("revenue_growth", 0.11))
    margin = float(payload.get("operating_margin", 0.42))
    terminal_multiple = float(payload.get("terminal_multiple", 24.0))
    fair_value = _round(price * (1 + revenue_growth) * (margin / 0.38) * (terminal_multiple / 24.0))
    return {
        "snapshot_id": f"research-{normalized.lower()}",
        "symbol": normalized,
        "financials": {
            "revenue_ttm": 245_100_000_000,
            "gross_margin": 0.69,
            "operating_margin": margin,
            "free_cash_flow_margin": 0.31,
            "revenue_growth": revenue_growth,
        },
        "valuation": {
            "pe": 34.2,
            "ev_to_sales": 12.4,
            "fcf_yield": 0.025,
            "dcf_fair_value": fair_value,
            "current_price": price,
            "upside_downside_pct": _round((fair_value / price) - 1, 4),
        },
        "peer_comparison": [
            {"symbol": "AAPL", "pe": 29.8, "revenue_growth": 0.04},
            {"symbol": "GOOGL", "pe": 25.1, "revenue_growth": 0.13},
            {"symbol": "NVDA", "pe": 41.6, "revenue_growth": 0.58},
        ],
        "insiders": [{"name": "Sandbox Officer", "transaction": "sale", "shares": 2500, "date": (date.today() - timedelta(days=12)).isoformat()}],
        "institutional_ownership": {"top_holders_pct": 0.31, "net_13f_change_pct": 0.018},
        "dividend_history": [{"ex_date": (date.today() - timedelta(days=46)).isoformat(), "amount": 0.75}, {"ex_date": (date.today() + timedelta(days=42)).isoformat(), "amount": 0.78}],
        "ai_brief": {
            "summary": f"{normalized} screens as a high-quality compounder, but valuation and portfolio concentration should cap position sizing.",
            "source_refs": ["financials:sandbox", "ownership:sandbox", "filing:latest-10q"],
            "model_version": "research-brief-2026-06",
            "audit_id": _audit("research-brief"),
        },
        "portfolio_link": {"held": True, "position_risk": "concentration_review"},
        "audit_id": _audit("research"),
    }


def broker_connectivity_hub() -> dict[str, Any]:
    return {
        "connections": [
            {
                "connection_id": "broker-alpaca-paper",
                "broker": "Alpaca",
                "account_id": "ALP-SANDBOX-001",
                "status": "paper_connected",
                "live_enabled": False,
                "permissions": ["quotes", "paper_orders", "positions"],
                "token_expires_at": (_now() + timedelta(days=18)).isoformat(),
                "sync_health": {"balances": "healthy", "orders": "healthy", "fills": "healthy"},
                "capability_matrix": {"market": True, "limit": True, "stop": True, "options": False, "fractional": True},
                "limitations": ["live trading requires M10 broker certification"],
                "audit_id": "audit-broker-alpaca-paper",
            },
            {
                "connection_id": "broker-ibkr-paper",
                "broker": "IBKR",
                "account_id": "IBKR-PAPER-042",
                "status": "degraded",
                "live_enabled": False,
                "permissions": ["positions", "orders"],
                "token_expires_at": (_now() + timedelta(hours=6)).isoformat(),
                "sync_health": {"balances": "stale", "orders": "healthy", "fills": "review"},
                "capability_matrix": {"market": True, "limit": True, "stop": True, "options": True, "fractional": False},
                "limitations": ["balance sync stale by 14 minutes"],
                "audit_id": "audit-broker-ibkr-paper",
            },
        ],
        "outages": [{"broker": "IBKR", "status": "degraded", "started_at": (_now() - timedelta(minutes=14)).isoformat()}],
        "live_status_gate": {"enabled": False, "blocked_reason": "Live broker actions require M10 evidence, broker certification, and fresh sync health."},
        "audit_id": _audit("broker-hub"),
    }


def refresh_broker_connection(payload: dict[str, Any]) -> dict[str, Any]:
    connection_id = payload.get("connection_id", "broker-alpaca-paper")
    live_requested = bool(payload.get("live", False))
    if live_requested and not payload.get("m10_evidence"):
        return {"connection_id": connection_id, "status": "blocked", "blocked_reason": "Live refresh requires M10 broker evidence.", "audit_id": _audit("broker-live-block")}
    return {
        "connection_id": connection_id,
        "status": "refreshed",
        "sync_health": {"balances": "healthy", "orders": "healthy", "fills": "healthy"},
        "token_expires_at": (_now() + timedelta(days=30)).isoformat(),
        "audit_id": _audit("broker-refresh"),
    }


def account_transfer_center() -> dict[str, Any]:
    return {
        "transfers": [
            {
                "transfer_id": "acats-in-001",
                "direction": "incoming",
                "status": "cost_basis_pending",
                "delivering_firm": "External Broker",
                "receiving_firm": "Trading Platform Sandbox",
                "assets": [{"symbol": "MSFT", "quantity": 25}, {"symbol": "JPM", "quantity": 40}],
                "rejected_assets": [{"symbol": "MUTFX", "reason": "unsupported mutual fund"}],
                "cost_basis_status": "pending_from_delivering_firm",
                "checklist": [
                    {"item": "identity_match", "status": "passed"},
                    {"item": "asset_eligibility", "status": "review"},
                    {"item": "cost_basis_import", "status": "pending"},
                ],
                "audit_id": "audit-acats-in-001",
            }
        ],
        "support_links": [{"case_id": "case-acats-001", "status": "open", "subject": "Rejected asset review"}],
        "audit_id": _audit("acats-center"),
    }


def create_acats_transfer(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("confirmed"):
        return {"status": "confirmation_required", "required_actions": ["confirm_transfer_request"], "audit_id": _audit("acats-confirm")}
    transfer = {
        "transfer_id": f"acats-{uuid4().hex[:8]}",
        "direction": payload.get("direction", "incoming"),
        "status": "initiated_sandbox",
        "delivering_firm": payload.get("delivering_firm", "External Broker"),
        "receiving_firm": payload.get("receiving_firm", "Trading Platform Sandbox"),
        "assets": payload.get("assets", []),
        "rejected_assets": [],
        "cost_basis_status": "requested",
        "checklist": [{"item": "account_match", "status": "pending"}, {"item": "asset_eligibility", "status": "pending"}],
        "audit_id": _audit("acats-transfer"),
    }
    return transfer


def account_type_rules() -> dict[str, Any]:
    return {
        "rules": [
            {"rule_id": "rule-ira-margin", "account_type": "traditional_ira", "rule_type": "margin", "status": "active", "constraints": {"margin_allowed": False, "shorting_allowed": False}},
            {"rule_id": "rule-roth-contribution", "account_type": "roth_ira", "rule_type": "contribution", "status": "active", "constraints": {"annual_limit": 7000, "income_phaseout_required": True}},
            {"rule_id": "rule-taxable-margin", "account_type": "taxable", "rule_type": "margin", "status": "active", "constraints": {"margin_allowed": True, "shorting_requires_borrow": True}},
            {"rule_id": "rule-custodial-options", "account_type": "custodial", "rule_type": "options", "status": "active", "constraints": {"max_options_level": 0}},
        ],
        "supported_account_types": ["traditional_ira", "roth_ira", "taxable", "joint", "trust", "business", "custodial", "hsa"],
        "audit_id": _audit("account-rules"),
    }


def evaluate_account_rule(payload: dict[str, Any]) -> dict[str, Any]:
    account_type = str(payload.get("account_type", "traditional_ira")).lower()
    action = str(payload.get("action", "short_sale")).lower()
    violations = []
    if account_type in {"traditional_ira", "roth_ira", "custodial", "hsa"} and action in {"short_sale", "margin_trade"}:
        violations.append(f"{action} is not allowed in {account_type}")
    if account_type == "custodial" and int(payload.get("options_level", 0)) > 0:
        violations.append("custodial accounts cannot trade options in this sandbox policy")
    return {
        "account_type": account_type,
        "action": action,
        "allowed": not violations,
        "status": "allowed" if not violations else "blocked",
        "violations": violations,
        "enforcement": "fail_closed",
        "audit_id": _audit("account-rule-eval"),
    }


def portfolio_analytics_pro() -> dict[str, Any]:
    command = portfolio_command_center()
    return {
        "analytics_id": f"analytics-{uuid4().hex[:8]}",
        "account_id": "ALP-SANDBOX-001",
        "performance": {"ytd_return": 0.118, "benchmark": "SPY", "benchmark_return": 0.091, "after_fee_return": 0.113},
        "attribution": {"allocation": 0.009, "selection": 0.014, "interaction": 0.003, "fees": -0.005, "tax_drag": -0.006},
        "factor_attribution": {"quality": 0.018, "momentum": 0.006, "value": -0.003, "rates": -0.002},
        "income_projection": {"next_12m_dividends": 2840.0, "cash_sweep_yield": 0.0475, "portfolio_yield": 0.021},
        "risk": {"rolling_sharpe_90d": 1.42, "max_drawdown": -0.061, "var_95": 0.032},
        "contribution_impact": {"monthly_1000": {"ending_value_delta_12m": 12480.0}},
        "holdings": command["positions"],
        "manager_report": {"exportable": True, "formats": ["html", "pdf", "csv"]},
        "audit_id": _audit("portfolio-analytics"),
    }


def alert_builder() -> dict[str, Any]:
    return {
        "rules": ALERT_RULES,
        "event_catalog": [
            "price",
            "volume",
            "technical_indicator",
            "options_iv",
            "earnings",
            "sec_filing",
            "margin_risk",
            "drawdown",
            "news_sentiment",
            "ai_signal_change",
            "corporate_action",
            "broker_outage",
            "account_transfer",
        ],
        "delivery_channels": ["email", "sms", "push", "in_app", "webhook", "slack", "discord"],
        "audit_id": _audit("alert-builder"),
    }


def create_alert_rule(payload: dict[str, Any]) -> dict[str, Any]:
    conditions = payload.get("conditions") or [{"field": "last", "operator": ">=", "value": 425}]
    destinations = payload.get("destinations") or ["in_app"]
    rule = {
        "alert_rule_id": f"alert-{uuid4().hex[:8]}",
        "name": payload.get("name", "New market alert"),
        "event_type": payload.get("event_type", "price"),
        "conditions": conditions,
        "destinations": destinations,
        "status": "active",
        "audit_id": _audit("alert-rule"),
    }
    ALERT_RULES.insert(0, rule)
    return rule


def test_alert_delivery(payload: dict[str, Any]) -> dict[str, Any]:
    channels = payload.get("channels") or ["in_app", "push"]
    deliveries = [
        {"delivery_id": f"delivery-{uuid4().hex[:8]}", "channel": channel, "status": "sent", "destination": payload.get("destination", "demo-user"), "audit_id": _audit("alert-delivery")}
        for channel in channels
    ]
    NOTIFICATION_LOGS[:0] = deliveries
    return {"status": "sent", "deliveries": deliveries, "audit_id": _audit("alert-test")}


def automation_studio() -> dict[str, Any]:
    return {
        "policies": AUTOMATION_POLICIES,
        "guardrail_catalog": ["pre_trade_control", "market_data_freshness", "kill_switch", "max_drawdown", "volatility_pause", "approval_required", "paper_only"],
        "eligible_actions": ["rebalance_schedule", "signal_following_paper", "recurring_strategy_check", "pause_if_volatility_spikes"],
        "audit_id": _audit("automation-studio"),
    }


def simulate_automation(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = _symbol(payload.get("symbol"))
    volatility = float(payload.get("volatility", 0.22))
    approval_required = bool(payload.get("approval_required", True))
    precheck = pre_trade_control({"symbol": symbol, "side": "BUY", "quantity": 5, "limit_price": _price(symbol), "signal_freshness": payload.get("signal_freshness", 0.82)})
    paused = volatility >= float(payload.get("volatility_pause_threshold", 0.35))
    return {
        "policy_id": payload.get("policy_id", f"auto-{uuid4().hex[:8]}"),
        "status": "blocked" if paused or not precheck["allowed"] else "approval_required" if approval_required else "paper_ready",
        "simulation": {"volatility": volatility, "paused_by_volatility": paused, "paper_only": True},
        "pre_trade": precheck,
        "required_actions": ["human_approval"] if approval_required else [],
        "audit_id": _audit("automation-sim"),
    }


def backtest_marketplace() -> dict[str, Any]:
    listings = [
        {"listing_id": "strat-quality-pullback", "name": "Quality Pullback", "strategy_type": "built_in", "performance_summary": {"sharpe": 1.32, "max_drawdown": -0.08}, "risk_summary": {"costs_included": True}, "status": "listed", "audit_id": "audit-strat-quality"},
        {"listing_id": "strat-ai-momentum", "name": "AI Momentum Guarded", "strategy_type": "ai", "performance_summary": {"sharpe": 1.18, "max_drawdown": -0.11}, "risk_summary": {"costs_included": True}, "status": "listed", "audit_id": "audit-strat-ai"},
        {"listing_id": "strat-community-income", "name": "Community Income Tilt", "strategy_type": "community", "performance_summary": {"sharpe": 0.97, "max_drawdown": -0.06}, "risk_summary": {"costs_included": True}, "status": "listed", "audit_id": "audit-strat-income"},
    ]
    return {"listings": listings, "comparison_dimensions": ["asset_class", "regime", "costs", "slippage", "walk_forward", "survivorship_bias"], "audit_id": _audit("backtest-marketplace")}


def compare_marketplace_strategies(payload: dict[str, Any]) -> dict[str, Any]:
    ids = payload.get("listing_ids") or ["strat-quality-pullback", "strat-ai-momentum"]
    research = strategy_research({"universe": payload.get("universe", ["MSFT", "NVDA", "JPM", "SPY"])})
    return {
        "comparison_id": f"compare-{uuid4().hex[:8]}",
        "listing_ids": ids,
        "walk_forward": research["walk_forward_report"],
        "costs": {"slippage_bps": 2.4, "commissions": 0.0, "borrow_fees_included": True},
        "regime_breakdown": {"bull": 0.14, "bear": -0.03, "sideways": 0.04},
        "paper_deploy_eligible": research["paper_deploy"]["eligible"],
        "audit_id": _audit("strategy-compare"),
    }


def document_ai_reader(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    doc_type = payload.get("document_type", "10-Q")
    title = payload.get("title", "MSFT quarterly filing")
    return {
        "summary_id": f"docai-{uuid4().hex[:8]}",
        "document_type": doc_type,
        "title": title,
        "impact_summary": "Revenue growth and margin commentary support the current hold thesis, but capex and AI infrastructure spend increase monitoring needs.",
        "position_level_impacts": [{"symbol": "MSFT", "impact": "supports_hold", "risk": "capex_watch"}, {"symbol": "NVDA", "impact": "positive_readthrough", "risk": "valuation"}],
        "source_refs": ["filing:msft-10q-risk-factors", "transcript:q-and-a", "macro:cpi-release"],
        "confidence": 0.84,
        "recommendation_boundary": "Educational summary only; trade actions require separate suitability, risk, and pre-trade checks.",
        "audit_id": _audit("doc-ai"),
    }


def coaching_center() -> dict[str, Any]:
    return {
        "plans": [
            {"plan_id": "coach-risk-sizing", "user_id": "demo", "focus_area": "position_sizing", "goals": ["Keep single-name exposure below 25%", "Write pre-trade invalidation levels"], "status": "active", "audit_id": "audit-coach-risk"}
        ],
        "lessons": [
            {"lesson_id": "lesson-options-basics", "title": "Options assignment risk", "type": "interactive"},
            {"lesson_id": "lesson-margin-warning", "title": "Margin interest and liquidation risk", "type": "simulation"},
            {"lesson_id": "lesson-tax-wash-sale", "title": "Wash-sale basics", "type": "guided_review"},
        ],
        "behavioral_insights": [{"pattern": "oversizing_after_wins", "severity": "review", "suggestion": "Use fixed risk budget before entering orders."}],
        "advice_boundary": "Coaching is educational and behavior-focused; personalized recommendations require platform suitability and disclosure gates.",
        "audit_id": _audit("coaching"),
    }


def collaboration_layer() -> dict[str, Any]:
    return {
        "spaces": COLLABORATION_SPACES,
        "shared_watchlists": [{"watchlist_id": "watch-quality-growth", "name": "Quality Growth", "symbols": ["MSFT", "NVDA", "GOOGL"], "visibility": "space"}],
        "team_approvals": [{"approval_id": "team-stage-msft", "status": "pending", "maker": "analyst@example.com", "checker": "mentor@example.com"}],
        "privacy_controls": {"read_only_account_sharing": True, "hide_balances": True, "recommendation_audit_required": True},
        "audit_id": _audit("collaboration"),
    }


def create_collaboration_space(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("privacy", "private") != "private":
        return {"status": "blocked", "blocked_reason": "Only private spaces are enabled in sandbox.", "audit_id": _audit("collab-block")}
    space = {
        "space_id": f"space-{uuid4().hex[:8]}",
        "name": payload.get("name", "Private trading room"),
        "privacy": "private",
        "members": payload.get("members", ["analyst@example.com"]),
        "shared_assets": payload.get("shared_assets", []),
        "moderation_status": "active",
        "audit_id": _audit("collab-space"),
    }
    COLLABORATION_SPACES.insert(0, space)
    return space


def fee_yield_center() -> dict[str, Any]:
    records = [
        {"record_id": "fee-margin", "account_id": "ALP-SANDBOX-001", "category": "margin_interest", "amount": -42.18, "annualized_rate": 0.0825, "broker": "Alpaca", "disclosure": "Margin interest estimate based on sandbox balance.", "audit_id": "audit-fee-margin"},
        {"record_id": "yield-cash", "account_id": "ALP-SANDBOX-001", "category": "cash_sweep_yield", "amount": 116.42, "annualized_rate": 0.0475, "broker": "Alpaca", "disclosure": "Cash sweep yield is variable.", "audit_id": "audit-yield-cash"},
        {"record_id": "fee-borrow", "account_id": "IBKR-PAPER-042", "category": "borrow_fee", "amount": -18.5, "annualized_rate": 0.0475, "broker": "IBKR", "disclosure": "Hard-to-borrow rates may change intraday.", "audit_id": "audit-fee-borrow"},
        {"record_id": "fee-reg", "account_id": "ALP-SANDBOX-001", "category": "regulatory_fees", "amount": -2.14, "annualized_rate": None, "broker": "Alpaca", "disclosure": "Regulatory fees are estimated.", "audit_id": "audit-fee-reg"},
    ]
    net = sum(record["amount"] for record in records)
    return {"records": records, "net_yield_after_fees": _round(net), "after_fee_performance": {"gross_return": 0.118, "after_fee_return": 0.113}, "pfof_disclosure": "Routing economics are disclosed where broker data is available.", "audit_id": _audit("fee-yield")}


def trust_center() -> dict[str, Any]:
    return {
        "devices": [{"device_id": "browser-win-demo", "status": "trusted", "last_seen": _now().isoformat()}, {"device_id": "mobile-ios-demo", "status": "trusted", "last_seen": (_now() - timedelta(hours=2)).isoformat()}],
        "sessions": [{"session_id": "session-current", "ip": "127.0.0.1", "status": "active"}],
        "withdrawal_locks": [{"lock_id": "withdrawal-lock-1", "status": "enabled", "cooldown_hours": 24}],
        "trusted_contacts": [{"name": "Trusted Contact", "status": "verified"}],
        "beneficiaries": [{"account_type": "ira", "status": "metadata_on_file"}],
        "account_protection": {"sipc_education": True, "not_a_bank_deposit_disclosure": True},
        "suspicious_login_alerts": [{"event_id": "login-review-1", "severity": "review", "status": "resolved"}],
        "data_exports": [{"export_id": "privacy-export-1", "status": "ready"}],
        "audit_id": _audit("trust"),
    }


def lock_account(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("confirmed"):
        return {"status": "confirmation_required", "audit_id": _audit("account-lock-confirm")}
    return {
        "event_id": f"trust-lock-{uuid4().hex[:8]}",
        "event_type": "emergency_account_lock",
        "status": "active",
        "severity": "critical",
        "reason": payload.get("reason", "user_requested"),
        "audit_id": _audit("account-lock"),
    }


def notification_system() -> dict[str, Any]:
    return {
        "policies": NOTIFICATION_POLICIES,
        "channels": ["email", "sms", "push", "in_app", "webhook", "slack", "discord"],
        "delivery_logs": NOTIFICATION_LOGS,
        "provider_health": {"email": "healthy", "sms": "sandbox", "push": "healthy", "webhook": "healthy", "slack": "not_configured", "discord": "not_configured"},
        "quiet_hours": {"default": {"start": "21:00", "end": "07:00", "timezone": "America/Chicago"}},
        "audit_id": _audit("notifications"),
    }


def test_notification(payload: dict[str, Any]) -> dict[str, Any]:
    channel = payload.get("channel", "in_app")
    provider_health = notification_system()["provider_health"].get(channel, "not_configured")
    if provider_health == "not_configured":
        return {"status": "blocked", "blocked_reason": f"{channel} provider is not configured.", "audit_id": _audit("notification-block")}
    delivery = {
        "delivery_id": f"delivery-{uuid4().hex[:8]}",
        "channel": channel,
        "status": "sent",
        "destination": payload.get("destination", "demo-user"),
        "retry_count": 0,
        "audit_id": _audit("notification-delivery"),
    }
    NOTIFICATION_LOGS.insert(0, delivery)
    return delivery
