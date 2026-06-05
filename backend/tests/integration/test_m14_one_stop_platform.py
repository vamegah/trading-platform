import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.workstation_service import EMERGENCY_STATE
from backend.shared import models


@pytest.fixture(autouse=True)
def reset_shared_emergency_state() -> None:
    EMERGENCY_STATE["trading_paused"] = False
    EMERGENCY_STATE["last_action"] = None
    EMERGENCY_STATE["open_order_count"] = 3


@pytest.mark.asyncio
async def test_m14_terminal_research_brokers_and_acats() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overview = await client.get("/one-stop/overview")
        terminal = await client.get("/one-stop/terminal/MSFT")
        research = await client.post("/one-stop/research/brief", json={"symbol": "MSFT", "revenue_growth": 0.12})
        brokers = await client.get("/one-stop/brokers")
        live_refresh = await client.post("/one-stop/brokers/refresh", json={"connection_id": "broker-alpaca-paper", "live": True})
        transfer_center = await client.get("/one-stop/transfers")
        acats = await client.post(
            "/one-stop/transfers/acats",
            json={"confirmed": True, "direction": "incoming", "assets": [{"symbol": "MSFT", "quantity": 10}]},
        )

    assert overview.status_code == 200
    assert any(module["id"] == "terminal" for module in overview.json()["modules"])
    assert terminal.json()["quote"]["entitlement_level"] == "real_time"
    assert terminal.json()["level_ii"]["entitlement"]["status"] == "blocked"
    assert terminal.json()["events"]
    assert research.json()["valuation"]["dcf_fair_value"] > 0
    assert research.json()["ai_brief"]["source_refs"]
    assert brokers.json()["live_status_gate"]["enabled"] is False
    assert live_refresh.json()["status"] == "blocked"
    assert transfer_center.json()["transfers"][0]["cost_basis_status"]
    assert acats.json()["status"] == "initiated_sandbox"


@pytest.mark.asyncio
async def test_m14_account_rules_analytics_alerts_and_automation() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rules = await client.get("/one-stop/account-rules")
        rule_eval = await client.post("/one-stop/account-rules/evaluate", json={"account_type": "traditional_ira", "action": "short_sale"})
        analytics = await client.get("/one-stop/analytics/portfolio")
        alerts = await client.get("/one-stop/alerts")
        alert = await client.post("/one-stop/alerts", json={"name": "MSFT filing alert", "event_type": "sec_filing", "destinations": ["in_app"]})
        delivery = await client.post("/one-stop/alerts/test", json={"channels": ["in_app", "push"], "destination": "demo-user"})
        automation = await client.get("/one-stop/automation")
        simulation = await client.post("/one-stop/automation/simulate", json={"symbol": "MSFT", "volatility": 0.22, "approval_required": True})

    assert "traditional_ira" in rules.json()["supported_account_types"]
    assert rule_eval.json()["status"] == "blocked"
    assert "short_sale" in rule_eval.json()["violations"][0]
    assert analytics.json()["performance"]["after_fee_return"] > 0
    assert analytics.json()["manager_report"]["exportable"] is True
    assert alerts.json()["delivery_channels"]
    assert alert.json()["status"] == "active"
    assert delivery.json()["status"] == "sent"
    assert automation.json()["guardrail_catalog"]
    assert simulation.json()["status"] == "approval_required"
    assert simulation.json()["pre_trade"]["allowed"] is True


@pytest.mark.asyncio
async def test_m14_marketplace_document_ai_coaching_collaboration_fees_trust_notifications() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        marketplace = await client.get("/one-stop/backtest-marketplace")
        comparison = await client.post(
            "/one-stop/backtest-marketplace/compare",
            json={"listing_ids": ["strat-quality-pullback", "strat-ai-momentum"], "universe": ["MSFT", "NVDA", "JPM"]},
        )
        doc_ai = await client.post("/one-stop/document-ai/read", json={"document_type": "10-Q", "title": "MSFT 10-Q"})
        coaching = await client.get("/one-stop/coaching")
        collaboration = await client.get("/one-stop/collaboration")
        space = await client.post("/one-stop/collaboration/spaces", json={"name": "MSFT review", "privacy": "private"})
        public_space = await client.post("/one-stop/collaboration/spaces", json={"name": "Public room", "privacy": "public"})
        fees = await client.get("/one-stop/fees-yield")
        trust = await client.get("/one-stop/trust")
        lock_confirm = await client.post("/one-stop/trust/lock", json={})
        lock = await client.post("/one-stop/trust/lock", json={"confirmed": True, "reason": "test"})
        notifications = await client.get("/one-stop/notifications")
        push = await client.post("/one-stop/notifications/test", json={"channel": "push", "destination": "demo-user"})
        slack = await client.post("/one-stop/notifications/test", json={"channel": "slack", "destination": "demo"})

    assert marketplace.json()["listings"]
    assert comparison.json()["costs"]["borrow_fees_included"] is True
    assert doc_ai.json()["source_refs"]
    assert "Educational" in doc_ai.json()["recommendation_boundary"]
    assert coaching.json()["advice_boundary"]
    assert collaboration.json()["privacy_controls"]["recommendation_audit_required"] is True
    assert space.json()["privacy"] == "private"
    assert public_space.json()["status"] == "blocked"
    assert fees.json()["after_fee_performance"]["after_fee_return"] > 0
    assert trust.json()["withdrawal_locks"][0]["status"] == "enabled"
    assert lock_confirm.json()["status"] == "confirmation_required"
    assert lock.json()["status"] == "active"
    assert notifications.json()["channels"]
    assert push.json()["status"] == "sent"
    assert slack.json()["status"] == "blocked"


def test_m14_domain_models_and_tables_exist() -> None:
    table_names = {
        models.TerminalQuoteModel.__tablename__,
        models.LevelIIBookModel.__tablename__,
        models.TimeAndSalesPrintModel.__tablename__,
        models.OptionFlowEventModel.__tablename__,
        models.ResearchSnapshotModel.__tablename__,
        models.BrokerConnectionModel.__tablename__,
        models.ACATSTransferModel.__tablename__,
        models.AccountTypeRuleModel.__tablename__,
        models.PortfolioAnalyticsSnapshotModel.__tablename__,
        models.AlertRuleModel.__tablename__,
        models.AutomationPolicyModel.__tablename__,
        models.StrategyMarketplaceListingModel.__tablename__,
        models.DocumentAISummaryModel.__tablename__,
        models.CoachingPlanModel.__tablename__,
        models.CollaborationSpaceModel.__tablename__,
        models.FeeYieldRecordModel.__tablename__,
        models.TrustSecurityEventModel.__tablename__,
        models.NotificationPolicyModel.__tablename__,
        models.NotificationDeliveryLogModel.__tablename__,
    }

    assert "one_stop_terminal_quotes" in table_names
    assert "one_stop_broker_connections" in table_names
    assert "one_stop_acats_transfers" in table_names
    assert "one_stop_notification_delivery_logs" in table_names
    assert models.TerminalQuoteDTO(quote_id="q1", symbol="msft", bid=1, ask=2, last=1.5, audit_id="audit").symbol == "MSFT"
    assert models.AlertRuleDTO(alert_rule_id="a1", name="Price", event_type="price", audit_id="audit").status == "active"
