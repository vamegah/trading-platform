import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.trader_operating_system import market_replay


@pytest.mark.asyncio
async def test_m11_command_center_and_order_blotter_are_operational() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        command = await client.get("/trader-os/command-center")
        blotter = await client.get("/trader-os/orders")
        submitted = await client.post(
            "/trader-os/orders",
            json={
                "symbol": "MSFT",
                "side": "BUY",
                "quantity": 5,
                "order_type": "limit",
                "limit_price": 420,
                "current_price": 420,
                "broker": "alpaca",
            },
        )
        order_id = submitted.json()["order"]["order_id"]
        replaced = await client.post(
            f"/trader-os/orders/{order_id}/replace",
            json={"quantity": 7, "limit_price": 421.5},
        )
        canceled = await client.post(f"/trader-os/orders/{order_id}/cancel")

    assert command.status_code == 200
    command_payload = command.json()
    assert command_payload["totals"]["equity"] > 0
    assert command_payload["positions"]
    assert command_payload["broker_health"]
    assert command_payload["exposure"]["sectors"]
    assert blotter.status_code == 200
    assert blotter.json()["open_orders"]
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "working"
    assert submitted.json()["precheck"]["allowed"] is True
    assert replaced.json()["status"] == "replaced"
    assert replaced.json()["order"]["quantity"] == 7
    assert canceled.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_m11_margin_and_options_gates_fail_closed() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        margin = await client.post(
            "/trader-os/margin",
            json={
                "broker": "alpaca",
                "asset_type": "option",
                "quantity": 50,
                "current_price": 800,
                "buying_power": 1000,
                "options_approved": False,
            },
        )
        denied_options = await client.post(
            "/trader-os/options/approval",
            json={"experience": "beginner", "risk_disclosure_acknowledged": False},
        )
        approved_options = await client.post(
            "/trader-os/options/approval",
            json={"experience": "advanced", "objective": "hedging", "risk_disclosure_acknowledged": True},
        )

    assert margin.status_code == 200
    assert margin.json()["allowed"] is False
    assert "options approval is required" in margin.json()["violations"]
    assert denied_options.json()["approved"] is False
    assert approved_options.json()["approved"] is True
    assert "defined_risk_spread" in approved_options.json()["allowed_strategies"]


@pytest.mark.asyncio
async def test_m11_replay_execution_quality_journal_copilot_and_compliance() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        options = await client.get("/trader-os/options/MSFT")
        quality = await client.get("/trader-os/execution-quality")
        replay = await client.get("/trader-os/replay/MSFT")
        replay_trade = await client.post(
            "/trader-os/replay/trades",
            json={"symbol": "MSFT", "side": "BUY", "quantity": 10, "price": 421.0},
        )
        journal_entry = await client.post(
            "/trader-os/journal",
            json={"symbol": "MSFT", "setup": "breakout retest", "thesis": "momentum continuation"},
        )
        copilot = await client.post("/trader-os/copilot", json={"question": "Build a hedged version of this trade"})
        compliance = await client.get("/trader-os/compliance-center")
        reconciliation = await client.get("/trader-os/reconciliation")
        watchlists = await client.get("/trader-os/watchlists")
        events = await client.get("/trader-os/events")

    assert options.json()["chain"]
    assert options.json()["strategy_builder"]
    assert quality.json()["summary"]["fills"] >= 1
    assert replay.json()["bars"]
    assert replay_trade.json()["ai_signal_alignment"] == "aligned"
    assert journal_entry.json()["journal_id"].startswith("journal-v2-")
    assert copilot.json()["guardrails"]["requires_explicit_confirmation"] is True
    assert copilot.json()["guardrails"]["can_place_trade"] is False
    assert "FINRA Rule 5310" in compliance.json()["regulatory_design_anchors"]
    assert reconciliation.json()["alerts"]
    assert watchlists.json()["heatmaps"]["sectors"]
    assert watchlists.json()["why_moving"]
    assert events.json()["events"][0]["linked_risks"]


def test_m11_market_replay_is_deterministic_for_same_symbol_and_date() -> None:
    first = market_replay("MSFT", "2026-06-04")
    second = market_replay("MSFT", "2026-06-04")

    assert first["bars"] == second["bars"]
    assert first["ai_signal_at_start"] == second["ai_signal_at_start"]
