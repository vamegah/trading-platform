from datetime import datetime

from backend.services.execution_service.broker_connectors.base import BaseBroker, BrokerCapabilities, BrokerOrder


class BinanceFuturesConnector(BaseBroker):
    name = "binance_futures"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            mode=self.mode,
            asset_classes=("crypto", "crypto_future"),
            order_types=("MARKET", "LIMIT", "STOP"),
            supports_margin=True,
            supports_streaming=True,
            supports_automated=False,
            max_order_notional=500000.0,
            max_participation_rate=0.2,
        )

    async def place_order(self, symbol, side, quantity, order_type="LIMIT", limit_price=None, stop_price=None):
        self.validate_order(symbol, side, quantity, order_type, limit_price, stop_price)
        return BrokerOrder(
            f"binance-futures-{symbol}",
            "ACCEPTED",
            0.0,
            limit_price or stop_price or 0.0,
            0.0,
            datetime.utcnow(),
            symbol=symbol.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            limit_price=limit_price,
            stop_price=stop_price,
        )

    async def get_order_status(self, broker_order_id: str) -> BrokerOrder:
        return BrokerOrder(broker_order_id, "WORKING", 0.0, 0.0, 0.0, datetime.utcnow())

    async def cancel_order(self, broker_order_id: str) -> bool:
        return True

    async def get_positions(self) -> dict[str, float]:
        return {}

    async def get_account_value(self) -> float:
        return 0.0
