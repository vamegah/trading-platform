import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app


@pytest.mark.asyncio
async def test_auth_demo_session_refresh_and_session_introspection() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await client.post("/api/auth/demo")
        session = await client.get(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        )
        refreshed = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": token.json()["refresh_token"]},
        )

    assert token.status_code == 200
    assert session.json()["authenticated"] is True
    assert "read:signals" in session.json()["permissions"]
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


@pytest.mark.asyncio
async def test_single_stock_deep_dive_payload_supports_dashboard() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signals/evaluate",
            json={"symbol": "MSFT", "portfolio_context": {"factor_load": {"quality": 0.4}}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "MSFT"
    assert {"fundamentals", "technical", "news_sentiment", "macro"}.issubset(payload["agent_outputs"])
    assert payload["rationale"]
    assert payload["explainability"]["top_drivers"]
    assert payload["return_distribution"]["horizon_days"] == 20
    assert payload["factor_exposures"]
    assert payload["tail_risk_summary"]["summary"]
    assert "freshness_score" in payload


@pytest.mark.asyncio
async def test_discovery_scanner_ranks_results_for_dashboard() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signals/scanner",
            json={
                "universe": ["AAPL", "MSFT", "NVDA", "JPM"],
                "min_confidence": 0.1,
                "factor": "momentum",
                "sector": "technology",
                "custom_criteria": {"min_reward_to_risk": 0.5, "max_tail_risk": 0.5},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["results"])
    assert payload["results"]
    assert "reward_to_risk" in payload["results"][0]
    assert payload["filters"]["sector"] == "technology"
    assert all(row["sector"] == "technology" for row in payload["results"])
    assert all(row["tail_risk"] <= 0.5 for row in payload["results"])


@pytest.mark.asyncio
async def test_explainability_and_freshness_payloads_support_dashboard_panels() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        signal = await client.post("/signals/evaluate", json={"symbol": "AAPL"})
        explanation = await client.get("/explain/AAPL")
        freshness = await client.post("/signals/freshness", json=signal.json())

    assert explanation.status_code == 200
    assert explanation.json()["feature_contributions"]
    assert explanation.json()["top_drivers"]
    assert freshness.status_code == 200
    assert freshness.json()["signal_freshness"]["half_life_minutes"] > 0
    assert freshness.json()["signal_freshness"]["invalidation_triggers"]


@pytest.mark.asyncio
async def test_alert_preferences_and_nudges_are_dashboard_ready() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alert_response = await client.get("/alerts", params={"user_id": "demo"})
        preferences_response = await client.post(
            "/alerts/preferences",
            json={
                "user_id": "demo",
                "push_enabled": True,
                "email_enabled": True,
                "high_conviction_threshold": 0.75,
                "stop_loss_alerts": True,
                "thesis_change_alerts": True,
            },
        )
        nudge_response = await client.get("/nudges/history", params={"user_id": "demo"})
        dismiss_response = await client.post("/nudges/dismiss/FOMO_BUY", params={"user_id": "demo"})
        dismissal_log = await client.get("/nudges/dismissals", params={"user_id": "demo"})

    assert alert_response.status_code == 200
    assert alert_response.json()[0]["type"] == "high_conviction_signal"
    assert preferences_response.status_code == 200
    assert preferences_response.json()["email_enabled"] is True
    assert nudge_response.status_code == 200
    assert nudge_response.json()[0]["event_type"] == "FOMO_BUY"
    assert nudge_response.json()[0]["evidence"]
    assert dismiss_response.json()["logged"] == "true"
    assert dismissal_log.json()
