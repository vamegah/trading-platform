import pytest
from httpx import ASGITransport, AsyncClient

from backend.api_gateway.main import app
from backend.services.execution_service.broker_connectors.alpaca import AlpacaBroker
from backend.services.execution_service.broker_connectors.base import BrokerConfigurationError
from backend.services.execution_service.broker_connectors.ibkr import IbkrBroker
from backend.services.execution_service.broker_registry import get_broker, list_broker_capabilities
from backend.services.execution_service.order_router import OrderRouter, execution_precheck


def test_broker_capability_model_is_consistent_and_extensible() -> None:
    capabilities = list_broker_capabilities("sandbox")
    brokers = {item["broker"] for item in capabilities}

    assert {"alpaca", "ibkr", "tradestation", "td_ameritrade"}.issubset(brokers)
    assert next(item for item in capabilities if item["broker"] == "alpaca")["mode"] == "sandbox"
    assert next(item for item in capabilities if item["broker"] == "td_ameritrade")["status"] == "deferred"
    assert next(item for item in capabilities if item["broker"] == "ibkr")["supports_order_preview"] is True


@pytest.mark.asyncio
async def test_deferred_td_connector_fails_closed_with_successor_status() -> None:
    broker = get_broker("schwab", "sandbox")

    assert broker.capabilities().status == "deferred"
    with pytest.raises(BrokerConfigurationError):
        await broker.place_order("MSFT", "BUY", 1, order_type="MARKET")


@pytest.mark.asyncio
async def test_alpaca_sandbox_orders_positions_balances_and_fills() -> None:
    broker = get_broker("alpaca", "sandbox")
    order = await broker.place_order("MSFT", "BUY", 5, order_type="MARKET")

    assert order.status == "FILLED"
    assert (await broker.get_order_status(order.broker_order_id)).broker_order_id == order.broker_order_id
    assert (await broker.get_positions())["MSFT"] == 5
    assert (await broker.get_balances())["equity"] > 0
    assert (await broker.get_fills(order.broker_order_id))[0]["filled_quantity"] == 5
    assert (await broker.get_fills(order.broker_order_id))[0]["symbol"] == "MSFT"


@pytest.mark.asyncio
async def test_ibkr_connector_supports_order_lifecycle() -> None:
    broker = get_broker("ibkr", "sandbox")
    order = await broker.place_order("ESM6", "BUY", 1, order_type="LIMIT", limit_price=5200)
    canceled = await broker.cancel_order(order.broker_order_id)

    assert canceled is True
    assert (await broker.get_order_status(order.broker_order_id)).status == "CANCELED"


@pytest.mark.asyncio
async def test_live_broker_modes_fail_closed_without_certification_or_credentials() -> None:
    alpaca = AlpacaBroker(mode="live")
    ibkr = IbkrBroker(mode="live")

    with pytest.raises(BrokerConfigurationError):
        await alpaca.place_order("MSFT", "BUY", 1)
    with pytest.raises(BrokerConfigurationError):
        await ibkr.place_order("MSFT", "BUY", 1)


@pytest.mark.asyncio
async def test_certified_live_broker_accepts_without_simulated_fill_or_position_mutation() -> None:
    broker = AlpacaBroker(
        mode="live",
        api_key="paper-live-key",
        api_secret="paper-live-secret",
        certified_live=True,
    )

    order = await broker.place_order("MSFT", "BUY", 1, order_type="LIMIT", limit_price=100)

    assert order.status == "ACCEPTED"
    assert order.filled_quantity == 0
    assert await broker.get_positions() == {}


@pytest.mark.asyncio
async def test_smart_order_router_selects_execution_algorithms() -> None:
    broker = get_broker("ibkr", "sandbox")
    router = OrderRouter(broker)

    market = await router.smart_route("MSFT", "BUY", 100, current_price=100, daily_volume=1_000_000, urgency="high")
    vwap = await router.smart_route("MSFT", "BUY", 100_000, current_price=100, daily_volume=1_000_000)
    iceberg = await router.smart_route("MSFT", "BUY", 3_000, current_price=100, daily_volume=10_000)

    assert market["strategy"] == "MARKET"
    assert vwap["strategy"] == "VWAP"
    assert iceberg["strategy"] == "ICEBERG"
    assert iceberg["filled_quantity"] == 3_000
    assert iceberg["execution_plan"]["capacity_warning"] is True
    assert iceberg["order_events"][0]["order_type"] == "LIMIT"


@pytest.mark.asyncio
async def test_router_rejects_unsupported_fractional_or_deferred_broker_orders() -> None:
    ibkr = await OrderRouter(get_broker("ibkr", "sandbox")).smart_route(
        "MSFT",
        "BUY",
        1.5,
        current_price=100,
        daily_volume=1_000_000,
    )
    deferred = await OrderRouter(get_broker("td_ameritrade", "sandbox")).smart_route(
        "MSFT",
        "BUY",
        1,
        current_price=100,
        daily_volume=1_000_000,
    )

    assert ibkr["status"] == "rejected"
    assert "unsupported_fractional_quantity" in ibkr["violations"]
    assert deferred["status"] == "rejected"
    assert "broker_unavailable" in deferred["violations"]


def test_execution_precheck_fails_closed_for_missing_consent_and_risk_flags() -> None:
    blocked = execution_precheck(
        {
            "mode": "automated",
            "suitability_completed": True,
            "risk_breach": True,
            "stale_signal": True,
            "automation_consent": False,
        }
    )

    assert blocked["allowed"] is False
    assert "portfolio_risk_breach" in blocked["violations"]
    assert "automation_consent_required" in blocked["violations"]
    assert "signed_automation_acknowledgement_required" in blocked["violations"]


def test_execution_precheck_requires_one_click_auth_and_role_gates_when_supplied() -> None:
    one_click = execution_precheck(
        {
            "mode": "one_click",
            "suitability_completed": True,
            "roles": ["user"],
            "auth_token_valid": True,
        }
    )
    automated = execution_precheck(
        {
            "mode": "automated",
            "suitability_completed": True,
            "automation_consent": True,
            "automation_acknowledgement_signed": True,
            "roles": ["user"],
        }
    )
    live = execution_precheck(
        {
            "mode": "one_click",
            "broker_mode": "live",
            "suitability_completed": True,
            "one_click_acknowledged": True,
            "auth_token_valid": False,
        }
    )

    assert "one_click_acknowledgement_required" in one_click["violations"]
    assert "missing_permission:trade:automated" in automated["violations"]
    assert "auth_required" in live["violations"]
    assert "live_trading_acknowledgement_required" in live["violations"]


@pytest.mark.asyncio
async def test_milestone6_gateway_execution_endpoints() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        brokers = await client.get("/execution/brokers")
        blocked = await client.post(
            "/execution/smart-route",
            json={
                "broker": "ibkr",
                "symbol": "MSFT",
                "side": "BUY",
                "quantity": 100,
                "suitability_completed": False,
            },
        )
        routed = await client.post(
            "/execution/smart-route",
            json={
                "broker": "ibkr",
                "broker_mode": "sandbox",
                "symbol": "MSFT",
                "side": "BUY",
                "quantity": 100,
                "current_price": 100,
                "daily_volume": 1_000_000,
                "urgency": "high",
                "mode": "one_click",
                "suitability_completed": True,
                "one_click_acknowledged": True,
            },
        )
        account = await client.get("/execution/brokers/alpaca/account")

    assert brokers.status_code == 200
    assert any(item["broker"] == "ibkr" for item in brokers.json())
    assert blocked.json()["status"] == "rejected"
    assert routed.status_code == 200
    assert routed.json()["status"] == "routed"
    assert routed.json()["strategy"] == "MARKET"
    assert routed.json()["execution_plan"]["strategy"] == "MARKET"
    assert account.json()["capabilities"]["broker"] == "alpaca"
