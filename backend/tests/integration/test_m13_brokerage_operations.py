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
async def test_m13_cash_chart_corporate_actions_and_documents() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overview = await client.get("/brokerage-ops/overview")
        cash = await client.get("/brokerage-ops/cash-settlement")
        live_transfer = await client.post(
            "/brokerage-ops/cash-settlement/transfers",
            json={"direction": "withdrawal", "method": "wire", "amount": 1000, "live": True},
        )
        chart = await client.get("/brokerage-ops/chart-trading/MSFT")
        chart_preview = await client.post(
            "/brokerage-ops/chart-trading/order-preview",
            json={"symbol": "MSFT", "side": "BUY", "quantity": 10, "entry": 421.25, "stop": 409, "target": 440},
        )
        corporate = await client.get("/brokerage-ops/corporate-actions")
        election = await client.post(
            "/brokerage-ops/corporate-actions/corp-jpm-tender-2026/election",
            json={"election": "hold_and_receive_cash", "lot_selection": "specific_lot"},
        )
        documents = await client.get("/brokerage-ops/account-documents")
        document = await client.get("/brokerage-ops/account-documents/stmt-daily-2026-06-03")

    assert overview.status_code == 200
    assert any(module["id"] == "cash" for module in overview.json()["modules"])
    assert cash.json()["cash_summary"]["unsettled_cash"] > 0
    assert cash.json()["settlement_lots"][0]["status"] == "pending_t_plus_1"
    assert any(warning["type"] == "good_faith" for warning in cash.json()["warnings"])
    assert live_transfer.json()["status"] == "blocked"
    assert "M10" in live_transfer.json()["blocked_reason"]
    assert chart.json()["bracket_preview"]["oco_linked"] is True
    assert chart.json()["trade_controls"]["confirmation_required"] is True
    assert chart_preview.json()["status"] == "ready_for_confirmation"
    assert chart_preview.json()["pre_trade"]["allowed"] is True
    assert any(action["election_required"] for action in corporate.json()["actions"])
    assert election.json()["status"] == "recorded_for_sandbox"
    assert documents.json()["retention_policy"]["audit_ready"] is True
    assert "download_urls" in document.json()["preview"]


@pytest.mark.asyncio
async def test_m13_admin_surveillance_and_entitlements_fail_closed() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin = await client.get("/brokerage-ops/admin")
        blocked_override = await client.post("/brokerage-ops/admin/overrides", json={"confirmed": True})
        queued_override = await client.post(
            "/brokerage-ops/admin/overrides",
            json={"confirmed": True, "reason": "test review", "subject_ref": "order-msft"},
        )
        surveillance = await client.get("/brokerage-ops/surveillance")
        surveillance_eval = await client.post(
            "/brokerage-ops/surveillance/evaluate",
            json={"symbol": "JPM", "cancellations": 42, "submitted": 90, "event_blackout": True},
        )
        entitlements = await client.get("/brokerage-ops/entitlements")
        level_two = await client.post(
            "/brokerage-ops/entitlements/check",
            json={"data_type": "level_ii", "required_level": "real_time"},
        )

    assert admin.json()["role_gate"]["required_role"] == "supervisor"
    assert blocked_override.json()["status"] == "blocked"
    assert queued_override.json()["status"] == "queued_for_supervisory_review"
    assert surveillance.json()["patterns_monitored"]
    assert surveillance_eval.json()["status"] == "alert_created"
    assert surveillance_eval.json()["release_allowed"] is False
    assert entitlements.json()["cost_controls"]["block_when_budget_exceeded"] is True
    assert level_two.json()["status"] == "blocked"
    assert "level_ii" in level_two.json()["blocked_reason"]


@pytest.mark.asyncio
async def test_m13_recurring_conditional_reports_mobile_and_support() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        recurring = await client.get("/brokerage-ops/recurring-investments")
        plan = await client.post(
            "/brokerage-ops/recurring-investments",
            json={"symbol": "MSFT", "dollar_amount": 250, "cadence": "weekly", "dividend_reinvestment": True},
        )
        conditional_sim = await client.post(
            "/brokerage-ops/conditional-orders/simulate",
            json={"symbol": "MSFT", "side": "BUY", "quantity": 10, "current_price": 420, "triggers": [{"field": "price", "operator": "<=", "value": 421}]},
        )
        conditional = await client.post(
            "/brokerage-ops/conditional-orders",
            json={"symbol": "MSFT", "side": "BUY", "quantity": 10, "confirmed": True},
        )
        report = await client.post("/brokerage-ops/reports/portfolio-review", json={"title": "Client review"})
        mobile = await client.get("/brokerage-ops/mobile")
        pause = await client.post("/brokerage-ops/mobile/emergency-pause", json={"reason": "test"})
        support = await client.get("/brokerage-ops/support")
        support_case = await client.post(
            "/brokerage-ops/support/cases",
            json={"category": "order_rejection", "subject": "Why was this order rejected?", "message": "Need audit trail"},
        )

    assert recurring.json()["cash_sweep"]["enabled"] is True
    assert plan.json()["status"] == "active_sandbox"
    assert plan.json()["estimated_fractional_quantity"] > 0
    assert conditional_sim.json()["release_ready"] is True
    assert conditional.json()["status"] == "armed_sandbox"
    assert {"html", "pdf", "csv"}.issubset(set(report.json()["formats"]))
    assert report.json()["archive_id"].startswith("archive-")
    assert mobile.json()["devices"][0]["biometric_approval_supported"] is True
    assert pause.json()["status"] == "active"
    assert support.json()["available_actions"]
    assert support_case.json()["status"] == "open"
    assert support_case.json()["sla"]["priority"] == "high"


def test_m13_domain_models_and_tables_exist() -> None:
    table_names = {
        models.FundingAccountModel.__tablename__,
        models.CashTransferModel.__tablename__,
        models.CashLedgerEntryModel.__tablename__,
        models.SettlementLotModel.__tablename__,
        models.ChartTradingLayoutModel.__tablename__,
        models.CorporateActionModel.__tablename__,
        models.AccountDocumentModel.__tablename__,
        models.AdminReviewModel.__tablename__,
        models.SurveillanceAlertModel.__tablename__,
        models.MarketDataEntitlementModel.__tablename__,
        models.DataUsageMeterModel.__tablename__,
        models.RecurringInvestmentPlanModel.__tablename__,
        models.ConditionalOrderModel.__tablename__,
        models.PortfolioReviewPackModel.__tablename__,
        models.MobileDeviceModel.__tablename__,
        models.SupportCaseModel.__tablename__,
        models.AuditRequestModel.__tablename__,
    }

    assert "funding_accounts" in table_names
    assert "cash_transfers" in table_names
    assert "brokerage_corporate_actions" in table_names
    assert "conditional_orders" in table_names
    assert "support_cases" in table_names
    assert models.FundingAccountDTO(funding_account_id="fund-1", account_type="checking", institution_name="Bank", audit_id="audit").live_transfer_enabled is False
    assert models.ConditionalOrderDTO(conditional_order_id="cond-1", symbol="msft", side="buy", quantity=1, audit_id="audit").symbol == "MSFT"
