import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.workstation_service import strategy_research


@pytest.mark.asyncio
async def test_m12_basket_rebalance_pretrade_and_staging_flow() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overview = await client.get("/workstation/overview")
        preview = await client.post(
            "/workstation/basket/preview",
            json={"target_weights": {"MSFT": 0.3, "NVDA": 0.16, "JPM": 0.2, "SPY": 0.34}},
        )
        submitted = await client.post(
            "/workstation/basket/submit",
            json={"target_weights": {"MSFT": 0.3, "NVDA": 0.16, "JPM": 0.2, "SPY": 0.34}, "confirmed": True},
        )
        staged = await client.post("/workstation/staging/orders", json={"symbol": "MSFT", "side": "BUY", "quantity": 4, "limit_price": 421})
        approved = await client.post(f"/workstation/staging/{staged.json()['stage_id']}/approve", json={"actor": "checker"})
        released = await client.post(f"/workstation/staging/{staged.json()['stage_id']}/release", json={"confirmed": True})

    assert overview.status_code == 200
    assert any(module["id"] == "basket" for module in overview.json()["modules"])
    assert preview.status_code == 200
    assert preview.json()["orders"]
    assert preview.json()["impact_preview"]["estimated_margin_delta"] >= 0
    assert preview.json()["pre_trade"]["allowed"] is True
    assert submitted.json()["status"] == "staged"
    assert submitted.json()["release_queue"]
    assert approved.json()["status"] == "approved"
    assert released.json()["status"] == "released_to_sandbox"


@pytest.mark.asyncio
async def test_m12_pretrade_borrow_and_tax_lots_fail_closed() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        blocked = await client.post(
            "/workstation/pre-trade/check",
            json={"symbol": "GME", "side": "SELL_SHORT", "quantity": 150, "limit_price": 28.5, "locate_status": "required", "liquidity_score": 0.31},
        )
        borrow = await client.get("/workstation/borrow/GME")
        locate = await client.post("/workstation/borrow/locate", json={"symbol": "MSFT", "quantity": 100})
        tax = await client.post("/workstation/tax-lots/MSFT/decision", json={"quantity": 25})

    assert blocked.status_code == 200
    assert blocked.json()["allowed"] is False
    assert any("Short sale requires" in violation for violation in blocked.json()["violations"])
    assert borrow.json()["hard_to_borrow"] is True
    assert borrow.json()["blocked_reason"]
    assert locate.json()["status"] == "located"
    assert tax.json()["recommended_method"] == "specific_lot"
    assert tax.json()["best_lot_to_sell"].startswith("MSFT-lot")


@pytest.mark.asyncio
async def test_m12_portfolio_microstructure_data_quality_and_strategy() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        portfolio = await client.post("/workstation/portfolio-lab/construct", json={"objective": "income with tax awareness"})
        microstructure = await client.get("/workstation/microstructure/MSFT?quantity=250")
        quality = await client.get("/workstation/data-quality")
        strategy = await client.post(
            "/workstation/strategy/research",
            json={"universe": ["MSFT", "NVDA", "JPM"], "rules": [{"field": "freshness_score", "operator": ">", "value": 0.65}]},
        )
        deploy = await client.post(
            "/workstation/strategy/deploy",
            json={"universe": ["MSFT", "NVDA", "JPM"], "rules": [{"field": "freshness_score", "operator": ">", "value": 0.65}], "confirmed": True},
        )

    assert portfolio.json()["target_allocations"]
    assert portfolio.json()["rebalance_plan"]["orders"]
    assert microstructure.json()["nbbo"]["spread_bps"] > 0
    assert microstructure.json()["depth"]
    assert quality.json()["overall_status"] == "degraded"
    assert quality.json()["signal_policy"]["degraded_signals"]
    assert strategy.json()["walk_forward_report"]["costs_included"] is True
    assert deploy.json()["status"] in {"paper_deployed", "confirmation_or_eligibility_required"}


@pytest.mark.asyncio
async def test_m12_risk_constitution_archive_and_emergency_controls() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        saved_rule = await client.post("/workstation/risk-constitution", json={"rule_type": "restricted_symbol", "symbol": "TSLA"})
        risk_eval = await client.post("/workstation/risk-constitution/evaluate", json={"symbol": "TSLA", "position_pct": 0.1})
        archive = await client.get("/workstation/disclosure-archive?query=options")
        emergency = await client.get("/workstation/emergency")
        paused = await client.post("/workstation/emergency/pause", json={"reason": "test"})
        canceled = await client.post("/workstation/emergency/cancel-all", json={"reason": "test"})
        post_pause = await client.get("/workstation/emergency")

    assert saved_rule.json()["status"] == "saved"
    assert risk_eval.json()["allowed"] is False
    assert "restricted" in " ".join(risk_eval.json()["violations"])
    assert archive.json()["records"]
    assert emergency.json()["push_ready"] is True
    assert paused.json()["status"] == "active"
    assert canceled.json()["status"] == "submitted"
    assert post_pause.json()["trading_paused"] is True


def test_m12_strategy_research_is_deterministic_for_same_definition() -> None:
    payload = {"universe": ["MSFT", "NVDA", "JPM"], "rules": [{"field": "freshness_score", "operator": ">", "value": 0.65}]}

    first = strategy_research(payload)
    second = strategy_research(payload)

    assert first["screen_results"] == second["screen_results"]
    assert first["walk_forward_report"] == second["walk_forward_report"]
