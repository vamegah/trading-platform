from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Optional


@dataclass(frozen=True)
class BrokerCapabilities:
    broker: str
    mode: str = "sandbox"
    status: str = "available"
    asset_classes: tuple[str, ...] = ("equity",)
    order_types: tuple[str, ...] = ("MARKET", "LIMIT")
    supports_fractional: bool = False
    supports_shorting: bool = False
    supports_margin: bool = False
    supports_streaming: bool = False
    supports_cancel_replace: bool = True
    supports_order_preview: bool = True
    supports_one_click: bool = True
    supports_automated: bool = False
    max_order_notional: float = 250000.0
    max_participation_rate: float = 0.2
    requires_credentials: bool = False
    requires_live_certification: bool = True
    certified_live: bool = False
    notes: str | None = None


@dataclass
class BrokerOrder:
    broker_order_id: str
    status: str  # FILLED, PARTIAL, etc.
    filled_quantity: float
    average_price: float
    commission: float
    timestamp: datetime
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    limit_price: float | None = None
    stop_price: float | None = None


class BrokerConfigurationError(RuntimeError):
    pass


class BaseBroker(ABC):
    name = "base"

    def __init__(self, mode: str = "sandbox"):
        self.mode = mode
        self.orders: dict[str, BrokerOrder] = {}
        self.positions: dict[str, float] = {}
        self.cash = 100000.0

    @property
    def live_mode(self) -> bool:
        return self.mode.lower() == "live"

    def ensure_live_ready(self) -> None:
        if self.live_mode and not self.capabilities().certified_live:
            raise BrokerConfigurationError(f"{self.name} live mode is not certified")

    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> None:
        caps = self.capabilities()
        if caps.status != "available":
            raise BrokerConfigurationError(f"{self.name} is not available: {caps.status}")
        if not symbol:
            raise BrokerConfigurationError("symbol is required")
        if side.upper() not in {"BUY", "SELL"}:
            raise BrokerConfigurationError("side must be BUY or SELL")
        if quantity <= 0:
            raise BrokerConfigurationError("quantity must be positive")
        if order_type.upper() not in caps.order_types:
            raise BrokerConfigurationError(f"{self.name} does not support {order_type.upper()} orders")
        if not caps.supports_fractional and quantity != int(quantity):
            raise BrokerConfigurationError(f"{self.name} does not support fractional quantities")
        if order_type.upper() in {"LIMIT", "STOP_LIMIT"} and limit_price is not None and limit_price <= 0:
            raise BrokerConfigurationError("limit_price must be positive")
        if order_type.upper() in {"STOP", "STOP_LIMIT", "TRAILING_STOP"} and stop_price is not None and stop_price <= 0:
            raise BrokerConfigurationError("stop_price must be positive")

    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "LIMIT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        raise NotImplementedError

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> Dict[str, float]:
        raise NotImplementedError

    @abstractmethod
    async def get_account_value(self) -> float:
        raise NotImplementedError

    async def get_balances(self) -> dict[str, float]:
        return {"cash": round(self.cash, 2), "equity": round(await self.get_account_value(), 2)}

    async def get_fills(self, broker_order_id: str | None = None) -> list[dict[str, object]]:
        orders = [self.orders[broker_order_id]] if broker_order_id and broker_order_id in self.orders else self.orders.values()
        return [
            {
                "broker_order_id": order.broker_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "filled_quantity": order.filled_quantity,
                "average_price": order.average_price,
                "commission": order.commission,
                "timestamp": order.timestamp.isoformat(),
            }
            for order in orders
            if order.filled_quantity > 0
        ]

    async def cancel_open_orders(self) -> list[str]:
        canceled = []
        for order_id, order in self.orders.items():
            if order.status not in {"FILLED", "CANCELED", "REJECTED"}:
                order.status = "CANCELED"
                canceled.append(order_id)
        return canceled

    def _record_fill(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        self.validate_order(symbol, side, quantity, order_type, limit_price, stop_price)
        normalized_side = side.upper()
        normalized_order_type = order_type.upper()
        broker_order_id = f"{self.name}-{self.mode}-{len(self.orders) + 1}"
        signed_quantity = quantity if normalized_side == "BUY" else -quantity
        is_filled = self.mode == "sandbox"
        if is_filled:
            self.positions[symbol.upper()] = self.positions.get(symbol.upper(), 0.0) + signed_quantity
            self.cash -= signed_quantity * price
        order = BrokerOrder(
            broker_order_id=broker_order_id,
            status="FILLED" if is_filled else "ACCEPTED",
            filled_quantity=quantity if is_filled else 0.0,
            average_price=round(price, 4),
            commission=round(max(0.35, quantity * 0.0035), 2),
            timestamp=datetime.utcnow(),
            symbol=symbol.upper(),
            side=normalized_side,
            order_type=normalized_order_type,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        self.orders[broker_order_id] = order
        return order


class SimulatedBroker(BaseBroker):
    name = "simulated"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(broker=self.name, mode=self.mode)

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "LIMIT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        price = limit_price or stop_price or 100.0
        return self._record_fill(symbol, side, quantity, price, order_type, limit_price, stop_price)

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        return self.orders[broker_order_id]

    async def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self.orders:
            self.orders[broker_order_id].status = "CANCELED"
            return True
        return False

    async def get_positions(self) -> Dict[str, float]:
        return dict(self.positions)

    async def get_account_value(self) -> float:
        return self.cash + sum(quantity * 100.0 for quantity in self.positions.values())
