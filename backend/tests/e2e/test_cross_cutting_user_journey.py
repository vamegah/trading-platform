import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app


@pytest.mark.asyncio
async def test_onboarding_dashboard_paper_trade_and_journal_happy_path() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        suitability = await client.post(
            "/api/profile/suitability/guard",
            json={
                "answers": {
                    "investment_experience": "advanced",
                    "risk_tolerance": "high",
                    "annual_income": "above_250k",
                    "net_worth": "above_1m",
                    "investment_horizon": "very_long",
                    "loss_tolerance": "buy_more",
                },
                "requested_strategy": "automated_trading",
            },
        )
        signal = await client.post("/signals/evaluate", json={"symbol": "MSFT"})
        dashboard = await client.post(
            "/signals/scanner",
            json={"universe": ["MSFT", "AAPL"], "min_confidence": 0.1},
        )
        paper = await client.post("/paper/execute/MSFT")
        journal = await client.get("/paper/journal")

    assert suitability.json()["allowed"] is True
    assert signal.json()["symbol"] == "MSFT"
    assert dashboard.json()["count"] >= 1
    assert paper.json()["status"] in {"executed", "skipped"}
    if paper.json()["status"] == "executed":
        assert paper.json()["paper_execution_parity"]["same_precheck_as_live"] is True
        assert paper.json()["journal_entry"]["attribution"]["source_breakdown"]
    else:
        assert paper.json()["reason"]
    assert "entries" in journal.json()


@pytest.mark.asyncio
async def test_unsuitable_user_is_blocked_from_automated_trading() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        suitability = await client.post(
            "/api/profile/suitability/guard",
            json={
                "answers": {
                    "investment_experience": "none",
                    "risk_tolerance": "low",
                    "annual_income": "below_50k",
                    "net_worth": "below_50k",
                    "investment_horizon": "short",
                    "loss_tolerance": "sell_all",
                },
                "requested_strategy": "automated_trading",
            },
        )
        precheck = await client.post(
            "/execution/precheck",
            json={
                "mode": "automated",
                "suitability_completed": False,
                "automation_consent": False,
                "risk_breach": False,
                "stale_signal": False,
            },
        )

    assert suitability.json()["allowed"] is False
    assert "automated_trading" in suitability.json()["restricted_strategies"]
    assert precheck.json()["allowed"] is False
    assert "suitability_required" in precheck.json()["violations"]
    assert "automation_consent_required" in precheck.json()["violations"]


@pytest.mark.asyncio
async def test_live_and_stale_order_paths_fail_closed_with_cancel_actions() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stale = await client.post(
            "/execution/precheck",
            json={
                "mode": "one_click",
                "broker_mode": "live",
                "suitability_completed": True,
                "one_click_acknowledged": True,
                "stale_signal": True,
            },
        )
        risk = await client.post(
            "/execution/precheck",
            json={
                "mode": "one_click",
                "suitability_completed": True,
                "one_click_acknowledged": True,
                "risk_breach": True,
            },
        )

    assert stale.json()["allowed"] is False
    assert "stale_signal" in stale.json()["violations"]
    assert "live_trading_acknowledgement_required" in stale.json()["violations"]
    assert stale.json()["cancel_pending_orders"] is True
    assert risk.json()["allowed"] is False
    assert "portfolio_risk_breach" in risk.json()["violations"]
    assert risk.json()["new_orders_blocked"] is True
