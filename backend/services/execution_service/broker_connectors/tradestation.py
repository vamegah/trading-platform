from typing import Optional

from backend.services.execution_service.broker_connectors.base import BaseBroker, BrokerCapabilities, BrokerOrder


class TradeStationConnector(BaseBroker):
    name = "tradestation"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            mode=self.mode,
            asset_classes=("equity", "option", "future"),
            order_types=("MARKET", "LIMIT", "STOP", "TWAP"),
            supports_shorting=True,
            supports_margin=True,
            supports_automated=False,
            max_order_notional=750000.0,
            max_participation_rate=0.18,
        )

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "LIMIT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> BrokerOrder:
        return self._record_fill(
            symbol,
            side,
            quantity,
            limit_price or stop_price or 100.0,
            order_type,
            limit_price,
            stop_price,
        )

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        return self.orders[broker_order_id]

    async def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self.orders:
            self.orders[broker_order_id].status = "CANCELED"
            return True
        return False

    async def get_positions(self) -> dict[str, float]:
        return dict(self.positions)

    async def get_account_value(self) -> float:
        return self.cash + sum(quantity * 100.0 for quantity in self.positions.values())
