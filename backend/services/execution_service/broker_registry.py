from backend.services.execution_service.broker_connectors.alpaca import AlpacaBroker
from backend.services.execution_service.broker_connectors.base import BaseBroker, BrokerCapabilities
from backend.services.execution_service.broker_connectors.binance_futures import BinanceFuturesConnector
from backend.services.execution_service.broker_connectors.deribit import DeribitConnector
from backend.services.execution_service.broker_connectors.ibkr import IbkrBroker
from backend.services.execution_service.broker_connectors.td_ameritrade import TDAmeritradeConnector
from backend.services.execution_service.broker_connectors.tradestation import TradeStationConnector


BROKER_FACTORIES = {
    "alpaca": AlpacaBroker,
    "ibkr": IbkrBroker,
    "tradestation": TradeStationConnector,
    "deribit": DeribitConnector,
    "binance_futures": BinanceFuturesConnector,
    "td_ameritrade": TDAmeritradeConnector,
}
BROKER_ALIASES = {
    "interactive_brokers": "ibkr",
    "interactivebrokers": "ibkr",
    "td": "td_ameritrade",
    "tda": "td_ameritrade",
    "schwab": "td_ameritrade",
    "binance": "binance_futures",
}


def get_broker(name: str = "alpaca", mode: str = "sandbox") -> BaseBroker:
    normalized = BROKER_ALIASES.get(name.lower(), name.lower())
    if normalized not in BROKER_FACTORIES:
        raise ValueError(f"Unsupported broker: {name}")
    return BROKER_FACTORIES[normalized](mode=mode)


def list_broker_capabilities(mode: str = "sandbox") -> list[dict[str, object]]:
    capabilities = []
    for factory in BROKER_FACTORIES.values():
        broker = factory(mode=mode)
        payload = broker.capabilities().__dict__
        if hasattr(broker, "status"):
            payload.update(broker.status())
        capabilities.append(payload)
    return sorted(capabilities, key=lambda item: str(item["broker"]))


def broker_supports_order(broker: BaseBroker, asset_type: str, order_type: str, notional: float) -> tuple[bool, list[str]]:
    caps: BrokerCapabilities = broker.capabilities()
    violations = []
    if caps.status != "available":
        violations.append("broker_unavailable")
    if asset_type not in caps.asset_classes:
        violations.append("unsupported_asset_type")
    if order_type.upper() not in caps.order_types:
        violations.append("unsupported_order_type")
    if notional > caps.max_order_notional:
        violations.append("broker_notional_limit")
    if broker.live_mode and caps.requires_live_certification and not caps.certified_live:
        violations.append("broker_live_not_certified")
    return not violations, violations


def broker_supports_quantity(broker: BaseBroker, quantity: float) -> tuple[bool, list[str]]:
    caps = broker.capabilities()
    violations = []
    if quantity <= 0:
        violations.append("quantity_must_be_positive")
    if not caps.supports_fractional and quantity != int(quantity):
        violations.append("unsupported_fractional_quantity")
    return not violations, violations
